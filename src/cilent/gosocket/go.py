import socket
import threading
import sys
import json

class go:
    lock = threading.Lock()
    channelServer = {}
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

    def subscribe(self, channelName: str, func):
        with self.lock:
            self.channelServer[channelName] = func
        self.socket.send(bytes('join %s' % channelName, encoding="utf8"))
        return self

    def unsubscribe(self, channelName: str):
        with self.lock:
            try:
                self.channelServer.pop(channelName)
            except Exception as ex:
                raise Exception('Channel not yet subscribed')
        self.socket.send(bytes('leave %s' % channelName, encoding="utf8"))
        return self

    def cilent_forever(self):
        self._close = False
        while not self._close:
            accept_data = str(self.socket.recv(1024), encoding="utf8")
            try:  # 区分返回内容
                data = json.loads(accept_data)
            except Exception as ex:
                # print(accept_data)
                continue

            try:  # 路由消息
                channel = data['channel']
                payload = data['data']
                with self.lock:
                    func = self.channelServer[channel]
                    func(payload)
            except Exception as ex:
                continue
        return self

    def send(self, channelName: str, dataString: str):
        encodedData = json.dumps(
            {'channel': channelName, 'data': dataString}).encode()  # 构造发送数据
        self.socket.send(encodedData)
        return self

    def close(self):
        self._close = True
        self.socket.close()
        del self