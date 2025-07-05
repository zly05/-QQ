import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading


class QQClient:
    def __init__(self):
        self.client = None
        self.username = None
        self.running = False
        self.root = None
        self.chat_windows = {}  # 存储聊天窗口，键为聊天对象用户名，值为窗口相关组件字典

    def connect(self, host='localhost', port=8888):
        """连接到服务器"""
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((host, port))
            return True
        except Exception as e:
            messagebox.showerror("连接失败", f"无法连接到服务器: {e}")
            return False

    def login(self, username, password):
        """用户登录"""
        try:
            self.client.send(f"LOGIN|{username}|{password}".encode('utf-8'))
            response = self.client.recv(1024).decode('utf-8')
            status, msg = response.split('|', 1)

            if status == 'SUCCESS':
                self.username = username
                self.running = True
                threading.Thread(target=self.receive_messages, daemon=True).start()
                return True, msg
            else:
                return False, msg
        except Exception as e:
            messagebox.showerror("登录错误", f"登录过程出错: {e}")
            return False, "登录过程发生错误"

    def receive_messages(self):
        """接收服务器消息的线程"""
        while self.running:
            try:
                message = self.client.recv(1024).decode('utf-8')
                if not message:
                    self.running = False
                    self.show_system_message("与服务器的连接已断开")
                    break

                cmd, *parts = message.split('|', 2)
                if cmd == 'MSG':
                    sender, content = parts
                    # 收到消息时，只弹出接收方为目标用户的聊天窗口（非自己）
                    if sender != self.username:
                        self.show_message(sender, content)
                elif cmd == 'SYSTEM':
                    self.show_system_message(parts[0])
            except Exception as e:
                if self.running:
                    self.show_system_message(f"接收消息时出错: {e}")
                self.running = False
                break

    def show_message(self, sender, content):
        """显示收到的消息到对应聊天窗口"""
        if self.root:
            self.root.after(0, lambda: self._show_receive_message_gui(sender, content))

    def _show_receive_message_gui(self, sender, content):
        """在GUI线程中显示收到的消息（左侧）"""
        if sender not in self.chat_windows:
            self.create_chat_window(sender)

        chat_window = self.chat_windows[sender]
        chat_text = chat_window['text_widget']
        chat_text.configure(state='normal')
        # 收到的消息，显示在左侧，带发送者前缀
        chat_text.insert(tk.END, f"{sender}: {content}\n", 'receive_msg')
        chat_text.tag_configure('receive_msg', justify='left', foreground='blue')
        chat_text.configure(state='disabled')
        chat_text.see(tk.END)

    def show_system_message(self, message):
        """显示系统消息"""
        if self.root:
            self.root.after(0, lambda: self._show_system_message_gui(message))

    def _show_system_message_gui(self, message):
        """在GUI线程中显示系统消息"""
        for chat_window in self.chat_windows.values():
            text_widget = chat_window['text_widget']
            text_widget.configure(state='normal')
            text_widget.insert(tk.END, f"[系统] {message}\n", 'system_msg')
            text_widget.tag_configure('system_msg', justify='center', foreground='red')
            text_widget.configure(state='disabled')
            text_widget.see(tk.END)

    def send_message(self, to_user, content):
        """发送消息给指定用户"""
        if self.running and content.strip():
            self.client.send(f"MSG|{to_user}|{content}".encode('utf-8'))
            # 发送的消息显示在自己的聊天窗口右侧
            self._show_send_message_gui(to_user, content)
            return True
        return False

    def _show_send_message_gui(self, to_user, content):
        """显示自己发送的消息到聊天窗口（右侧）"""
        if to_user not in self.chat_windows:
            self.create_chat_window(to_user)

        chat_window = self.chat_windows[to_user]
        chat_text = chat_window['text_widget']
        chat_text.configure(state='normal')
        # 自己发送的消息，显示在右侧，带自己用户名前缀
        chat_text.insert(tk.END, f"{self.username}: {content}\n", 'send_msg')
        chat_text.tag_configure('send_msg', justify='right', foreground='green')
        chat_text.configure(state='disabled')
        chat_text.see(tk.END)

    def create_chat_window(self, recipient):
        """创建与指定用户的聊天窗口"""
        if recipient in self.chat_windows:
            self.chat_windows[recipient]['window'].lift()
            return

        window = tk.Toplevel(self.root)
        window.title(f"与 {recipient} 聊天")
        window.geometry("400x500")

        text_frame = ttk.Frame(window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(window)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        message_entry = ttk.Entry(input_frame)
        message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        message_entry.bind("<Return>", lambda event, r=recipient: self._send_message_event(r, message_entry))

        send_button = ttk.Button(input_frame, text="发送",
                                 command=lambda r=recipient: self._send_message_event(r, message_entry))
        send_button.pack(side=tk.RIGHT)

        self.chat_windows[recipient] = {
            'window': window,
            'text_widget': text_widget,
            'entry_widget': message_entry
        }

    def _send_message_event(self, recipient, entry_widget):
        """处理发送消息事件"""
        content = entry_widget.get()
        if self.send_message(recipient, content):
            entry_widget.delete(0, tk.END)

    def logout(self):
        """退出登录"""
        self.running = False
        try:
            if self.client:
                self.client.close()
        except:
            pass

        if self.root:
            self.root.destroy()

    def run(self):
        """运行客户端GUI"""
        self.root = tk.Tk()
        self.root.title("简易QQ客户端")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(login_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        username_entry = ttk.Entry(login_frame, width=20)
        username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(login_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(login_frame, width=20, show="*")
        password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()

            if not username or not password:
                messagebox.showerror("错误", "用户名和密码不能为空")
                return

            if self.connect():
                success, msg = self.login(username, password)
                if success:
                    messagebox.showinfo("成功", msg)
                    login_frame.pack_forget()
                    self.create_main_window()
                else:
                    messagebox.showerror("登录失败", msg)
                    # 关闭连接准备重试
                    try:
                        self.client.close()
                    except:
                        pass
            else:
                # 清空输入框，准备重新输入
                username_entry.delete(0, tk.END)
                password_entry.delete(0, tk.END)

        ttk.Button(login_frame, text="登录", command=do_login).grid(row=2, column=0, columnspan=2, pady=10)

        # 不再预先填充用户名和密码
        username_entry.focus_set()

        self.root.mainloop()

    def create_main_window(self):
        """创建主窗口"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"欢迎，{self.username}").pack(pady=10)

        chat_frame = ttk.LabelFrame(main_frame, text="发送消息")
        chat_frame.pack(fill=tk.X, pady=10)

        ttk.Label(chat_frame, text="发送至:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        recipient_entry = ttk.Entry(chat_frame, width=15)
        recipient_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(chat_frame, text="消息内容:").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        message_entry = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, height=3)
        message_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        def open_chat_window():
            recipient = recipient_entry.get().strip()
            if recipient and recipient != self.username:
                self.create_chat_window(recipient)
            else:
                messagebox.showerror("错误", "请输入有效的用户名")

        ttk.Button(chat_frame, text="打开聊天窗口", command=open_chat_window).grid(row=2, column=0, columnspan=2, pady=10)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(status_frame, text="状态: 已连接").pack(side=tk.LEFT, padx=10)

        def logout_action():
            if messagebox.askyesno("确认", "确定要退出登录吗？"):
                self.logout()

        ttk.Button(status_frame, text="退出登录", command=logout_action).pack(side=tk.RIGHT, padx=10)


if __name__ == "__main__":
    client = QQClient()
    client.run()
