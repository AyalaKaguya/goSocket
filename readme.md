# goSocket

## 这是什么 | What`s this?

简单的基于通道的SocketServer...

说不定能写个可以对战的游戏呢？

## 如何使用 | How to use it?

### 服务端

修改 `serv.py` ,使端口符合你的要求

```python
SERV = "127.0.0.1"
PORT = 25538
```

### 客户端

示例：

```python
import gosocket

if __name__ == "__main__":
    def abc(data: str):
        print(data)
    gosocket.go('127.0.0.1', 25538).subscribe('mro', abc).cilet_forver()
```

类 `go` 的一些方法：

构造函数提供服务器的地址和端口。

method|introduce
----|----
subscribe(chanelName: str, func) | 订阅一个通道，提供一个回调函数，一个通道只能订阅一个回调函数。
unsubscribe(chanelName: str) | 退订一个通道。
cilet_forver() | 启动事件循环，建议使用多线程。
send(chanelName: str, dataString: str) | 向指定的通道发送信息。
close() | 关闭并 `删除` 连接。

## 贡献 | Contribute

[pull requests](https://github.com/AyalaKaguya/goSocket/pulls)

## 许可 | License

本项目使用 MIT。
