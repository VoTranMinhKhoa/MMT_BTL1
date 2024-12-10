import tkinter as tk
from tkinter import messagebox
import threading
import os
import peer  # Import module peer.py của bạn

class TorrentClientGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Torrent Client")
        self.geometry("400x300")

        # Các nhãn và trường nhập liệu
        self.ip_label = tk.Label(self, text="IP:")
        self.ip_label.grid(row=0, column=0, padx=10, pady=5)
        self.ip_entry = tk.Entry(self)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=5)
        self.ip_entry.insert(0, "127.0.0.1")  # Giá trị mặc định

        self.port_label = tk.Label(self, text="Port:")
        self.port_label.grid(row=1, column=0, padx=10, pady=5)
        self.port_entry = tk.Entry(self)
        self.port_entry.grid(row=1, column=1, padx=10, pady=5)
        self.port_entry.insert(0, "4040")  # Giá trị mặc định

        self.download_label = tk.Label(self, text="Download Torrent File:")
        self.download_label.grid(row=2, column=0, padx=10, pady=5)
        self.download_entry = tk.Entry(self)
        self.download_entry.grid(row=2, column=1, padx=10, pady=5)
        
        self.upload_label = tk.Label(self, text="Upload Torrent File:")
        self.upload_label.grid(row=3, column=0, padx=10, pady=5)
        self.upload_entry = tk.Entry(self)
        self.upload_entry.grid(row=3, column=1, padx=10, pady=5)

        self.tracker_ip_label = tk.Label(self, text="Tracker IP:")
        self.tracker_ip_label.grid(row=4, column=0, padx=10, pady=5)
        self.tracker_ip_entry = tk.Entry(self)
        self.tracker_ip_entry.grid(row=4, column=1, padx=10, pady=5)
        self.tracker_ip_entry.insert(0, "127.0.0.1")

        self.tracker_port_label = tk.Label(self, text="Tracker Port:")
        self.tracker_port_label.grid(row=5, column=0, padx=10, pady=5)
        self.tracker_port_entry = tk.Entry(self)
        self.tracker_port_entry.grid(row=5, column=1, padx=10, pady=5)
        self.tracker_port_entry.insert(0, "5050")

        self.become_seeder_var = tk.BooleanVar()
        self.become_seeder_check = tk.Checkbutton(self, text="Become Seeder", variable=self.become_seeder_var)
        self.become_seeder_check.grid(row=6, columnspan=2, pady=10)

        # Nút để bắt đầu
        self.start_button = tk.Button(self, text="Start", command=self.start_torrent)
        self.start_button.grid(row=7, columnspan=2, pady=10)

    def start_torrent(self):
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        download = self.download_entry.get().strip()
        upload = self.upload_entry.get().strip()
        tracker_ip = self.tracker_ip_entry.get()
        tracker_port = int(self.tracker_port_entry.get())
        become_seeder = self.become_seeder_var.get()

        if download:
            download_files = [download]
        else:
            download_files = []

        if upload:
            upload_files = [upload]
        else:
            upload_files = []

        # Khởi tạo đối tượng Peer và chạy các tác vụ download/upload trong thread riêng
        peer_instance = peer.Peer(
            ip=ip,
            port=port,
            metainfo_storage="metainfo",
            pieces_storage="pieces",
            output_storage="output",
            tracker_ip=tracker_ip,
            tracker_port=tracker_port,
            header_length=1024
        )

        # Đảm bảo không chạy lệnh đồng bộ mà là trong thread
        def run_peer():
            if download_files:
                peer_instance.download_files(download_files)
            if upload_files:
                peer_instance.upload_files(upload_files, (tracker_ip, tracker_port))
            if become_seeder:
                peer_instance.run()

        thread = threading.Thread(target=run_peer)
        thread.start()
        thread.join()

        # Thông báo sau khi hoàn thành
        messagebox.showinfo("Torrent Client", "Download/Upload complete!")

if __name__ == "__main__":
    app = TorrentClientGUI()
    app.mainloop()
