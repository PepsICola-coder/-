#!/usr/bin/env python
# _*_ coding: utf-8 _*_
# @Time       : 2025/5/17 1:27
# @Author     : ZZ
# @File       : 截图快捷键.py
# @Software   : PyCharm
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog  # 新增 filedialog 导入
from PIL import Image, ImageGrab, ImageDraw
import os
import pystray
import keyboard
from threading import Thread
from datetime import datetime
import win32gui
import win32con

class CropApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        # 获取并缓存屏幕尺寸，避免每次截图时都调用 ImageGrab.grab()
        screen_img = ImageGrab.grab()
        self.screen_width, self.screen_height = screen_img.size
        del screen_img  # 显式释放图像资源

        # 初始化系统托盘
        self.tray_icon = self.create_tray_icon()
        self.tray_thread = Thread(target=self.tray_icon.run)
        self.tray_thread.daemon = True
        self.tray_thread.start()

        # 注册全局快捷键（仅保留基础功能键）
        keyboard.unhook_all()  # 清除原有快捷键
        keyboard.on_press_key('f1', self.enable_capture, suppress=True)
        keyboard.on_press_key('f3', self.disable_capture, suppress=True)
        keyboard.on_press_key('`', self.handle_hotkey, suppress=True)

        # 配置保存参数
        self.save_dir = r"F:\兼职\500"
        self.hotkey_handlers = []  # 新增：存储方向键相关的事件处理器
        self.jpeg_quality = 100
        self.jpeg_subsampling = 0
        os.makedirs(self.save_dir, exist_ok=True)

        self.detail_mode = False  # 新增：记录是否处于详情模式
        self.crop_wins = []  # 新增：管理多个裁剪窗口
        self.enabled = False  # 新增：初始化 enabled 属性
        self.drag_start_x = 0  # 新增：记录拖拽起点X坐标
        self.drag_start_y = 0  # 新增：记录拖拽起点Y坐标
        self.last_positions = []  # 修改：初始化空列表存储位置
        self.active_window = None  # 新增：记录当前激活的窗口

    def enable_capture(self, _):
        if self.enabled:
            return
        new_dir = filedialog.askdirectory(title="选择截图保存路径", initialdir=self.save_dir)
        if new_dir:
            self.save_dir = new_dir
            os.makedirs(self.save_dir, exist_ok=True)
            
            # 修改：精确匹配路径结尾判断模式
            folder_name = os.path.basename(new_dir)
            prev_mode = self.detail_mode
            self.detail_mode = (folder_name == "详情")
            
            # 新增：处理500目录逻辑
            if folder_name == "500":
                self.detail_mode = False
                self.last_positions = []  # 修改：确保初始化为空列表而非None
                
            # 当模式发生变化时清除历史位置
            if prev_mode != self.detail_mode:
                self.last_positions = []  # 修改：初始化为空列表而非None
            self.enabled = True
            messagebox.showinfo("截图功能已启用", 
                              f"请按下 / 开始截图。\n{'将创建双区域截图模式' if self.detail_mode else '当前为单区域截图模式'}\n按下 * 可退出该模式。")

    def disable_capture(self, _):
        if not self.enabled:
            return
        self.enabled = False
        messagebox.showinfo("截图功能已关闭", "当前仅监听快捷键。\n请按下 / 再次启用截图功能。")

    def handle_hotkey(self, _):
        """带启用状态检查的快捷键处理"""
        print("截图快捷键已触发")  # ✅ 添加日志输出，用于调试
        if self.enabled:
            self.create_crop_window()

    def create_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem('开始截图', self.create_crop_window),  # ✅ 现在方法已存在
            pystray.MenuItem('退出', self.quit_app)
        )

        try:
            image = Image.open("icon.ico") if os.path.exists("icon.ico") else self.create_default_icon()
        except Exception as e:
            print(f"图标加载失败: {str(e)}")
            image = self.create_default_icon()

        return pystray.Icon("screenshot_tool", image, "截图工具", menu)

    def create_default_icon(self):
        """创建应急默认图标"""
        image = Image.new('RGB', (64, 64), 'blue')
        draw = ImageDraw.Draw(image)
        draw.text((10, 25), "SC", fill='white')
        return image

    def create_crop_window(self):
        """创建裁剪窗口"""
        if not self.enabled:
            return
            
        # 修改：增强窗口位置记忆逻辑
        if self.last_positions:
            # 使用记忆位置创建窗口
            for pos in self.last_positions[: (2 if self.detail_mode else 1)]:
                self.create_single_window(pos[0], pos[1])
        else:
            # 初始创建逻辑
            window_count = 2 if self.detail_mode else 1
            for i in range(window_count):
                self.create_single_window()

    def create_single_window(self, x=None, y=None):
        """创建单个截图窗口"""
        win = tk.Toplevel()
        win.overrideredirect(True)
        win.attributes('-alpha', 0.3)
        win.attributes('-topmost', True)
        win.geometry("1040x780")  # 窗口尺寸已正确设置
        
        # 保持原有红色矩形尺寸与窗口一致（1040x780）
        canvas = tk.Canvas(win, bg='white', highlightthickness=1)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_rectangle(0, 0, 1040, 780, outline='red', width=5)
        
        # 调整十字线到窗口中心（修改部分）
        canvas.create_line(520, 0, 520, 780, fill='red', width=3)  # 水平中线（1040/2=520）
        canvas.create_line(0, 390, 1040, 390, fill='red', width=3)  # 垂直中线（780/2=390）

        # 绑定事件并传递当前窗口引用
        win.bind("<ButtonPress-1>", lambda e, w=win: self.on_drag_start(e, w))
        win.bind("<B1-Motion>", lambda e, w=win: self.on_drag_motion(e, w))
        win.bind("<ButtonRelease-1>", lambda e: None)
        
        # 绑定窗口激活事件
        win.bind("<FocusIn>", lambda e, w=win: self.set_active_window(w))
        canvas.bind("<ButtonPress-1>", lambda e, w=win: self.set_active_window(w))
        
        self.crop_wins.append((win, canvas))
        
        # 新增：当第一个窗口创建时注册方向键和确认取消键
        if len(self.crop_wins) == 1:
            self.hotkey_handlers = [
                keyboard.on_press_key('left', self.handle_arrow_key, suppress=True),
                keyboard.on_press_key('right', self.handle_arrow_key, suppress=True),
                keyboard.on_press_key('up', self.handle_arrow_key, suppress=True),
                keyboard.on_press_key('down', self.handle_arrow_key, suppress=True),
                keyboard.on_press_key('enter', lambda _: self.confirm_capture(), suppress=True),
                keyboard.on_press_key('esc', lambda _: self.cancel_capture(), suppress=True)
            ]

    def on_drag_start(self, event, window):
        """处理窗口拖拽开始事件"""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root

    def on_drag_motion(self, event, window):
        """处理窗口拖拽移动事件"""
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y
        
        # 使用动态窗口尺寸进行边界检查
        win_width = window.winfo_width()
        win_height = window.winfo_height()
        new_x = max(0, min(window.winfo_x() + dx, self.screen_width - win_width))
        new_y = max(0, min(window.winfo_y() + dy, self.screen_height - win_height))
        
        window.geometry(f"+{new_x}+{new_y}")
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        
        # 实时更新绝对位置到记忆数组
        if self.last_positions:
            for idx, (w, _) in enumerate(self.crop_wins):
                if w == window:
                    self.last_positions[idx] = (new_x, new_y)
                    break

    def set_active_window(self, window):
        """设置当前激活窗口"""
        self.active_window = window

    def handle_arrow_key(self, event):
        """处理方向键全局事件（仅移动激活窗口）"""
        if self.active_window and self.crop_wins:
            step = 10
            win = self.active_window
            win_width = win.winfo_width()
            win_height = win.winfo_height()
            
            current_x = win.winfo_x()
            current_y = win.winfo_y()
            
            if event.name == 'left':
                new_x = max(0, current_x - step)
                new_y = current_y
            elif event.name == 'right':
                new_x = min(self.screen_width - win_width, current_x + step)
                new_y = current_y
            elif event.name == 'up':
                new_x = current_x
                new_y = max(0, current_y - step)
            elif event.name == 'down':
                new_x = current_x
                new_y = min(self.screen_height - win_height, current_y + step)
            
            # 仅移动激活窗口
            win.geometry(f"+{new_x}+{new_y}")
            
            # 更新对应窗口的位置记录
            if self.last_positions:  # 添加安全判断
                for idx, (w, _) in enumerate(self.crop_wins):
                    if w == win:
                        self.last_positions[idx] = (new_x, new_y)
                        break

    def confirm_capture(self):
        """确认并执行截图"""
        windows_info = []
        for win, _ in self.crop_wins:
            x = win.winfo_x()
            y = win.winfo_y()
            windows_info.append((y, x, win))

        self.destroy_all_crops()
        
        # 按Y坐标排序（上方窗口先保存）
        windows_info.sort()
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 无论是否详情模式都尝试获取画图软件文件名
        paint_name = self.get_paint_filename()  # 修改：删除原条件判断
        
        # 处理每个窗口
        for i, (y_val, x_val, win) in enumerate(windows_info):
            suffix = i + 1  # 生成后缀1/2
            
            # 构建文件名
            if self.detail_mode and paint_name:
                base_name = f"{paint_name}_{suffix}"  # 详情模式：文件名+后缀
            elif paint_name:  # 新增：单窗口模式且有画图文件名时
                base_name = f"{paint_name}_{timestamp}"  # 单窗口特殊处理
            else:
                base_name = f"{suffix}_{timestamp}"  # 普通模式保持不变
            
            # 调用截图方法
            self.capture_screen(x_val, y_val, suffix, base_name)

    def capture_screen(self, x, y, suffix=None, base_name=None):
        try:
            # 截图区域计算（修改尺寸为1040x780）
            img = ImageGrab.grab(bbox=(
                max(x, 0),
                max(y, 0),
                min(x + 1040, self.screen_width),  # 修改宽度为1040
                min(y + 780, self.screen_height)    # 修改高度为780
            ))

            # 确保文件名有效性
            if not base_name:
                base_name = f"{suffix}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 构建保存路径（直接使用原始选择目录）
            save_path = os.path.join(self.save_dir, f"{base_name}.jpg")
            
            # 确保文件名唯一性
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(self.save_dir, f"{base_name}_{counter}.jpg")
                counter += 1

            # 保存图片
            img.convert('RGB').save(
                save_path,
                quality=self.jpeg_quality,
                subsampling=self.jpeg_subsampling,
                optimize=True
            )

            self.show_notification("截图成功", f"已保存至：\n{save_path}")

            del img

        except Exception as e:
            self.show_notification("截图失败", f"错误原因：\n{str(e)}")

    def show_notification(self, title, message):
        self.tray_icon.notify(message, title)

    def quit_app(self):
        self.tray_icon.stop()
        self.root.destroy()

    def cancel_capture(self):
        """取消截图操作"""
        self.destroy_all_crops()
        # 可选：重置其他状态变量
        # self.detail_mode = False  

    def destroy_all_crops(self):
        """销毁所有已创建的截图窗口，并保存窗口位置"""
        positions = []
        for win, canvas in self.crop_wins:
            x = win.winfo_x()
            y = win.winfo_y()
            positions.append((x, y))
        self.last_positions = positions
        
        # 新增：移除方向键和确认取消键的注册
        if self.hotkey_handlers:
            for handler in self.hotkey_handlers:
                keyboard.unhook(handler)
            self.hotkey_handlers = []
            
        # 销毁窗口
        for win, canvas in self.crop_wins:
            win.destroy()
        self.crop_wins.clear()

    def get_active_window_filename(self):
        """获取当前活动窗口的文件名"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            # 解析画图软件窗口标题（格式如：文件名 - 画图）
            if " - 画图" in title:
                # 获取文件名并移除后缀
                full_name = title.split(" - 画图")[0]
                return os.path.splitext(full_name)[0]  # ✅ 新增文件名后缀处理
            return None
        except:
            return None

    def get_paint_filename(self):
        """自动获取画图软件文件名"""
        return self.get_active_window_filename()  # 删除原有弹窗逻辑

if __name__ == "__main__":
    app = CropApp()
    app.root.mainloop()