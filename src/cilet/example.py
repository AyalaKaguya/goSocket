import gosocket

if __name__ == "__main__":
    def abc(data: str):
        print(data)
    gosocket.go('127.0.0.1', 25538).subscribe('mro', abc).cilet_forver()