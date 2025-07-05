import socket
import threading

class QQServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.server = None
        self.clients = {}  # 存储在线用户 {用户名: 客户端套接字}
        self.lock = threading.Lock()  # 用于线程同步
        # 预设用户数据库（用户名: 密码）
        self.users = {
            'user1': '123456',
            'user2': '654321'
        }
    
    def start(self):
        """启动服务器"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"服务器已启动，监听地址: {self.host}:{self.port}")
        
        # 开始接受客户端连接
        while True:
            client_socket, client_address = self.server.accept()
            print(f"新连接来自: {client_address}")
            # 为每个客户端创建一个线程
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()
    
    def handle_client(self, client_socket):
        """处理客户端连接"""
        username = None
        
        try:
            # 验证用户登录
            login_data = client_socket.recv(1024).decode('utf-8')
            cmd, user, pwd = login_data.split('|', 2)
            
            if cmd == 'LOGIN':
                if self.validate_user(user, pwd):
                    with self.lock:
                        if user in self.clients:
                            client_socket.send("FAIL|该用户已登录".encode('utf-8'))
                            return
                        
                        self.clients[user] = client_socket
                        username = user
                        client_socket.send("SUCCESS|登录成功".encode('utf-8'))
                    
                    # 在锁外广播，避免阻塞其他客户端
                    self.broadcast_system_message(f"{user} 上线了")
                    print(f"{user} 登录成功")
                else:
                    client_socket.send("FAIL|用户名或密码错误".encode('utf-8'))
                    return
            else:
                client_socket.send("FAIL|无效的命令".encode('utf-8'))
                return
            
            # 处理客户端消息
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                cmd, *parts = data.split('|', 2)
                if cmd == 'MSG':
                    to_user, content = parts
                    self.forward_message(username, to_user, content)
                else:
                    print(f"收到无效命令: {data}")
        
        except Exception as e:
            print(f"处理客户端时出错: {e}")
        finally:
            # 用户下线处理
            if username and username in self.clients:
                # 先删除用户，关闭套接字
                with self.lock:
                    client = self.clients.pop(username, None)
                    if client:
                        try:
                            client.close()
                        except:
                            pass
                
                # 在锁外广播下线消息
                self.broadcast_system_message(f"{username} 下线了")
                print(f"{username} 已下线")
    
    def validate_user(self, username, password):
        """验证用户登录"""
        return username in self.users and self.users[username] == password
    
    def forward_message(self, sender, recipient, content):
        """转发消息给目标用户"""
        with self.lock:
            if recipient in self.clients:
                try:
                    msg = f"MSG|{sender}|{content}"
                    self.clients[recipient].send(msg.encode('utf-8'))
                except Exception as e:
                    print(f"转发消息给 {recipient} 失败: {e}")
            else:
                try:
                    error_msg = f"SYSTEM|用户 {recipient} 不在线"
                    self.clients[sender].send(error_msg.encode('utf-8'))
                except Exception as e:
                    print(f"发送错误消息给 {sender} 失败: {e}")
    
    def broadcast_system_message(self, message):
        """广播系统消息给所有在线用户"""
        # 复制用户列表，减少锁的持有时间
        with self.lock:
            clients_copy = list(self.clients.values())
        
        # 在锁外进行广播
        for client in clients_copy:
            try:
                client.send(f"SYSTEM|{message}".encode('utf-8'))
            except Exception as e:
                print(f"发送系统消息失败: {e}")


if __name__ == "__main__":
    server = QQServer()
    server.start()    
