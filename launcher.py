import sys
import os
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import shutil
import time

# Function to find the path of internal files when running as exe or script
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MasterControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Server Tracker - Master Control (VN)")
        self.root.geometry("600x450")
        
        # Determine Installation Path
        self.install_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'MCTracker')
        if not os.path.exists(self.install_dir):
            os.makedirs(self.install_dir)

        # CRITICAL FIX: Determine which python to use for subprocesses
        # If frozen (EXE), sys.executable is the EXE itself. We need the system 'python'.
        # If script, sys.executable is the python interpreter running this script.
        if getattr(sys, 'frozen', False):
            self.python_exec = "python" 
        else:
            self.python_exec = sys.executable

        # UI Elements (Vietnamese)
        self.label_status = tk.Label(root, text="Trạng thái hệ thống: Sẵn sàng", font=("Arial", 12, "bold"))
        self.label_status.pack(pady=10)

        self.btn_start = tk.Button(root, text="CÀI ĐẶT & KHỞI CHẠY", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.start_sequence)
        self.btn_start.pack(pady=5, ipadx=10)

        self.btn_stop = tk.Button(root, text="DỪNG HỆ THỐNG", bg="red", fg="white", font=("Arial", 10, "bold"), command=self.stop_sequence, state=tk.DISABLED)
        self.btn_stop.pack(pady=5, ipadx=10)

        self.btn_open_web = tk.Button(root, text="Mở Web Frontend", command=self.open_browser)
        self.btn_open_web.pack(pady=5)

        self.log_area = scrolledtext.ScrolledText(root, state='disabled', height=15)
        self.log_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.log(">>> Chào mừng. Nhấn 'CÀI ĐẶT & KHỞI CHẠY' để bắt đầu.")
        self.log(f">>> Thư mục làm việc: {self.install_dir}")
        self.log(f">>> Python Executable: {self.python_exec}")

        self.backend_process = None
        self.frontend_process = None
        self.is_running = False

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def start_sequence(self):
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.is_running = True
        
        # Run in a separate thread to keep GUI responsive
        threading.Thread(target=self._run_logic, daemon=True).start()

    def _run_logic(self):
        try:
            # 1. Export Files
            self.log("[1/3] Đang trích xuất file hệ thống...")
            self.export_files()
            
            # 2. Install Libraries
            self.log("[2/3] Đang kiểm tra và cài đặt thư viện (aiohttp, mcstatus)...")
            self.install_libraries()

            # 3. Start Processes
            self.log("[3/3] Đang khởi động Backend và Frontend (Cửa sổ mới)...")
            self.start_servers()
            
            self.log(">>> HỆ THỐNG ĐANG CHẠY THÀNH CÔNG!")
            self.root.after(0, lambda: self.label_status.config(text="Trạng thái: ĐANG CHẠY", fg="green"))

            # Automatically open browser after a short delay
            self.log(">>> Đang mở trình duyệt mặc định...")
            time.sleep(1.5)
            self.open_browser()

        except Exception as e:
            self.log(f"!!! LỖI NGHIÊM TRỌNG: {str(e)}")
            self.stop_sequence()

    def export_files(self):
        # List of files bundled inside the EXE
        files_to_export = ['backend.py', 'index.html']
        
        for file_name in files_to_export:
            src = resource_path(file_name)
            dst = os.path.join(self.install_dir, file_name)
            try:
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    self.log(f"   + Đã chép: {file_name}")
                else:
                    self.log(f"   ! Không tìm thấy file nguồn: {file_name}")
            except Exception as e:
                self.log(f"   ! Lỗi sao chép {file_name}: {e}")

    def install_libraries(self):
        # We use self.python_exec to ensure we call the actual python interpreter,
        # not the frozen exe wrapper.
        try:
            # 1. Check if libraries exist first to save time
            self.log("   ... Đang kiểm tra thư viện...")
            subprocess.check_call(
                [self.python_exec, "-c", "import aiohttp; import mcstatus"],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            self.log("   + Thư viện đã tồn tại. Bỏ qua bước cài đặt.")
            
        except subprocess.CalledProcessError:
            # 2. If check fails (import error), then install
            self.log("   > Chưa tìm thấy thư viện. Đang cài đặt...")
            try:
                subprocess.check_call([self.python_exec, "-m", "pip", "install", "aiohttp", "mcstatus", "--disable-pip-version-check"])
                self.log("   + Thư viện đã được cài đặt thành công.")
            except subprocess.CalledProcessError:
                self.log("   ! Cảnh báo: Lỗi cài đặt thư viện. Có thể đã tồn tại hoặc thiếu quyền.")
        except FileNotFoundError:
             self.log(f"   ! Lỗi: Không tìm thấy '{self.python_exec}'. Hãy đảm bảo Python đã được cài đặt.")

    def start_servers(self):
        # Start Backend (backend.py)
        backend_path = os.path.join(self.install_dir, "backend.py")
        
        # Use CREATE_NEW_CONSOLE (flag 16) to spawn a visible terminal window for each process.
        # This prevents the "infinite loop" of opening the launcher exe, and lets the user see output.
        flags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0

        self.backend_process = subprocess.Popen(
            [self.python_exec, backend_path],
            cwd=self.install_dir,
            creationflags=flags
        )
        self.log("   + Backend (Python) đã khởi chạy trong terminal riêng.")

        # Start Frontend (http.server)
        self.frontend_process = subprocess.Popen(
            [self.python_exec, "-m", "http.server", "8000"],
            cwd=self.install_dir,
            creationflags=flags
        )
        self.log("   + Frontend (HTTP Server) đang chạy tại port 8000 trong terminal riêng.")

    def stop_sequence(self):
        self.log(">>> Đang dừng hệ thống...")
        
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process = None
        
        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process = None

        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.label_status.config(text="Trạng thái: ĐÃ DỪNG", fg="red")
        self.log(">>> Đã dừng tất cả tác vụ.")

    def open_browser(self):
        import webbrowser
        webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    root = tk.Tk()
    app = MasterControlPanel(root)
    
    # Handle closing the window
    def on_closing():
        if app.is_running:
            if messagebox.askokcancel("Thoát", "Hệ thống đang chạy. Bạn có muốn dừng và thoát không?"):
                app.stop_sequence()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()