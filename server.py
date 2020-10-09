# coding=utf-8

from bottle import Bottle, route, run, template, request,abort
import threading
import socket
import traceback
import struct
import time

"""
待改进的地方：
1. 消息的结构可以更详细一些，比如分为3段：消息长、类型、内容。其中消息与类型是固定长度
2. 两边可能同时编辑，同时将内容推送给对方，从而导致内容不一致。可以根据Lamport的逻辑时钟概念
构造一个全局顺序，用来确定一致的显示内容。算法大致如下：
	1. 每个主机一个从0开始的计数器，并且当前显示内容时间戳为0
	2. 每当主机发送一个SYNC消息，计数器加1
	3. SYNC消息中含有发送消息时主机的计数器值（时间戳）
	4. 每当主机收到一个SYNC消息，将自己的计数器值调整为不小于当前值与SYNC中时间戳的新值
	5. 当主机收到一个SYNC消息时，如果SYNC时间戳比当前内容时间戳小则丢弃，相等则比较IP地址，大于则更新为SYNC中内容。
	6. 如果丢弃某个SYNC消息，则向SYNC消息来源同步自己的当前显示消息。（相当于告诉它：嘿，你已经严重落伍了，这才是最新版本）

"""

LISTEN_PORT = 33377
BROADCAST_ADDR = ("255.255.255.255", LISTEN_PORT)
group_member = dict()

#消息的最小长度，读取到最小长度的数据后就可以获知后面数据的长度
MSG_HEAD_LEN = 4

JOIN_MSG = "JOIN"
EXIT_MSG = "EXIT"
ACK_MSG = "WELCOME"
SYNC_MSG = "SYNC"

MSG_BUFF_LEN = 8192

host_ip = ""
wsock = None

def get_host_ip():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		ip = s.getsockname()[0]
	finally:
		s.close()
	return ip

def send_ack(addr):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
	sock.bind((host_ip, 0))

	c_len = MSG_HEAD_LEN+len(ACK_MSG)
	fmt = "!i"+str(len(ACK_MSG))+"s"
	content = struct.pack(fmt, c_len, ACK_MSG)
	sock.sendto(content, addr)
	sock.close()

# 为了简化，一次同步的内容完全容纳在一个UDP报文中
def sync_content(content):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	content = content.encode("utf-8")
	c_len = len(content)
	fmt = "!i"+str(c_len)+"s"
	msg = struct.pack(fmt, c_len+MSG_HEAD_LEN, content)
	sock.bind((host_ip, 0))
	sock.sendto(msg, BROADCAST_ADDR)
	sock.close()

def send_join():
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

	content = struct.pack("!i4s", 8, JOIN_MSG)
	sock.bind((host_ip, 0))
	sock.sendto(content, BROADCAST_ADDR)
	sock.close()

#需要处理加入与退出两种消息
def process_msg(msg, addr):

	#if addr[0] == host_ip:
	#	return

	c_len = struct.unpack("!i",msg[:MSG_HEAD_LEN])[0]
	fmt = "!"+str(c_len-MSG_HEAD_LEN)+"s"
	content = struct.unpack(fmt, msg[MSG_HEAD_LEN:])[0]
	if not content:
		print "empty content"
		return
	content = content.decode("utf-8")
	
	if content == JOIN_MSG:
		group_member[addr]="JOIN"
		print addr, "join"
		send_ack(addr)
	elif content == EXIT_MSG:
		del group_member[addr]
		print addr, "exit"
	elif content == ACK_MSG and addr[0] != host_ip:
		group_member[addr]="JOIN"
		print addr, "ack"
	elif addr[0] != host_ip: #收到其他主机传来的同步消息 一致性问题
		wsock.send(content)
		print "content update"



def manage_group():
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(("0.0.0.0", LISTEN_PORT))

	send_join()

	while True:
		#这里依次recv就接收一个UDP分组吗
		print "start listen msg on", LISTEN_PORT
		(msg, address) = sock.recvfrom(MSG_BUFF_LEN)
		process_msg(msg, address)



from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
app = Bottle()
@app.route('/websocket')
def handle_websocket():
	global wsock
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')

	while True:
		try:
			message = wsock.receive()
			sync_content(message)

		except Exception:
			traceback.print_exc()
			break


if __name__ == "__main__":
	host_ip = get_host_ip()

	# 一个线程去处理新加入的广播消息
	group_th = threading.Thread(target = manage_group)
	group_th.start()

	# 主线程处理websocket
	server = WSGIServer(("0.0.0.0", 8080), app,
		                    handler_class=WebSocketHandler)
	server.serve_forever()

