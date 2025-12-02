# Minecraft Server Tracker 🎮 - @LuckyVN Network  

---

## English Version

## Introduction  
This is a comprehensive tool I built to monitor **Minecraft Java Edition servers in real-time**.  
It tracks latency (ping), player counts, and uptime history with fancy graphs.

It comes with a **"Master Control" launcher** that handles all the setup automatically — no need to manually run commands.

I created this because I wanted a **self-hosted** way to monitor my favorite servers without relying on external websites.

### Features  
- **Real-time Monitoring:** Updates ping & player counts every few seconds  
- **Live Graphs:** Chart.js visualizes lag spikes & player drops  
- **Master Launcher:** Python Tkinter tool that runs backend + frontend for you  
- **Persistent Data:** Server list is saved locally  

> [!IMPORTANT]
> This project requires `Python 3.x` to be installed on your system

---

## Usage  
The easiest way to run this is via the **Launcher script**:

1. Run `launcher.py`
2. Click the large green button **“CÀI ĐẶT & KHỞI CHẠY”** (Install & Start)
3. The tool will automatically:
   - Install libraries (`aiohttp`, `mcstatus`)
   - Launch the backend (new terminal)
   - Launch the web server (new terminal)
   - Open your browser automatically
4. Click the **+** button on the dashboard to add a server (e.g. `hypixel.net`)

---

## Build (For Developers)

### Prerequisites  
- Python **3.8+**  
- `pip`

### Running From Source
```bash
# 1. Install dependencies manually (optional — launcher handles this)
pip install aiohttp mcstatus

# 2. Run the launcher
python launcher.py
```

### Building a Windows EXE  

> [!NOTE]
> The project is already configured for PyInstaller (`sys._MEIPASS` support included).

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Build the executable (bundle backend + HTML):
```bash
pyinstaller --noconsole --onefile --add-data "backend.py;." --add-data "index.html;."
```

> **Note:**  
> `;` is for **Windows**.  
> Use `:` on **Linux/macOS**.

3. Your executable appears in the `dist/` folder as `launcher.exe`.

---

# **Phiên bản Tiếng Việt**

## Giới thiệu  
Chào mừng đến với **Minecraft Server Tracker!**  
Đây là tool mình viết để theo dõi trạng thái server Minecraft theo thời gian thực — ping, số người chơi, biểu đồ uptime,…

Kèm theo là **Master Launcher** để tự động cài và chạy mọi thứ.

### Tính năng  
- **Theo dõi real-time:** Ping & số người chơi cập nhật liên tục  
- **Biểu đồ sinh động:** Dùng Chart.js để trực quan hóa lag  
- **Master Launcher:** Tool Python quản lý backend + frontend  
- **Lưu dữ liệu:** Danh sách server được lưu trên trình duyệt  

> [!IMPORTANT]
> Ứng dụng này yêu cầu bạn phải có `Python 3.x` trên hệ thống

---

## Cách dùng  

1. Chạy file `launcher.py`  
2. Bấm nút xanh: **“CÀI ĐẶT & KHỞI CHẠY”**  
3. Tool tự động:
   - Cài thư viện (`aiohttp`, `mcstatus`)
   - Chạy Backend
   - Chạy Web Server
   - Mở trình duyệt
4. Bấm nút **+** để thêm IP server (vd: `hypixel.net`)

---

## Build (Dành cho Dev)

### Cần chuẩn bị:
- Python **3.8+**
- `pip`

### Chạy từ mã nguồn
```bash
# Cài thủ công (không bắt buộc)
pip install aiohttp mcstatus

# Chạy launcher
python launcher.py
```

### Đóng gói file .EXE (Windows)

1. Cài PyInstaller:
```bash
pip install pyinstaller
```

2. Build EXE:
```bash
pyinstaller --noconsole --onefile --add-data "backend.py;." --add-data "index.html;."
```

> **Lưu ý:**  
> `;` cho **Windows**  
> `:` cho **Linux/macOS**

3. File `launcher.exe` nằm trong thư mục `dist/`.

---
