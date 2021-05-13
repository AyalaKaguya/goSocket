import logging
import sys
import socketserver
import socket
import threading
import json

SERV = "127.0.0.1"
PORT = 25538

CodingFormat = "utf-8"  # 定义全局编码格式

logging.basicConfig(format="%(asctime)s %(thread)d %(threadName)s %(message)s",
                    stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()


'''
Public 频道
承载基础指令和错误反馈
不接受json信息

如果发送json，将会触发数据路由
'''

back_def_document = '''
Return Code Definition：
    200     Return success
    500     Triggers an unhandled exception
    501     Channel request failed
    502     The instruction does not define a keyword
    503     The JSON information parameter sent is incorrect
    504     Exit channel when not in channel
    505     Wrong data type
    506     You must specify parameters for data
'''

help_document = '''
Help Document:
    send [message]          Send a message to 'Public' chanel.
    help                    Show help tips.
    exit                    Close this connection.
    back_def                Show return code definition.
    join <Chanel Name>      Join a chanel.
    leave <Chanel Name>     Leave a chanel.
'''


class MainHandler(socketserver.BaseRequestHandler):
    lock = threading.Lock()  # 进程锁
    clients = {}  # 连接池
    chanels = {'Public': {}}  # 通道池

    def setup(self):
        super().setup()
        self.event = threading.Event()

        msg = "Server:[{}:{}]:{}".format(
            self.client_address[0], self.client_address[1], "加入了服务器").encode()

        log.info("Connection:'{}:{}'".format(
            self.client_address[0], self.client_address[1]))

        with self.lock:
            self.clients[self.client_address] = self.request
            for c, sk in self.clients.items():  # 递归连接池，连接发送信息
                try:
                    sk.send(msg)
                except:
                    pass
            self.ChanelJoin()

    def handle(self):
        super().handle()
        sock: socket.socket = self.request

        while not self.event.is_set():
            # 监听消息
            try:
                data = sock.recv(1024).decode(CodingFormat)
            except Exception as e:
                log.error(e)
                break

            # 常见的退出字符串
            if not data or data == '':
                continue
            elif data in {'exit'}:
                break

            # 当不是json时当作指令处理
            try:
                jsonData = json.loads(data)
            except:
                self.PublicExec(data.split(' '))
                continue

            self.ChanelRouter(jsonData)

    def finish(self):
        super().finish()
        self.event.set()

        msg = "Server:[{}:{}]:{}".format(
            self.client_address[0], self.client_address[1], "退出了服务器").encode()

        with self.lock:
            if self.client_address in self.clients:
                self.clients.pop(self.client_address)
            for c, sk in self.clients.items():
                try:
                    sk.send(msg)
                except:
                    pass

        self.request.close()
        log.info("Exit:'{}:{}'".format(
            self.client_address[0], self.client_address[1]))

    def PublicExec(self, command: list) -> None:
        sock: socket.socket = self.request
        try:
            if command[0] == 'send': # 发送消息的逻辑
                data = json.dumps({'target': '{}:{}'.format(
                    self.client_address[0], self.client_address[1]), 'type': 'msg', 'msg': command[1:]})
                self.ChanelSend('Public', data)
                return
            elif command[0] == 'help': # 发送帮助文档
                msg = help_document.encode()
                sock.send(msg)
                return
            elif command[0] == 'join': # 加入频道的逻辑
                if len(command) < 2:
                    self.error(502, 'Please enter the channel name')
                    return
                self.ChanelJoin(command[1])
                return
            elif command[0] == 'leave': # 离开频道的逻辑
                if len(command) < 2:
                    self.error(502, 'Please enter the channel name')
                    return
                self.ChanelLeave(command[1])
                return
            elif command[0] == 'back_def': # 发送返回码定义
                msg = back_def_document.encode()
                sock.send(msg)
                return

            sock.send("Server Error:\n\tUndefined command '{}'\n\tType 'help' to get some commands.".format(
                ' '.join(command)).encode())
        except Exception as ex: # 发生了未知的错误
            self.crash('Server Error！', ex)
            log.error("On exec error:'{}:{}' -> {}".format(
                self.client_address[0], self.client_address[1], ex))

    def sendAll(self, msg) -> None:
        '''
        向所有连接发送信息
        将出错连接踢出连接池
        '''
        msg = str(msg).encode()
        expc = []
        with self.lock:
            for c, sk in self.clients.items():
                try:
                    sk.send(msg)
                except:
                    expc.append(c)
            for c in expc:
                self.clients.pop(c)

    def error(self, code: int, msg: str) -> None:
        '''
        向连接发送异常
        '''
        sock: socket.socket = self.request
        sock.send(json.dumps({'chanel': 'Public', 'data': {
            'code': code, 'msg': msg, 'type': 'message.error'}}).encode())

    def crash(self, msg: str, ex: Exception) -> None:
        '''
        向连接发送不可预料的错误
        '''
        sock: socket.socket = self.request
        sock.send(json.dumps({'chanel': 'Public', 'data': {
            'code': 500, 'msg': msg, 'type': 'message.crash', 'except': ex}}).encode())

    def success(self, msg: str, **payloads: dict) -> None:
        '''
        向连接发送成功的信息
        '''
        sock: socket.socket = self.request
        if payloads:
            data = {'msg': msg}
            data.update(payloads)
            data.update({'code': 200, 'type': 'message.succeed'})
            sock.send(json.dumps({'chanel': 'Public', 'data': data}).encode())
        else:
            sock.send(json.dumps({'chanel': 'Public', 'data': {
                'code': 200, 'msg': msg, 'type': 'message.succeed'}}).encode())

    def ChanelRouter(self, jsonData) -> None:
        '''
        通道路由
        jsonData: 处理成功的原始信息
        '''
        try: # 找不到json的'chanel'属性
            if not jsonData['chanel'] in self.chanels:
                self.error(501, 'There is no such channel')
                return
            try: # 找不到json的'data'属性
                if not isinstance(jsonData['data'], str): # data必须是字符串
                    self.error(505, 'Wrong data type')
                    return
            except:
                self.error(506, 'You must specify parameters for data')
                return
            self.ChanelSend(jsonData['chanel'], jsonData['data']) # 发送消息
        except:
            self.error(503, 'Wrong parameter')

    def ChanelFresh(self) -> None:
        '''
        !暂时有问题
        剔除空的频道
        但不会删除公共频道
        '''
        expc = []
        for ch, ls in self.chanels:
            if len(ls) == 0 and not ch == 'Public':
                expc.append(ch)

    def ChanelJoin(self, chanelName='Public') -> None:
        '''
        加入指定的频道
        如果不存在，则创建
        '''
        try:
            a = self.chanels[chanelName]
            a[self.client_address] = self.request
        except:
            self.chanels[chanelName] = {}
            (self.chanels[chanelName])[self.client_address] = self.request

        if not chanelName == 'Public': # 不是public频道就发送消息
            self.success("Join channel '%s' succeeded" % chanelName)
            log.info("'{}:{}' joined chanel: '{}'".format(
                self.client_address[0], self.client_address[1], chanelName))

    def ChanelLeave(self, chanelName: str) -> None:
        '''
        离开指定的频道
        '''
        try:
            self.chanels[chanelName].pop(self.client_address)
        except Exception as e:
            self.error(504, 'You have not joined this channel')
            return

        self.success("Leaving channel '%s' succeeded" % chanelName)
        log.info("'{}:{}' leaved chanel: '{}'".format(
            self.client_address[0], self.client_address[1], chanelName))

    def ChanelSend(self, chanelName: str, DataString: str) -> bool:
        '''
        向指定的通道发送信息
        会将失效的连接踢出通道池
        '''
        encodedData = json.dumps(
            {'chanel': chanelName, 'data': DataString}).encode() # 构造发送数据
        expc = []
        with self.lock:
            try: # 通道不存在的情况
                for c, sk in self.chanels[chanelName].items():
                    try: # 客户端已下线等等
                        sk.send(encodedData)
                    except:
                        expc.append(c)
                for c in expc: # 剔除异常客户端
                    self.chanels[chanelName].pop(c)
                    self.clients.pop(c)
                return True
            except:
                return False


if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer((SERV, PORT), MainHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever,
                     name="server", daemon=True).start()
    log.info('Server start...')
    while True:
        cmd = input()
        if cmd.strip() == "close":
            server.shutdown()
            server.server_close()
            log.info("Server closed")
            break
        if cmd.strip() == "tread":
            log.info(threading.enumerate())
            continue
        log.info("Unknown Command:'%s'" % cmd)
