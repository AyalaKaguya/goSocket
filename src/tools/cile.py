import socket
import threading
import sys

SERV = "127.0.0.1"
PORT = 25538

try:
    sk = socket.socket()
    sk.connect((SERV, PORT))  # 主动初始化与服务器端的连接
except Exception as e:
    print('无法连接至服务器')
    raise e

CLOSE_FLAG = False

def Reconnect():
    for i in range(3):
        try:
            sk = socket.socket()
            sk.connect((SERV, PORT))  # 主动初始化与服务器端的连接
            return True
        except Exception as e:
            continue
    raise '重新连接至服务器失败'


def tSocketBack():
    while not CLOSE_FLAG:
        try:
            accept_data = str(sk.recv(1024), encoding="utf8")
            print("".join(accept_data))
        except Exception as e:
            continue


if __name__ == '__main__':
    threading.Thread(target=tSocketBack).start()
    while True:
        send_data = input()
        if not send_data:
            continue
        
        sk.sendall(bytes(send_data, encoding="utf8"))

        if send_data == "exit":
            CLOSE_FLAG = True
            sk.close()
            break
            
    
