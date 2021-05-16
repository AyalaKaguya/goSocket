from . import go as mGo

__version__ = '1.0.2'
__author__ = 'AyalaKaguya <ayalakaguya@outlook.com>'
__all__ = [go]


def go(serv: str, port: int) -> mGo.go:
    """
    创建一个goSocket客户端实例

    serv: 服务器地址
    port: 服务器端口
    """
    return mGo.go(serv, port)
