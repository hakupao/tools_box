import os
import sys
from pathlib import Path

# 添加src目录到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe
    bundle_dir = Path(sys._MEIPASS)
else:
    # 如果是开发环境
    bundle_dir = Path(__file__).parent.parent

# 确保src目录在Python路径中
if str(bundle_dir) not in sys.path:
    sys.path.insert(0, str(bundle_dir))

import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from src.gui.main_window import MainWindow

def setup_tkdnd():
    """设置tkdnd库文件路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        base_path = Path(sys._MEIPASS)
        tkdnd_path = base_path / 'tkdnd'
        if tkdnd_path.exists():
            os.environ['TKDND_LIBRARY'] = str(tkdnd_path)

def force_exit():
    """强制退出程序"""
    try:
        # 尝试清理所有窗口
        for widget in tk.Tk.winfo_all():
            try:
                widget.destroy()
            except:
                pass
    except:
        pass
    
    # 强制退出
    os._exit(0)

def main():
    try:
        setup_tkdnd()
        root = TkinterDnD.Tk()
        app = MainWindow(root)
        
        # 绑定关闭事件
        root.protocol("WM_DELETE_WINDOW", force_exit)
        
        root.mainloop()
    except Exception as e:
        print(f"程序发生错误: {str(e)}")
    finally:
        force_exit()

if __name__ == "__main__":
    main() 