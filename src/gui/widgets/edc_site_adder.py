import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import pyautogui
import time
import pyperclip
import win32com.client
import os
import keyboard
import threading
import json
import sys

class EdcSiteAdderWindow:
    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("EDC站点添加工具")
        self.window.geometry("800x600")
        self.window.configure(bg='#f0f0f0')
        
        # 保存主窗口引用
        self.main_window = main_window
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置pyautogui的安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # 初始化处理状态
        self.processing = False
        
        # 内置默认配置
        self.default_config = {
            "max_loops": 100,
            "click_positions": {
                "新建": {"x": 241, "y": 212},
                "查找": {"x": 1137, "y": 460},
                "搜索框": {"x": 817, "y": 409},
                "搜索": {"x": 1040, "y": 406},
                "选择": {"x": 699, "y": 471},
                "ok": {"x": 1121, "y": 758},
                "确认": {"x": 1038, "y": 728}
            }
        }
        
        # 初始化配置为默认值
        self.config = self.default_config.copy()
        
        # 尝试加载配置文件
        self.load_config()
        
        # 创建ESC键监听线程
        self.esc_thread = threading.Thread(target=self.esc_listener, daemon=True)
        self.esc_thread.start()
        
        self._create_widgets()
    
    def get_config_path(self):
        """获取配置文件路径"""
        # 使用程序所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的程序
            app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(app_dir, "edc_site_adder_config.json")
    
    def load_config(self):
        """加载配置文件"""
        config_path = self.get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print(f"已加载用户配置文件: {config_path}")
            else:
                print("未找到用户配置文件，使用默认配置")
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            # 加载失败时使用默认配置
            self.config = self.default_config.copy()
    
    def save_config(self):
        """保存配置文件"""
        config_path = self.get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"已保存配置文件: {config_path}")
            return True
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False
    
    def reset_to_default_config(self):
        """重置为默认配置"""
        self.config = self.default_config.copy()
        if self.save_config():
            messagebox.showinfo("成功", "已重置为默认配置")
        else:
            messagebox.showerror("错误", "重置配置失败，请检查文件权限")
    
    def esc_listener(self):
        """ESC键监听线程"""
        while True:
            if keyboard.is_pressed('esc') and self.processing:
                # 立即设置处理状态为False，确保处理立即停止
                self.processing = False
                # 使用after方法在主线程中执行日志记录和停止操作
                self.window.after(0, lambda: self.log("用户按下ESC键，正在停止处理..."))
                self.window.after(0, self.stop_processing)
            time.sleep(0.01)  # 进一步降低检测间隔，提高响应速度
    
    def _create_widgets(self):
        # 创建主框架
        main_frame = tk.Frame(self.window, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题框架
        title_frame = tk.Frame(main_frame, bg='#f0f0f0')
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 创建标题
        title_label = tk.Label(
            title_frame,
            text="EDC站点添加工具",
            font=('Microsoft YaHei UI', 20, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        title_label.pack(side=tk.LEFT)
        
        # 创建返回按钮
        back_btn = tk.Button(
            title_frame,
            text="返回主界面",
            command=self.back_to_main,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#e74c3c',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        back_btn.pack(side=tk.RIGHT)
        
        # 创建配置按钮
        config_btn = tk.Button(
            title_frame,
            text="配置参数",
            command=self.show_config_dialog,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#3498db',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        config_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 创建说明框架
        instruction_frame = tk.Frame(main_frame, bg='#f0f0f0')
        instruction_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 创建说明文本
        instruction_text = """
使用说明：
1. 请确保Excel已打开并选中要处理的单元格
2. 请确保Chrome浏览器已打开并登录到EDC系统
3. 点击"开始处理"按钮开始自动添加站点
4. 处理过程中请勿移动鼠标或使用键盘
5. 按ESC键可随时终止处理（这是停止处理的唯一方式）
6. 点击"配置参数"按钮可以调整循环次数和点击坐标
        """
        
        instruction_label = tk.Label(
            instruction_frame,
            text=instruction_text,
            font=('Microsoft YaHei UI', 11),
            fg='#34495e',
            bg='#f0f0f0',
            justify=tk.LEFT
        )
        instruction_label.pack(anchor=tk.W)
        
        # 创建控制框架
        control_frame = tk.Frame(main_frame, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 创建开始按钮
        start_btn = tk.Button(
            control_frame,
            text="开始处理",
            command=self.start_processing,
            width=20,
            height=2,
            font=('Microsoft YaHei UI', 11),
            bg='#2ecc71',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        start_btn.pack(side=tk.LEFT)
        
        # 创建日志框架
        log_frame = tk.Frame(main_frame, bg='#f0f0f0')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建日志标签
        log_label = tk.Label(
            log_frame,
            text="处理日志:",
            font=('Microsoft YaHei UI', 11, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        log_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#ffffff',
            fg='#2c3e50',
            height=15
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 创建配置窗口
        config_window = tk.Toplevel(self.window)
        config_window.title("配置参数")
        config_window.geometry("600x600")
        config_window.configure(bg='#f0f0f0')
        config_window.transient(self.window)  # 设置为父窗口的临时窗口
        config_window.grab_set()  # 模态窗口
        
        # 创建主框架
        main_frame = tk.Frame(config_window, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        title_label = tk.Label(
            main_frame,
            text="配置参数",
            font=('Microsoft YaHei UI', 16, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        title_label.pack(pady=(0, 20))
        
        # 创建循环次数配置
        loop_frame = tk.Frame(main_frame, bg='#f0f0f0')
        loop_frame.pack(fill=tk.X, pady=(0, 10))
        
        loop_label = tk.Label(
            loop_frame,
            text="最大循环次数:",
            font=('Microsoft YaHei UI', 11),
            fg='#2c3e50',
            bg='#f0f0f0',
            width=15,
            anchor='w'
        )
        loop_label.pack(side=tk.LEFT, padx=(0, 10))
        
        loop_var = tk.StringVar(value=str(self.config["max_loops"]))
        loop_entry = tk.Entry(
            loop_frame,
            textvariable=loop_var,
            font=('Microsoft YaHei UI', 11),
            width=10
        )
        loop_entry.pack(side=tk.LEFT)
        
        # 创建坐标获取框架
        coord_getter_frame = tk.Frame(main_frame, bg='#f0f0f0')
        coord_getter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建坐标获取标签
        coord_getter_label = tk.Label(
            coord_getter_frame,
            text="坐标获取:",
            font=('Microsoft YaHei UI', 11),
            fg='#2c3e50',
            bg='#f0f0f0',
            width=15,
            anchor='w'
        )
        coord_getter_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建坐标显示标签
        coord_display_var = tk.StringVar(value="X: 0, Y: 0")
        coord_display_label = tk.Label(
            coord_getter_frame,
            textvariable=coord_display_var,
            font=('Microsoft YaHei UI', 11, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0',
            width=20
        )
        coord_display_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建锁定状态标签
        locked_var = tk.BooleanVar(value=False)
        locked_label = tk.Label(
            coord_getter_frame,
            text="按F2锁定/解锁坐标",
            font=('Microsoft YaHei UI', 9),
            fg='#95a5a6',
            bg='#f0f0f0'
        )
        locked_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建坐标获取按钮
        coord_getter_running = False
        coord_getter_thread = None
        locked_coords = None
        
        def toggle_coord_getter():
            nonlocal coord_getter_running, coord_getter_thread, locked_coords
            
            if not coord_getter_running:
                # 开始获取坐标
                coord_getter_running = True
                coord_getter_btn.configure(text="停止获取", bg='#e74c3c')
                
                # 设置窗口半透明和置顶
                config_window.attributes('-alpha', 0.8)
                config_window.attributes('-topmost', True)
                
                # 创建新线程获取坐标
                def coord_getter():
                    while coord_getter_running:
                        if locked_coords:
                            x, y = locked_coords
                        else:
                            x, y = pyautogui.position()
                        coord_display_var.set(f"X: {x}, Y: {y}")
                        time.sleep(0.1)
                
                coord_getter_thread = threading.Thread(target=coord_getter, daemon=True)
                coord_getter_thread.start()
                
            else:
                # 停止获取坐标
                coord_getter_running = False
                coord_getter_btn.configure(text="开始获取", bg='#3498db')
                
                # 恢复窗口不透明和不置顶
                config_window.attributes('-alpha', 1.0)
                config_window.attributes('-topmost', False)
        
        # 创建F2热键处理函数
        def toggle_lock(e=None):
            nonlocal locked_coords
            is_locked = locked_var.get()
            if not is_locked:
                # 锁定当前坐标
                x, y = pyautogui.position()
                locked_coords = (x, y)
                locked_var.set(True)
                locked_label.configure(text="坐标已锁定 (F2解锁)", fg='#e74c3c')
            else:
                # 解锁坐标
                locked_coords = None
                locked_var.set(False)
                locked_label.configure(text="按F2锁定/解锁坐标", fg='#95a5a6')
        
        # 绑定F2热键
        keyboard.on_press_key('F2', toggle_lock)
        
        coord_getter_btn = tk.Button(
            coord_getter_frame,
            text="开始获取",
            command=toggle_coord_getter,
            width=10,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#3498db',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        coord_getter_btn.pack(side=tk.LEFT)
        
        # 创建点击坐标配置
        coords_frame = tk.Frame(main_frame, bg='#f0f0f0')
        coords_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        coords_label = tk.Label(
            coords_frame,
            text="点击坐标配置:",
            font=('Microsoft YaHei UI', 11, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        coords_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 创建坐标输入框架
        coords_input_frame = tk.Frame(coords_frame, bg='#f0f0f0')
        coords_input_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建坐标输入框
        coord_vars = {}
        coord_names = []
        row = 0
        for key, coord in self.config["click_positions"].items():
            coord_names.append(key)
            # 创建标签
            label = tk.Label(
                coords_input_frame,
                text=f"{key}:",
                font=('Microsoft YaHei UI', 11),
                fg='#2c3e50',
                bg='#f0f0f0',
                width=15,
                anchor='w'
            )
            label.grid(row=row, column=0, padx=(0, 10), pady=5, sticky='w')
            
            # 创建X坐标输入
            x_var = tk.StringVar(value=str(coord["x"]))
            x_entry = tk.Entry(
                coords_input_frame,
                textvariable=x_var,
                width=8,
                font=('Microsoft YaHei UI', 9)
            )
            x_entry.grid(row=row, column=2, padx=5, pady=5)
            
            # 创建Y坐标输入
            y_var = tk.StringVar(value=str(coord["y"]))
            y_entry = tk.Entry(
                coords_input_frame,
                textvariable=y_var,
                width=8,
                font=('Microsoft YaHei UI', 9)
            )
            y_entry.grid(row=row, column=3, padx=5, pady=5)
            
            # 保存变量引用
            coord_vars[key] = {"x": x_var, "y": y_var}
            
            row += 1
        
        # 创建按钮框架
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 创建保存按钮
        def save_config_values():
            try:
                # 更新循环次数
                self.config["max_loops"] = int(loop_var.get())
                
                # 更新坐标
                for key, vars in coord_vars.items():
                    self.config["click_positions"][key]["x"] = int(vars["x"].get())
                    self.config["click_positions"][key]["y"] = int(vars["y"].get())
                
                # 保存配置
                if self.save_config():
                    # 显示成功消息
                    messagebox.showinfo("成功", "配置已保存")
                    
                    # 关闭窗口
                    config_window.destroy()
                else:
                    messagebox.showerror("错误", "保存配置失败，请检查文件权限")
                
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        save_btn = tk.Button(
            button_frame,
            text="保存配置",
            command=save_config_values,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#2ecc71',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        save_btn.pack(side=tk.RIGHT)
        
        # 创建重置按钮
        reset_btn = tk.Button(
            button_frame,
            text="重置默认",
            command=self.reset_to_default_config,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#f39c12',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        reset_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 创建取消按钮
        cancel_btn = tk.Button(
            button_frame,
            text="取消",
            command=config_window.destroy,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#e74c3c',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 窗口关闭时停止坐标获取
        def on_config_window_closing():
            nonlocal coord_getter_running
            coord_getter_running = False
            keyboard.unhook_all()  # 移除所有热键绑定
            config_window.destroy()
        
        config_window.protocol("WM_DELETE_WINDOW", on_config_window_closing)
    
    def log(self, message):
        """添加日志信息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.window.update()
    
    def start_processing(self):
        """开始处理"""
        if self.processing:
            messagebox.showinfo("提示", "处理已在进行中")
            return
        
        self.processing = True
        self.log("开始处理...")
        
        try:
            # 获取Excel实例
            self.log("正在连接Excel...")
            xl = win32com.client.Dispatch("Excel.Application")
            
            # 获取当前选中的单元格
            cell = xl.Selection
            if not cell:
                self.log("错误: 未选中Excel单元格")
                self.processing = False
                return
            
            # 处理循环
            for i in range(self.config["max_loops"]):  # 使用配置的最大循环次数
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 获取单元格内容
                cell_value = cell.Text.strip()
                if not cell_value:
                    self.log(f"第 {i+1} 行为空，自动终止处理")
                    break
                
                self.log(f"处理第 {i+1} 行: {cell_value}")
                
                # 复制到剪贴板
                pyperclip.copy(cell_value)
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 保存当前窗口句柄（Excel）
                excel_hwnd = xl.ActiveWindow.Hwnd
                
                # 切换到Chrome窗口
                self.log("切换到Chrome窗口...")
                chrome_window = pyautogui.getWindowsWithTitle("Chrome")
                if not chrome_window:
                    self.log("错误: 未找到Chrome窗口")
                    self.processing = False
                    return
                
                chrome_window[0].activate()
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 执行点击操作
                self.log("执行点击操作...")
                
                # 点击新建
                pyautogui.click(
                    self.config["click_positions"]["新建"]["x"],
                    self.config["click_positions"]["新建"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 点击查找
                pyautogui.click(
                    self.config["click_positions"]["查找"]["x"],
                    self.config["click_positions"]["查找"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 点击搜索框
                pyautogui.click(
                    self.config["click_positions"]["搜索框"]["x"],
                    self.config["click_positions"]["搜索框"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 粘贴内容
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 点击搜索
                pyautogui.click(
                    self.config["click_positions"]["搜索"]["x"],
                    self.config["click_positions"]["搜索"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 点击选择
                pyautogui.click(
                    self.config["click_positions"]["选择"]["x"],
                    self.config["click_positions"]["选择"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 点击OK
                pyautogui.click(
                    self.config["click_positions"]["ok"]["x"],
                    self.config["click_positions"]["ok"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 点击确认
                pyautogui.click(
                    self.config["click_positions"]["确认"]["x"],
                    self.config["click_positions"]["确认"]["y"]
                )
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 检查是否已停止处理
                if not self.processing:
                    self.log("处理已停止")
                    break
                
                # 切回Excel
                self.log("切回Excel窗口...")
                xl.ActiveWindow.Activate()
                time.sleep(0.1)  # 进一步减少等待时间
                
                # 移动到下一行 - 使用更直接的方法
                try:
                    # 记录当前单元格地址和行列信息
                    current_address = cell.Address
                    current_row = cell.Row
                    current_column = cell.Column
                    self.log(f"当前单元格: {current_address} (行: {current_row}, 列: {current_column})")
                    
                    # 直接选择下一行的相同列
                    next_row = current_row + 1
                    next_cell = xl.ActiveSheet.Cells(next_row, current_column)
                    next_cell.Select()
                    
                    # 更新cell变量为新的选中单元格
                    cell = xl.Selection
                    self.log(f"已移动到下一行: {current_address} -> {cell.Address} (行: {cell.Row}, 列: {cell.Column})")
                except Exception as e:
                    self.log(f"错误: 无法移动到下一行 - {str(e)}")
                    break
                
                time.sleep(0.1)  # 进一步减少等待时间
            
            if self.processing:  # 只有在正常完成时才显示"处理完成"
                self.log("处理完成")
            
        except Exception as e:
            self.log(f"错误: {str(e)}")
        
        finally:
            self.processing = False
    
    def stop_processing(self):
        """停止处理"""
        if not self.processing:
            messagebox.showinfo("提示", "当前没有正在进行的处理")
            return
        
        # 确保窗口处于活动状态
        self.window.lift()
        self.window.focus_force()
        
        # 显示停止处理的消息
        messagebox.showinfo("提示", "处理已停止")
    
    def back_to_main(self):
        """返回主界面"""
        self.window.destroy()
        self.main_window.show()
    
    def on_closing(self):
        """处理窗口关闭事件"""
        if self.processing:
            if messagebox.askyesno("确认", "处理正在进行中，确定要关闭吗?"):
                self.processing = False
                # 等待处理线程结束
                time.sleep(0.5)
                self.window.destroy()
                self.main_window.show()
        else:
            self.window.destroy()
            self.main_window.show() 