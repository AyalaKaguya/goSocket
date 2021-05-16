from . import go as mGo

__version__ = '1.0.2'
__author__ = 'AyalaKaguya <ayalakaguya@outlook.com>'
__all__ = [go]


def go(serv, port):
    return mGo.go(serv, port)
