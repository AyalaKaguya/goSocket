import logging
import sys
import socketserver
import socket
import threading
import json

SERV = "127.0.0.1"
PORT = 25538

logging.basicConfig(format="%(asctime)s %(thread)d %(threadName)s %(message)s",
                    stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()

CodingFormat = "utf-8"  # 定义全局编码格式

'''一些定义
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

        with self.lock:
            self.clients[self.client_address] = self.request
            self.ChanelJoin()
            for c, sk in self.clients.items():  # 递归连接池，连接发送信息
                try:
                    sk.send(msg)
                except:
                    pass

        log.info("Connection:'{}:{}'".format(
            self.client_address[0], self.client_address[1]))

    def handle(self):
        super().handle()
        sock: socket.socket = self.request

        while not self.event.is_set():

            try:
                data = sock.recv(1024).decode(CodingFormat)
            except Exception as e:
                log.error(e)
                break

            if not data or data == '':
                continue
            elif data in {'exit'}:
                break

            try:
                jsonData = json.loads(data)
            except:
                self.PublicExec(data.split(' '), sock)
                continue

            '''
            以下处理消息事件
            '''
            self.ChanelRouter(jsonData, sock, data)

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

    def PublicExec(self, command, sock):
        try:
            if command[0] == 'send':
                msg = "[{}:{}]:{}".format(
                    self.client_address[0], self.client_address[1], ' '.join(command[1:]))
                self.ChanelSend('Public', msg)
                return
            elif command[0] == 'help':
                msg = help_document.encode()
                sock.send(msg)
                return
            elif command[0] == 'join':
                if len(command) < 2:
                    sock.send(json.dumps({'chanel': 'Public', 'data': {
                        'code': 502, 'msg': '请输入频道名称', 'type': 'message.error'}}).encode())
                    return
                self.ChanelJoin(command[1])
                sock.send(json.dumps({'chanel': 'Public', 'data': {
                    'code': 200, 'msg': "加入频道'%s'成功" % command[1], 'type': 'message.succeed'}}).encode())
                return
            elif command[0] == 'leave':
                if len(command) < 2:
                    sock.send(json.dumps({'chanel': 'Public', 'data': {
                        'code': 502, 'msg': '请输入频道名称', 'type': 'message.error'}}).encode())
                self.ChanelLeave(command[1])
                return
            elif command[0] == 'back_def':
                msg = back_def_document.encode()
                sock.send(msg)
                return

            sock.send("Server Error:\n\tUndefined command '{}'\n\tType 'help' to get some commands.".format(
                ' '.join(command)).encode())
        except Exception as ex:
            sock.send(json.dumps({'chanel': 'Public', 'data': {
                'code': 500, 'msg': 'Server Error！', 'type': 'message.crash', 'except': ex}}).encode())
            log.error("On exec error:'{}:{}' -> {}".format(
                self.client_address[0], self.client_address[1], ex))

    def ChanelRouter(self, jsonData, sock, data):
        try:
            if not jsonData['chanel'] in self.chanels:
                sock.send(json.dumps({'chanel': 'Public', 'data': {
                    'code': 501, 'msg': '没有这个频道', 'type': 'message.error'}}).encode())
            self.ChanelSend(jsonData['chanel'], data)
        except:
            sock.send(json.dumps({'chanel': 'Public', 'data': {
                      'code': 503, 'msg': '错误的参数', 'type': 'message.error'}}).encode())

    def ChanelFresh(self):
        '''
        !暂时有问题
        剔除空的频道
        但不会删除公共频道
        '''
        expc = []
        for ch, ls in self.chanels:
            if len(ls) == 0 and not ch == 'Public':
                expc.append(ch)

    def ChanelJoin(self, chanelName='Public'):
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
        log.info("'{}:{}' joined chanel: '{}'".format(
            self.client_address[0], self.client_address[1], chanelName))

    def ChanelLeave(self, chanelName):
        sock: socket.socket = self.request
        '''
        离开指定的频道
        '''
        try:
            self.chanels[chanelName].pop(self.client_address)
        except Exception as e:
            sock.send(json.dumps({'chanel': 'Public', 'data': {
                'code': 504, 'msg': '尚未加入此频道', 'type': 'message.error'}}).encode())
            return e

        sock.send(json.dumps({'chanel': 'Public', 'data': {
            'code': 200, 'msg': "离开频道'%s'成功" % chanelName, 'type': 'message.succeed'}}).encode())
        log.info("'{}:{}' leaved chanel: '{}'".format(
            self.client_address[0], self.client_address[1], chanelName))

    def ChanelSend(self, chanelName: str, DataString: str):
        '''
        向指定的通道发送信息
        会将失效的连接踢出通道池
        '''
        encodedData = str(DataString).encode()
        expc = []
        with self.lock:
            try:
                for c, sk in self.chanels[chanelName].items():
                    try:
                        sk.send(encodedData)
                    except:
                        expc.append(c)
                for c in expc:
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
