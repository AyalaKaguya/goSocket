import socket
import threading
import sys
import json

__version__ = '1.0.0'
__author__ = 'AyalaKaguya <ayalakaguya@outlook.com>'


class go:
    lock = threading.Lock()
    chanelServer = {}
    _close = False

    def __init__(self, server: str, port: int):
        super().__init__()

        self._server = server
        self._port = port

        try:
            self.socket = socket.socket()
            self.socket.connect((server, port))  # 主动初始化与服务器端的连接
        except Exception as ex:
            raise Exception('Unable to connect to the server')

    def subscribe(self, chanelName: str, func):
        with self.lock:
            self.chanelServer[chanelName] = func
        self.socket.send(bytes('join %s' % chanelName, encoding="utf8"))
        return self

    def unsubscribe(self, chanelName: str):
        with self.lock:
            try:
                self.chanelServer.pop(chanelName)
            except Exception as ex:
                raise Exception('Channel not yet subscribed')
        self.socket.send(bytes('leave %s' % chanelName, encoding="utf8"))
        return self

    def cilet_forver(self):
        self._close = False
        while not self._close:
            accept_data = str(self.socket.recv(1024), encoding="utf8")
            try:  # 区分返回内容
                data = json.loads(accept_data)
            except Exception as ex:
                # print(accept_data)
                continue

            try:  # 路由消息
                chanel = data['chanel']
                payload = data['data']
                with self.lock:
                    func = self.chanelServer[chanel]
                    func(payload)
            except Exception as ex:
                continue
        return self

    def send(self, chanelName: str, dataString: str):
        encodedData = json.dumps(
            {'chanel': chanelName, 'data': dataString}).encode()  # 构造发送数据
        self.socket.send(encodedData)
        return self

    def close(self):
        self._close = True
        self.socket.close()
