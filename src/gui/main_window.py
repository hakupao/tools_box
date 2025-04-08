import tkinter as tk
from src.gui.widgets.date_converter import DateConverterWindow
from src.gui.widgets.csv_converter import CsvConverterWindow
from src.gui.widgets.xlsx_converter import XlsxConverterWindow
from src.gui.widgets.edc_site_adder import EdcSiteAdderWindow
from src.gui.widgets.xlsx_file_restructuring import FileRestructureWindow
from src.version import VERSION

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("工具集合")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # 设置窗口最小尺寸
        self.root.update()
        self.root.minsize(800, 600)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=20)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重，使界面居中
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        
        # 创建标题框架
        title_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 30))
        
        # 创建标题
        title_label = tk.Label(
            title_frame,
            text="工具箱",
            font=('Microsoft YaHei UI', 32, 'bold'),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        title_label.pack()
        
        # 创建副标题
        subtitle_label = tk.Label(
            title_frame,
            text=f"实用工具集合 v{VERSION}",
            font=('Microsoft YaHei UI', 12),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 按钮配置
        self.buttons = [
            ("日期转换", self.function_one),
            ("CSV转XLSX", self.function_two),
            ("XLSX转CSV", self.function_three),
            ("EDC施设添加", self.function_four),
            ("生成Data Set", self.function_five),
            ("功能六", self.function_six)
        ]
        
        self.colors = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6', '#1abc9c']
        
        self._create_widgets()
    
    def hide(self):
        """隐藏主窗口"""
        self.root.withdraw()
    
    def show(self):
        """显示主窗口"""
        self.root.deiconify()
    
    def _create_widgets(self):
        # 创建按钮网格
        for i, (text, command) in enumerate(self.buttons):
            # 创建按钮容器框架
            btn_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
            row = (i // 2) + 1
            col = i % 2
            btn_frame.grid(row=row, column=col, padx=15, pady=15)
            
            # 创建按钮
            btn = tk.Button(
                btn_frame,
                text=text,
                command=command,
                width=25,
                height=2,
                font=('Microsoft YaHei UI', 11),
                bg=self.colors[i],
                fg='white',
                relief='flat',
                cursor='hand2'
            )
            btn.pack(pady=5)
            
            # 创建按钮描述标签
            desc_label = tk.Label(
                btn_frame,
                text="点击使用此功能",
                font=('Microsoft YaHei UI', 9),
                fg='#95a5a6',
                bg='#f0f0f0'
            )
            desc_label.pack()
            
            # 绑定鼠标悬停事件
            btn.bind('<Enter>', lambda e, b=btn: self.on_enter(e, b))
            btn.bind('<Leave>', lambda e, b=btn: self.on_leave(e, b))
    
    def on_enter(self, event, button):
        """鼠标悬停时改变按钮颜色"""
        button.configure(bg=self.colors[self.buttons.index((button['text'], button['command']))])
    
    def on_leave(self, event, button):
        """鼠标离开时恢复按钮颜色"""
        button.configure(bg=self.colors[self.buttons.index((button['text'], button['command']))])
    
    def function_one(self):
        # 隐藏主窗口
        self.hide()
        # 打开日期转换窗口
        DateConverterWindow(self.root, self)
    
    def function_two(self):
        # 隐藏主窗口
        self.hide()
        # 打开CSV转换窗口
        CsvConverterWindow(self.root, self)
    
    def function_three(self):
        # 隐藏主窗口
        self.hide()
        # 打开XLSX转换窗口
        XlsxConverterWindow(self.root, self)
    
    def function_four(self):
        # 隐藏主窗口
        self.hide()
        # 打开EDC施设添加窗口
        EdcSiteAdderWindow(self.root, self)
    
    def function_five(self):
        # 隐藏主窗口
        self.hide()
        # 打开生成Data Set加窗口
        FileRestructureWindow(self.root, self)
    
    def function_six(self):
        # 功能六实现位置
        pass
    
    def on_closing(self):
        """处理窗口关闭事件"""
        # 强制退出程序
        import os
        os._exit(0) 