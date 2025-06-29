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

        # 注册全局快捷键（新增F4快捷键绑定）
        keyboard.unhook_all()  # 清除原有快捷键
        keyboard.on_press_key('f2', self.enable_capture, suppress=True)
        keyboard.on_press_key('f3', self.disable_capture, suppress=True)
        keyboard.on_press_key('`', self.handle_hotkey, suppress=True)
        keyboard.on_press_key('f4', lambda _: self.set_custom_size(), suppress=True)  # 新增F4快捷键绑定

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
        self.crop_width = 1040  # 新增：截图窗口宽度
        self.crop_height = 780  # 新增：截图窗口高度

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

            # 使用if-elif结构统一处理模式判断
            if folder_name == "详情":
                self.detail_mode = True
            elif folder_name == "500":
                self.detail_mode = False
                # 500目录专用处理（预留扩展）
            else:
                # 默认情况保持原模式
                pass

            # 统一状态变更检测机制
            if prev_mode != self.detail_mode or folder_name == "500":
                self.last_positions = []  # 删除: self.last_positions = []

            # 修改：使用 after 方法调度到主线程执行
            self.root.after(0, lambda: self.show_size_dialog())

            self.enabled = True
            messagebox.showinfo("截图功能已启用",
                                f"请按下 / 开始截图。\n{'将创建双区域截图模式' if self.detail_mode else '当前为单区域截图模式'}\n按下 * 可退出该模式。")

    def show_size_dialog(self):
        """在主线程安全显示尺寸输入对话框"""
        try:
            size_input = simpledialog.askstring(
                "输入尺寸", 
                "请输入截图窗口尺寸（格式：宽x高）:", 
                initialvalue=f"{self.crop_width}x{self.crop_height}"
            )
            if size_input:
                try:
                    width, height = map(int, size_input.split('x'))
                    if width > 0 and height > 0:
                        self.crop_width = width
                        self.crop_height = height
                    else:
                        raise ValueError
                except:
                    messagebox.showerror("错误", "尺寸格式错误，使用默认尺寸1040x780")
        # 修改：明确捕获预期异常类型并保留原有逻辑
        except tk.TclError as e:
            # 处理窗口已被销毁的特殊情况，记录异常信息
            print(f"对话框显示失败: {str(e)}")
            # 可选：记录日志或提示用户重试

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

        # ✅ 新增：设置窗口尺寸和位置
        if x is not None and y is not None:
            win.geometry(f"{self.crop_width}x{self.crop_height}+{x}+{y}")
        else:
            win.geometry(f"{self.crop_width}x{self.crop_height}")

        # 修改红色边框尺寸
        canvas = tk.Canvas(win, bg='white', highlightthickness=1)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_rectangle(0, 0, self.crop_width, self.crop_height, outline='red', width=5)

        # 修改十字线坐标计算
        mid_x = self.crop_width // 2
        mid_y = self.crop_height // 2
        canvas.create_line(mid_x, 0, mid_x, self.crop_height, fill='red', width=3)
        canvas.create_line(0, mid_y, self.crop_width, mid_y, fill='red', width=3)

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
            # 初始化 new_x/new_y 为当前窗口坐标（修复未定义问题）
            new_x, new_y = current_x, current_y
            
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

        # 尝试获取画图软件文件名
        paint_name = self.get_paint_filename()

        # 处理每个窗口
        for i, (y_val, x_val, win) in enumerate(windows_info):
            suffix = i + 1  # 生成后缀1/2
            
            # ✅ 优化命名逻辑：优先使用文件名+序号，失败使用时间戳
            if paint_name:
                base_name = f"{paint_name}_{suffix}"
            else:
                base_name = f"{suffix}_{timestamp}"
                
            # 调用截图方法
            self.capture_screen(x_val, y_val, suffix, base_name)

    def capture_screen(self, x, y, suffix=None, base_name=None):
        try:
            # 修改截图区域计算
            img = ImageGrab.grab(bbox=(
                max(x, 0),
                max(y, 0),
                min(x + self.crop_width, self.screen_width),
                min(y + self.crop_height, self.screen_height)
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
        """获取当前活动窗口的文件名（增强兼容性）"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if title:
                full_name = None
                
                # 优先尝试提取含扩展名的片段
                if " - " in title:
                    parts = title.split(" - ")
                    for part in parts:
                        if '.' in part and any(part.lower().endswith(ext) for ext in ['.jpg','.png','.bmp','.jpeg']):
                            full_name = part
                            break
                
                # 如果未找到含扩展名的片段，使用完整标题
                if not full_name:
                    full_name = title
                
                # 移除可能存在的窗口状态标识（如[修改]）
                if '[' in full_name:
                    full_name = full_name.split('[')[0].rstrip()
                    
                # 返回去除扩展名的文件名
                if '.' in full_name:
                    return os.path.splitext(full_name)[0]
                return full_name
                
            return None
        except:
            return None

    def get_paint_filename(self):
        """自动获取画图软件文件名"""
        return self.get_active_window_filename()  # 删除原有弹窗逻辑

    def set_custom_size(self):
        """通过F4快捷键重新设置截图尺寸（增强线程安全性）"""
        try:
            # 使用after方法确保在主线程执行UI操作
            self.root.after(0, lambda: self._show_size_dialog())
        except Exception as e:
            print(f"设置尺寸异常: {str(e)}")
            messagebox.showerror("错误", "无法打开尺寸设置窗口")

    def _show_size_dialog(self):
        """显示尺寸输入对话框并处理输入验证"""
        size_input = simpledialog.askstring(
            "输入尺寸", 
            "请输入截图窗口尺寸（格式：宽x高）:", 
            initialvalue=f"{self.crop_width}x{self.crop_height}"
        )
        
        if size_input:
            try:
                width, height = map(int, size_input.split('x'))
                if width > 0 and height > 0:
                    self.crop_width = width
                    self.crop_height = height
                    messagebox.showinfo("成功", f"尺寸已更新为：{width}x{height}")
                else:
                    raise ValueError("尺寸必须为正数")
            except ValueError as ve:
                print(f"尺寸输入错误: {str(ve)}")
                messagebox.showerror("错误", "请输入有效的正整数尺寸（如1040x780）")
            except Exception as e:
                print(f"未知错误: {str(e)}")
                messagebox.showerror("错误", "尺寸设置失败，请重试")


if __name__ == "__main__":
    app = CropApp()
    app.root.mainloop()



