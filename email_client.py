import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import imaplib
import poplib
import email
from email.header import decode_header
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import json
import threading
import webbrowser
from datetime import datetime


class EmailClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Yanyn Email")
        self.root.geometry("1000x700")

        # 蓝色主题配置
        self.bg_color = "#e6f2ff"
        self.button_color = "#4d94ff"
        self.active_button_color = "#1a75ff"
        self.text_color = "#003366"
        self.listbox_color = "#ffffff"

        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TButton", background=self.button_color, foreground=self.text_color)
        self.style.map("TButton",
                       background=[("active", self.active_button_color)],
                       foreground=[("active", "white")])
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        self.style.configure("Treeview", background=self.listbox_color, fieldbackground=self.listbox_color)

        # 邮箱账户存储
        self.accounts = []
        self.current_account = None
        self.load_accounts()

        # 创建UI
        self.create_ui()

        # 自动登录第一个账户
        if self.accounts:
            self.current_account = self.accounts[0]
            self.update_account_display()
            self.check_email()

    def create_ui(self):
        # 主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧账户和文件夹面板
        self.left_panel = ttk.Frame(self.main_frame, width=200)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 账户列表
        self.account_frame = ttk.LabelFrame(self.left_panel, text="邮箱账户")
        self.account_frame.pack(fill=tk.X, pady=(0, 10))

        self.account_listbox = tk.Listbox(self.account_frame, height=5, bg=self.listbox_color)
        self.account_listbox.pack(fill=tk.X)
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)

        self.refresh_account_list()

        # 添加/删除账户按钮
        self.account_button_frame = ttk.Frame(self.account_frame)
        self.account_button_frame.pack(fill=tk.X, pady=(5, 0))

        self.add_account_btn = ttk.Button(self.account_button_frame, text="添加", command=self.show_add_account_dialog)
        self.add_account_btn.pack(side=tk.LEFT, expand=True)

        self.edit_account_btn = ttk.Button(self.account_button_frame, text="编辑",
                                           command=self.show_edit_account_dialog)
        self.edit_account_btn.pack(side=tk.LEFT, expand=True)

        self.del_account_btn = ttk.Button(self.account_button_frame, text="删除", command=self.delete_account)
        self.del_account_btn.pack(side=tk.LEFT, expand=True)

        # 文件夹列表
        self.folder_frame = ttk.LabelFrame(self.left_panel, text="文件夹")
        self.folder_frame.pack(fill=tk.BOTH, expand=True)

        self.folder_tree = ttk.Treeview(self.folder_frame, show="tree", selectmode="browse")
        self.folder_tree.pack(fill=tk.BOTH, expand=True)
        self.folder_tree.bind("<<TreeviewSelect>>", self.on_folder_select)

        # 右侧邮件和内容面板
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 邮件列表
        self.email_list_frame = ttk.LabelFrame(self.right_panel, text="邮件列表")
        self.email_list_frame.pack(fill=tk.BOTH, expand=True)

        self.email_tree = ttk.Treeview(
            self.email_list_frame,
            columns=("from", "subject", "date"),
            show="headings"
        )
        self.email_tree.pack(fill=tk.BOTH, expand=True)

        self.email_tree.heading("from", text="发件人")
        self.email_tree.heading("subject", text="主题")
        self.email_tree.heading("date", text="日期")

        self.email_tree.column("from", width=150)
        self.email_tree.column("subject", width=300)
        self.email_tree.column("date", width=120)

        self.email_tree.bind("<<TreeviewSelect>>", self.on_email_select)

        # 邮件内容
        self.email_content_frame = ttk.LabelFrame(self.right_panel, text="邮件内容")
        self.email_content_frame.pack(fill=tk.BOTH, expand=True)

        self.email_content = tk.Text(
            self.email_content_frame,
            wrap=tk.WORD,
            bg=self.listbox_color,
            padx=10,
            pady=10
        )
        self.email_content.pack(fill=tk.BOTH, expand=True)

        # 工具栏
        self.toolbar_frame = ttk.Frame(self.right_panel)
        self.toolbar_frame.pack(fill=tk.X, pady=(5, 0))

        self.refresh_btn = ttk.Button(self.toolbar_frame, text="刷新", command=self.check_email)
        self.refresh_btn.pack(side=tk.LEFT)

        self.compose_btn = ttk.Button(self.toolbar_frame, text="写邮件", command=self.show_compose_dialog)
        self.compose_btn.pack(side=tk.LEFT)

        self.reply_btn = ttk.Button(self.toolbar_frame, text="回复", command=self.reply_email)
        self.reply_btn.pack(side=tk.LEFT)

        self.forward_btn = ttk.Button(self.toolbar_frame, text="转发", command=self.forward_email)
        self.forward_btn.pack(side=tk.LEFT)

        self.delete_btn = ttk.Button(self.toolbar_frame, text="删除", command=self.delete_email)
        self.delete_btn.pack(side=tk.LEFT)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X)

        # 附件列表
        self.attachment_frame = ttk.LabelFrame(self.right_panel, text="附件")
        self.attachment_frame.pack(fill=tk.X)

        self.attachment_listbox = tk.Listbox(
            self.attachment_frame,
            height=3,
            bg=self.listbox_color
        )
        self.attachment_listbox.pack(fill=tk.X)
        self.attachment_listbox.bind("<Double-Button-1>", self.open_attachment)

    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for account in self.accounts:
            self.account_listbox.insert(tk.END, account["email"])

    def load_accounts(self):
        try:
            with open("accounts.json", "r") as f:
                self.accounts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.accounts = []

    def save_accounts(self):
        with open("accounts.json", "w") as f:
            json.dump(self.accounts, f, indent=2)

    def on_account_select(self, event):
        selection = self.account_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_account = self.accounts[index]
            self.update_account_display()
            self.check_email()

    def update_account_display(self):
        if self.current_account:
            self.root.title(f"BlueMail - {self.current_account['email']}")
            self.update_folder_list()

    def update_folder_list(self):
        self.folder_tree.delete(*self.folder_tree.get_children())

        if not self.current_account:
            return

        # 添加默认文件夹
        folders = ["收件箱", "已发送", "草稿箱", "垃圾邮件", "已删除"]
        for folder in folders:
            self.folder_tree.insert("", tk.END, text=folder, values=(folder.lower(),))

        # 如果是IMAP，可以获取服务器上的文件夹
        if self.current_account["protocol"] == "imap":
            try:
                self.status_var.set("正在连接服务器获取文件夹列表...")
                self.root.update()

                if self.current_account["ssl"]:
                    mail = imaplib.IMAP4_SSL(self.current_account["incoming_server"],
                                             int(self.current_account["incoming_port"]))
                else:
                    mail = imaplib.IMAP4(self.current_account["incoming_server"],
                                         int(self.current_account["incoming_port"]))

                mail.login(self.current_account["email"], self.current_account["password"])
                status, folders = mail.list()

                if status == "OK":
                    for folder_info in folders:
                        folder_name = folder_info.decode().split('"/"')[-1].strip('"')
                        if folder_name.lower() not in ["inbox", "sent", "drafts", "junk", "trash"]:
                            self.folder_tree.insert("", tk.END, text=folder_name, values=(folder_name.lower(),))

                mail.logout()
                self.status_var.set("文件夹列表已更新")
            except Exception as e:
                messagebox.showerror("错误", f"获取文件夹列表失败: {str(e)}")
                self.status_var.set("获取文件夹列表失败")

    def on_folder_select(self, event):
        selection = self.folder_tree.selection()
        if selection:
            folder = self.folder_tree.item(selection[0], "values")[0]
            self.check_email(folder)

    def check_email(self, folder="inbox"):
        if not self.current_account:
            return

        self.email_tree.delete(*self.email_tree.get_children())
        self.email_content.delete(1.0, tk.END)
        self.attachment_listbox.delete(0, tk.END)

        self.status_var.set("正在检查邮件...")
        self.root.update()

        try:
            if self.current_account["protocol"] == "imap":
                self.check_email_imap(folder)
            else:
                self.check_email_pop3()

            self.status_var.set("邮件检查完成")
        except Exception as e:
            messagebox.showerror("错误", f"检查邮件失败: {str(e)}")
            self.status_var.set("检查邮件失败")

    def check_email_imap(self, folder="inbox"):
        if self.current_account["ssl"]:
            mail = imaplib.IMAP4_SSL(self.current_account["incoming_server"],
                                     int(self.current_account["incoming_port"]))
        else:
            mail = imaplib.IMAP4(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.login(self.current_account["email"], self.current_account["password"])

        # 选择文件夹
        if folder.lower() == "sent":
            folder_name = "sent"
        elif folder.lower() == "drafts":
            folder_name = "drafts"
        elif folder.lower() == "trash":
            folder_name = "trash"
        elif folder.lower() == "junk":
            folder_name = "junk"
        else:
            folder_name = "inbox"

        mail.select(folder_name)

        # 搜索邮件
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            raise Exception("搜索邮件失败")

        message_ids = messages[0].split()

        # 获取最新的50封邮件
        for msg_id in message_ids[-50:]:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # 解析邮件头
            from_ = self.decode_header(email_message["From"])
            subject = self.decode_header(email_message["Subject"])
            date = self.decode_header(email_message["Date"])

            # 简化日期显示
            try:
                date_obj = email.utils.parsedate_to_datetime(date)
                date_str = date_obj.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = date

            self.email_tree.insert("", tk.END, values=(from_, subject, date_str), iid=msg_id.decode())

        mail.logout()

    def check_email_pop3(self):
        if self.current_account["ssl"]:
            mail = poplib.POP3_SSL(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))
        else:
            mail = poplib.POP3(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.user(self.current_account["email"])
        mail.pass_(self.current_account["password"])

        # 获取邮件数量和大小
        num_messages = len(mail.list()[1])

        # 获取最新的20封邮件
        for i in range(max(1, num_messages - 19), num_messages + 1):
            try:
                response, lines, octets = mail.retr(i)
                raw_email = b"\n".join(lines)
                email_message = email.message_from_bytes(raw_email)

                # 解析邮件头
                from_ = self.decode_header(email_message["From"])
                subject = self.decode_header(email_message["Subject"])
                date = self.decode_header(email_message["Date"])

                # 简化日期显示
                try:
                    date_obj = email.utils.parsedate_to_datetime(date)
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = date

                self.email_tree.insert("", tk.END, values=(from_, subject, date_str), iid=str(i))
            except:
                continue

        mail.quit()

    def on_email_select(self, event):
        selection = self.email_tree.selection()
        if not selection:
            return

        self.email_content.delete(1.0, tk.END)
        self.attachment_listbox.delete(0, tk.END)

        msg_id = selection[0]
        self.current_email_id = msg_id

        try:
            if self.current_account["protocol"] == "imap":
                self.display_email_imap(msg_id)
            else:
                self.display_email_pop3(msg_id)
        except Exception as e:
            messagebox.showerror("错误", f"显示邮件失败: {str(e)}")

    def display_email_imap(self, msg_id):
        if self.current_account["ssl"]:
            mail = imaplib.IMAP4_SSL(self.current_account["incoming_server"],
                                     int(self.current_account["incoming_port"]))
        else:
            mail = imaplib.IMAP4(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.login(self.current_account["email"], self.current_account["password"])

        # 选择收件箱
        mail.select("inbox")

        # 获取邮件
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            raise Exception("获取邮件失败")

        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        self.process_email_message(email_message)

        mail.logout()

    def display_email_pop3(self, msg_id):
        if self.current_account["ssl"]:
            mail = poplib.POP3_SSL(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))
        else:
            mail = poplib.POP3(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.user(self.current_account["email"])
        mail.pass_(self.current_account["password"])

        # 获取邮件
        response, lines, octets = mail.retr(int(msg_id))
        raw_email = b"\n".join(lines)
        email_message = email.message_from_bytes(raw_email)

        self.process_email_message(email_message)

        mail.quit()

    def process_email_message(self, email_message):
        # 解析邮件头
        from_ = self.decode_header(email_message["From"])
        to = self.decode_header(email_message["To"])
        subject = self.decode_header(email_message["Subject"])
        date = self.decode_header(email_message["Date"])

        # 显示邮件头
        self.email_content.insert(tk.END, f"发件人: {from_}\n")
        self.email_content.insert(tk.END, f"收件人: {to}\n")
        self.email_content.insert(tk.END, f"主题: {subject}\n")
        self.email_content.insert(tk.END, f"日期: {date}\n")
        self.email_content.insert(tk.END, "\n" + "=" * 50 + "\n\n")

        # 解析邮件内容
        self.current_email_attachments = []

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # 附件
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self.decode_header(filename)
                        self.attachment_listbox.insert(tk.END, filename)
                        self.current_email_attachments.append((filename, part))
                # 邮件正文
                elif content_type == "text/plain":
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    self.email_content.insert(tk.END, body)
                elif content_type == "text/html":
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    # 简单显示HTML内容
                    self.email_content.insert(tk.END, self.strip_html(body))
        else:
            body = email_message.get_payload(decode=True).decode(email_message.get_content_charset() or "utf-8",
                                                                 errors="ignore")
            self.email_content.insert(tk.END, body)

    def open_attachment(self, event):
        selection = self.attachment_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        filename = self.attachment_listbox.get(index)

        # 保存附件到临时文件夹
        temp_dir = os.path.join(os.getcwd(), "temp_attachments")
        os.makedirs(temp_dir, exist_ok=True)
        filepath = os.path.join(temp_dir, filename)

        for attachment in self.current_email_attachments:
            if attachment[0] == filename:
                with open(filepath, "wb") as f:
                    f.write(attachment[1].get_payload(decode=True))
                break

        # 打开附件
        try:
            os.startfile(filepath)
        except:
            messagebox.showinfo("打开附件", f"附件已保存到: {filepath}")

    def strip_html(self, html):
        # 简单的HTML标签去除
        import re
        clean = re.compile("<.*?>")
        return re.sub(clean, "", html)

    def decode_header(self, header):
        if header is None:
            return ""

        decoded_parts = decode_header(header)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    result.append(part.decode(encoding))
                else:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        return "".join(result)

    def show_add_account_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("添加账户")
        dialog.geometry("650x450")
        dialog.resizable(False, False)

        # 蓝色主题
        dialog.configure(bg=self.bg_color)

        # 表单框架
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # 邮箱地址
        ttk.Label(form_frame, text="邮箱地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        email_entry = ttk.Entry(form_frame, width=40)
        email_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # 显示名称
        #ttk.Label(form_frame, text="显示名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        #name_entry = ttk.Entry(form_frame, width=40)
        #name_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(form_frame, width=40, show="*")
        password_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        # 协议选择
        ttk.Label(form_frame, text="协议:").grid(row=3, column=0, sticky=tk.W, pady=5)
        protocol_var = tk.StringVar(value="imap")
        protocol_imap = ttk.Radiobutton(form_frame, text="IMAP", variable=protocol_var, value="imap")
        protocol_imap.grid(row=3, column=1, sticky=tk.W, pady=5)
        #protocol_pop3 = ttk.Radiobutton(form_frame, text="POP3", variable=protocol_var, value="pop3")
        #protocol_pop3.grid(row=3, column=1, sticky=tk.E, pady=5)

        # 服务器设置框架
        server_frame = ttk.LabelFrame(form_frame, text="服务器设置")
        server_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W + tk.E, pady=10)

        # 接收服务器
        ttk.Label(server_frame, text="接收邮件服务器:").grid(row=0, column=0, sticky=tk.W, pady=5)
        incoming_server_entry = ttk.Entry(server_frame, width=30)
        incoming_server_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(server_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, pady=5)
        incoming_port_entry = ttk.Entry(server_frame, width=10)
        incoming_port_entry.grid(row=0, column=3, sticky=tk.W, pady=5)

        # SSL
        incoming_ssl_var = tk.IntVar(value=1)
        incoming_ssl_check = ttk.Checkbutton(server_frame, text="SSL", variable=incoming_ssl_var)
        incoming_ssl_check.grid(row=0, column=4, sticky=tk.W, pady=5)

        # 发送服务器
        ttk.Label(server_frame, text="发送邮件服务器:").grid(row=1, column=0, sticky=tk.W, pady=5)
        outgoing_server_entry = ttk.Entry(server_frame, width=30)
        outgoing_server_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(server_frame, text="端口:").grid(row=1, column=2, sticky=tk.W, pady=5)
        outgoing_port_entry = ttk.Entry(server_frame, width=10)
        outgoing_port_entry.grid(row=1, column=3, sticky=tk.W, pady=5)

        # SSL
        outgoing_ssl_var = tk.IntVar(value=1)
        outgoing_ssl_check = ttk.Checkbutton(server_frame, text="SSL", variable=outgoing_ssl_var)
        outgoing_ssl_check.grid(row=1, column=4, sticky=tk.W, pady=5)

        # 常见邮箱预设
        def set_preset(preset):
            if preset == "qq":
                incoming_server_entry.delete(0, tk.END)
                incoming_server_entry.insert(0, "imap.qq.com")
                incoming_port_entry.delete(0, tk.END)
                incoming_port_entry.insert(0, "993")
                incoming_ssl_var.set(1)

                outgoing_server_entry.delete(0, tk.END)
                outgoing_server_entry.insert(0, "smtp.qq.com")
                outgoing_port_entry.delete(0, tk.END)
                outgoing_port_entry.insert(0, "465")
                outgoing_ssl_var.set(1)
            elif preset == "163":
                incoming_server_entry.delete(0, tk.END)
                incoming_server_entry.insert(0, "imap.163.com")
                incoming_port_entry.delete(0, tk.END)
                incoming_port_entry.insert(0, "993")
                incoming_ssl_var.set(1)

                outgoing_server_entry.delete(0, tk.END)
                outgoing_server_entry.insert(0, "smtp.163.com")
                outgoing_port_entry.delete(0, tk.END)
                outgoing_port_entry.insert(0, "465")
                outgoing_ssl_var.set(1)
            elif preset == "sina":
                incoming_server_entry.delete(0, tk.END)
                incoming_server_entry.insert(0, "imap.sina.com")
                incoming_port_entry.delete(0, tk.END)
                incoming_port_entry.insert(0, "993")
                incoming_ssl_var.set(1)

                outgoing_server_entry.delete(0, tk.END)
                outgoing_server_entry.insert(0, "smtp.sina.com")
                outgoing_port_entry.delete(0, tk.END)
                outgoing_port_entry.insert(0, "465")
                outgoing_ssl_var.set(1)

            elif preset == "outlook":
                incoming_server_entry.delete(0, tk.END)
                incoming_server_entry.insert(0, "outlook.office365.com")
                incoming_port_entry.delete(0, tk.END)
                incoming_port_entry.insert(0, "993")
                incoming_ssl_var.set(1)

                outgoing_server_entry.delete(0, tk.END)
                outgoing_server_entry.insert(0, "smtp-mail.outlook.com")
                outgoing_port_entry.delete(0, tk.END)
                outgoing_port_entry.insert(0, "587")
                outgoing_ssl_var.set(1)

            elif preset == "yanyn":
                incoming_server_entry.delete(0, tk.END)
                incoming_server_entry.insert(0, "yanyn.cn")
                incoming_port_entry.delete(0, tk.END)
                incoming_port_entry.insert(0, "143")
                incoming_ssl_var.set(0)

                outgoing_server_entry.delete(0, tk.END)
                outgoing_server_entry.insert(0, "yanyn.cn")
                outgoing_port_entry.delete(0, tk.END)
                outgoing_port_entry.insert(0, "25")
                outgoing_ssl_var.set(0)

        # 预设按钮
        preset_frame = ttk.Frame(form_frame)
        preset_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Label(preset_frame, text="预设:").pack(side=tk.LEFT)
        ttk.Button(preset_frame, text="QQ邮箱", command=lambda: set_preset("qq")).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="163邮箱", command=lambda: set_preset("163")).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="新浪邮箱", command=lambda: set_preset("sina")).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="Outlook邮箱", command=lambda: set_preset("outlook")).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="晏阳邮箱", command=lambda: set_preset("yanyn")).pack(side=tk.LEFT, padx=5)

        # 按钮框架
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)

        def save_account():
            account = {
                "email": email_entry.get(),
                #"name": name_entry.get(),
                "password": password_entry.get(),
                "protocol": protocol_var.get(),
                "incoming_server": incoming_server_entry.get(),
                "incoming_port": incoming_port_entry.get(),
                "incoming_ssl": bool(incoming_ssl_var.get()),
                "outgoing_server": outgoing_server_entry.get(),
                "outgoing_port": outgoing_port_entry.get(),
                "outgoing_ssl": bool(outgoing_ssl_var.get()),
                "ssl": bool(incoming_ssl_var.get())
            }

            # 验证必填字段
            if not account["email"] or not account["password"]:
                messagebox.showerror("错误", "邮箱地址和密码是必填项")
                return

            if not account["incoming_server"] or not account["incoming_port"]:
                messagebox.showerror("错误", "接收邮件服务器和端口是必填项")
                return

            if not account["outgoing_server"] or not account["outgoing_port"]:
                messagebox.showerror("错误", "发送邮件服务器和端口是必填项")
                return

            # 添加到账户列表
            self.accounts.append(account)
            self.save_accounts()
            self.refresh_account_list()
            dialog.destroy()

        ttk.Button(button_frame, text="保存", command=save_account).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def show_edit_account_dialog(self):
        if not self.current_account:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("编辑邮箱账户")
        dialog.geometry("500x400")
        dialog.resizable(False, False)

        # 蓝色主题
        dialog.configure(bg=self.bg_color)

        # 表单框架
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill=tk.BOTH, padx=10, pady=10)

        # 邮箱地址
        ttk.Label(form_frame, text="邮箱地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        email_entry = ttk.Entry(form_frame, width=40)
        email_entry.insert(0, self.current_account["email"])
        email_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        email_entry.config(state="readonly")

        # 显示名称
        ttk.Label(form_frame, text="显示名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(form_frame, width=40)
        name_entry.insert(0, self.current_account.get("name", ""))
        name_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(form_frame, width=40, show="*")
        password_entry.insert(0, self.current_account["password"])
        password_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        # 协议选择
        ttk.Label(form_frame, text="协议:").grid(row=3, column=0, sticky=tk.W, pady=5)
        protocol_var = tk.StringVar(value=self.current_account["protocol"])
        protocol_imap = ttk.Radiobutton(form_frame, text="IMAP", variable=protocol_var, value="imap")
        protocol_imap.grid(row=3, column=1, sticky=tk.W, pady=5)
        protocol_pop3 = ttk.Radiobutton(form_frame, text="POP3", variable=protocol_var, value="pop3")
        protocol_pop3.grid(row=3, column=1, sticky=tk.E, pady=5)

        # 服务器设置框架
        server_frame = ttk.LabelFrame(form_frame, text="服务器设置")
        server_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W + tk.E, pady=10)

        # 接收服务器
        ttk.Label(server_frame, text="接收邮件服务器:").grid(row=0, column=0, sticky=tk.W, pady=5)
        incoming_server_entry = ttk.Entry(server_frame, width=30)
        incoming_server_entry.insert(0, self.current_account["incoming_server"])
        incoming_server_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(server_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, pady=5)
        incoming_port_entry = ttk.Entry(server_frame, width=10)
        incoming_port_entry.insert(0, self.current_account["incoming_port"])
        incoming_port_entry.grid(row=0, column=3, sticky=tk.W, pady=5)

        # SSL
        incoming_ssl_var = tk.IntVar(value=int(self.current_account["incoming_ssl"]))
        incoming_ssl_check = ttk.Checkbutton(server_frame, text="SSL", variable=incoming_ssl_var)
        incoming_ssl_check.grid(row=0, column=4, sticky=tk.W, pady=5)

        # 发送服务器
        ttk.Label(server_frame, text="发送邮件服务器:").grid(row=1, column=0, sticky=tk.W, pady=5)
        outgoing_server_entry = ttk.Entry(server_frame, width=30)
        outgoing_server_entry.insert(0, self.current_account["outgoing_server"])
        outgoing_server_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(server_frame, text="端口:").grid(row=1, column=2, sticky=tk.W, pady=5)
        outgoing_port_entry = ttk.Entry(server_frame, width=10)
        outgoing_port_entry.insert(0, self.current_account["outgoing_port"])
        outgoing_port_entry.grid(row=1, column=3, sticky=tk.W, pady=5)

        # SSL
        outgoing_ssl_var = tk.IntVar(value=int(self.current_account["outgoing_ssl"]))
        outgoing_ssl_check = ttk.Checkbutton(server_frame, text="SSL", variable=outgoing_ssl_var)
        outgoing_ssl_check.grid(row=1, column=4, sticky=tk.W, pady=5)

        # 按钮框架
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        def save_changes():
            account = {
                "email": email_entry.get(),
                "name": name_entry.get(),
                "password": password_entry.get(),
                "protocol": protocol_var.get(),
                "incoming_server": incoming_server_entry.get(),
                "incoming_port": incoming_port_entry.get(),
                "incoming_ssl": bool(incoming_ssl_var.get()),
                "outgoing_server": outgoing_server_entry.get(),
                "outgoing_port": outgoing_port_entry.get(),
                "outgoing_ssl": bool(outgoing_ssl_var.get()),
                "ssl": bool(incoming_ssl_var.get())
            }

            # 验证必填字段
            if not account["email"] or not account["password"]:
                messagebox.showerror("错误", "邮箱地址和密码是必填项")
                return

            if not account["incoming_server"] or not account["incoming_port"]:
                messagebox.showerror("错误", "接收邮件服务器和端口是必填项")
                return

            if not account["outgoing_server"] or not account["outgoing_port"]:
                messagebox.showerror("错误", "发送邮件服务器和端口是必填项")
                return

            # 更新账户
            index = self.accounts.index(self.current_account)
            self.accounts[index] = account
            self.current_account = account
            self.save_accounts()
            self.refresh_account_list()
            dialog.destroy()

        ttk.Button(button_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def delete_account(self):
        if not self.current_account:
            return

        if messagebox.askyesno("确认", f"确定要删除账户 {self.current_account['email']} 吗？"):
            self.accounts.remove(self.current_account)
            self.save_accounts()
            self.refresh_account_list()

            if self.accounts:
                self.current_account = self.accounts[0]
                self.update_account_display()
            else:
                self.current_account = None
                self.root.title("BlueMail - Python邮件客户端")
                self.folder_tree.delete(*self.folder_tree.get_children())
                self.email_tree.delete(*self.email_tree.get_children())
                self.email_content.delete(1.0, tk.END)
                self.attachment_listbox.delete(0, tk.END)

    def show_compose_dialog(self, reply_to=None, forward_msg=None):
        if not self.current_account:
            messagebox.showerror("错误", "请先选择一个邮箱账户")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("写邮件")
        dialog.geometry("800x600")

        # 蓝色主题
        dialog.configure(bg=self.bg_color)

        # 表单框架
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)

        # 收件人
        ttk.Label(form_frame, text="收件人:").grid(row=0, column=0, sticky=tk.W, pady=5)
        to_entry = ttk.Entry(form_frame, width=80)
        to_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # 抄送
        ttk.Label(form_frame, text="抄送:").grid(row=1, column=0, sticky=tk.W, pady=5)
        cc_entry = ttk.Entry(form_frame, width=80)
        cc_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 密送
        ttk.Label(form_frame, text="密送:").grid(row=2, column=0, sticky=tk.W, pady=5)
        bcc_entry = ttk.Entry(form_frame, width=80)
        bcc_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        # 主题
        ttk.Label(form_frame, text="主题:").grid(row=3, column=0, sticky=tk.W, pady=5)
        subject_entry = ttk.Entry(form_frame, width=80)
        subject_entry.grid(row=3, column=1, sticky=tk.W, pady=5)

        # 邮件内容
        content_text = tk.Text(form_frame, wrap=tk.WORD, height=20, width=80)
        content_text.grid(row=4, column=0, columnspan=2, pady=10)

        # 如果是回复或转发，填充相应内容
        if reply_to:
            msg = reply_to
            to_entry.insert(0, msg["from"])
            subject = msg["subject"]
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            subject_entry.insert(0, subject)

            # 添加引用内容
            content_text.insert(tk.END, f"\n\n----- 原始邮件 -----\n")
            content_text.insert(tk.END, f"发件人: {msg['from']}\n")
            content_text.insert(tk.END, f"日期: {msg['date']}\n")
            content_text.insert(tk.END, f"主题: {msg['subject']}\n\n")
            content_text.insert(tk.END, msg.get("body", ""))
        elif forward_msg:
            msg = forward_msg
            subject = msg["subject"]
            if not subject.startswith("Fw:"):
                subject = f"Fw: {subject}"
            subject_entry.insert(0, subject)

            # 添加转发内容
            content_text.insert(tk.END, f"\n\n----- 转发邮件 -----\n")
            content_text.insert(tk.END, f"发件人: {msg['from']}\n")
            content_text.insert(tk.END, f"日期: {msg['date']}\n")
            content_text.insert(tk.END, f"主题: {msg['subject']}\n\n")
            content_text.insert(tk.END, msg.get("body", ""))

        # 附件列表
        self.compose_attachments = []
        attachment_frame = ttk.LabelFrame(form_frame, text="附件")
        attachment_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W + tk.E, pady=5)

        self.attachment_list = tk.Listbox(attachment_frame, height=3, width=80)
        self.attachment_list.pack(fill=tk.X)

        # 添加附件按钮
        def add_attachment():
            filenames = filedialog.askopenfilenames(title="选择附件")
            for filename in filenames:
                self.compose_attachments.append(filename)
                self.attachment_list.insert(tk.END, os.path.basename(filename))

        def remove_attachment():
            selection = self.attachment_list.curselection()
            if selection:
                index = selection[0]
                self.compose_attachments.pop(index)
                self.attachment_list.delete(index)

        attachment_button_frame = ttk.Frame(attachment_frame)
        attachment_button_frame.pack(fill=tk.X)

        ttk.Button(attachment_button_frame, text="添加附件", command=add_attachment).pack(side=tk.LEFT)
        ttk.Button(attachment_button_frame, text="删除附件", command=remove_attachment).pack(side=tk.LEFT)

        # 按钮框架
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)

        def send_email():
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = f"{self.current_account.get('name', '')} <{self.current_account['email']}>"
            msg["To"] = to_entry.get()
            msg["Cc"] = cc_entry.get()
            msg["Subject"] = subject_entry.get()

            # 邮件正文
            body = content_text.get("1.0", tk.END)
            msg.attach(MIMEText(body, "plain"))

            # 添加附件
            for filename in self.compose_attachments:
                with open(filename, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(filename)}",
                )
                msg.attach(part)

            # 发送邮件
            try:
                if self.current_account["outgoing_ssl"]:
                    server = smtplib.SMTP_SSL(self.current_account["outgoing_server"],
                                              int(self.current_account["outgoing_port"]))
                else:
                    server = smtplib.SMTP(self.current_account["outgoing_server"],
                                          int(self.current_account["outgoing_port"]))

                server.login(self.current_account["email"], self.current_account["password"])

                recipients = [to_entry.get()]
                if cc_entry.get():
                    recipients.extend(cc_entry.get().split(","))
                if bcc_entry.get():
                    recipients.extend(bcc_entry.get().split(","))

                server.sendmail(self.current_account["email"], recipients, msg.as_string())
                server.quit()

                messagebox.showinfo("成功", "邮件发送成功")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"发送邮件失败: {str(e)}")

        ttk.Button(button_frame, text="发送", command=send_email).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="保存草稿", command=lambda: self.save_draft(
            to_entry.get(),
            cc_entry.get(),
            bcc_entry.get(),
            subject_entry.get(),
            content_text.get("1.0", tk.END),
            self.compose_attachments
        )).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

    def save_draft(self, to, cc, bcc, subject, content, attachments):
        # 在实际应用中，这里应该将草稿保存到服务器的草稿箱
        # 这里只是简单显示消息
        messagebox.showinfo("保存草稿", "草稿已保存")

    def reply_email(self):
        if not hasattr(self, "current_email_id") or not self.current_email_id:
            messagebox.showerror("错误", "请先选择一封邮件")
            return

        # 获取当前选中的邮件信息
        selected_item = self.email_tree.selection()[0]
        values = self.email_tree.item(selected_item, "values")

        msg = {
            "from": values[0],
            "subject": values[1],
            "date": values[2],
            "body": self.email_content.get("1.0", tk.END)
        }

        self.show_compose_dialog(reply_to=msg)

    def forward_email(self):
        if not hasattr(self, "current_email_id") or not self.current_email_id:
            messagebox.showerror("错误", "请先选择一封邮件")
            return

        # 获取当前选中的邮件信息
        selected_item = self.email_tree.selection()[0]
        values = self.email_tree.item(selected_item, "values")

        msg = {
            "from": values[0],
            "subject": values[1],
            "date": values[2],
            "body": self.email_content.get("1.0", tk.END)
        }

        self.show_compose_dialog(forward_msg=msg)

    def delete_email(self):
        if not hasattr(self, "current_email_id") or not self.current_email_id:
            messagebox.showerror("错误", "请先选择一封邮件")
            return

        if not self.current_account:
            messagebox.showerror("错误", "请先选择一个邮箱账户")
            return

        if messagebox.askyesno("确认", "确定要删除这封邮件吗？"):
            try:
                if self.current_account["protocol"] == "imap":
                    self.delete_email_imap()
                else:
                    self.delete_email_pop3()

                messagebox.showinfo("成功", "邮件已删除")
                self.check_email()
            except Exception as e:
                messagebox.showerror("错误", f"删除邮件失败: {str(e)}")

    def delete_email_imap(self):
        if self.current_account["ssl"]:
            mail = imaplib.IMAP4_SSL(self.current_account["incoming_server"],
                                     int(self.current_account["incoming_port"]))
        else:
            mail = imaplib.IMAP4(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.login(self.current_account["email"], self.current_account["password"])
        mail.select("inbox")
        mail.store(self.current_email_id, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.close()
        mail.logout()

    def delete_email_pop3(self):
        if self.current_account["ssl"]:
            mail = poplib.POP3_SSL(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))
        else:
            mail = poplib.POP3(self.current_account["incoming_server"], int(self.current_account["incoming_port"]))

        mail.user(self.current_account["email"])
        mail.pass_(self.current_account["password"])
        mail.dele(int(self.current_email_id))
        mail.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = EmailClient(root)
    root.mainloop()