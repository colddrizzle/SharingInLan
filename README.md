# SharingInLan
基于浏览器的局域网内共享软件原型

目前只实现了简单的文本同步功能。

其基本原理很简单，每台电脑的server都在相同的端口上监听局域网广播帧。

同时每个server启动的时候发送一个广播帧表示自己加入了局域网。其余server收到这个广播帧
则将其地址记录下来，同时发送一个ack，于是新启动的server也知道了其余server的地址。

server与浏览器端界面通过websocket通信。

后续可以做的很多，比如同步文件，同步桌面等，目前仅是一个验证。

# 使用

本项目依赖于gevent提供的webserver以及websocket功能。

为了避免环境问题，本项目使用[virtualenv](https://www.liaoxuefeng.com/wiki/1016959663602400/1019273143120480)
创建了虚拟环境。

使用时首先应该切换到虚拟python环境下（当然如果gevent按照没问题就不需要这个虚拟环境了）：

```
cd SharingInLan
venv\\Scripts\activate
```

然后启动服务器（需要python2）

```
cd SharingInLan
python server.py
```

因为是原型，端口硬编码，如果端口冲突更换端口就可以了。

如果使用vscode启动或调试

注意需要在settings.json中配置

```
{
    "python.pythonPath": "venv\\Scripts\\python.exe"
}

```

然后用Chrome打开main.html。

在局域网内每一台需要共享的电脑上重复上面步骤。


在浏览器界面上的任何输入都会同步到局域网中其他电脑中。