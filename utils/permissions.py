"""权限检测工具模块"""
import ctypes
import sys

def check_admin_rights():
    """检查并确保程序以管理员权限运行"""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, sys.argv[0], None, 1)
        sys.exit()