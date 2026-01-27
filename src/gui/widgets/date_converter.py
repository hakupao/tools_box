import tkinter as tk
from tkinter import scrolledtext

from ...utils.date_utils import convert_to_iso8601
from ..theme import get_theme

class DateConverterWindow:
    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("日期转换工具")
        self.window.geometry("1200x600")
        self.theme = get_theme(self.window)
        self.colors = self.theme.colors
        self.fonts = self.theme.fonts
        self.window.configure(bg=self.colors.bg)
        
        # 保存主窗口引用
        self.main_window = main_window
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self._create_widgets()
    
    def _create_widgets(self):
        colors = self.colors
        fonts = self.fonts
        # 创建主框架
        main_frame = tk.Frame(
            self.window,
            bg=colors.surface,
            padx=24,
            pady=22,
            highlightbackground=colors.stroke,
            highlightthickness=1,
            bd=0,
        )
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=18)
        
        # 创建标题框架
        title_frame = tk.Frame(main_frame, bg=colors.surface)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 创建标题
        title_label = tk.Label(
            title_frame,
            text="日期格式转换",
            font=fonts["title"],
            fg=colors.text,
            bg=colors.surface
        )
        title_label.pack(side=tk.LEFT)
        
        # 创建返回按钮
        back_btn = tk.Button(
            title_frame,
            text="返回主界面",
            command=self.back_to_main,
            width=15,
            height=1,
            font=fonts["body"],
            relief='flat',
            cursor='hand2'
        )
        back_btn.pack(side=tk.RIGHT)
        self.theme.style_button(back_btn, variant="secondary")
        
        # 创建左右布局框架
        content_frame = tk.Frame(main_frame, bg=colors.surface)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧框架
        left_frame = tk.Frame(content_frame, bg=colors.surface)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 右侧框架
        right_frame = tk.Frame(content_frame, bg=colors.surface)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 左侧输入区域
        input_label = tk.Label(
            left_frame,
            text="输入数据：",
            font=fonts["body_bold"],
            fg=colors.text,
            bg=colors.surface
        )
        input_label.pack(anchor='w')
        
        self.input_text = scrolledtext.ScrolledText(
            left_frame,
            width=50,
            height=20,
            font=fonts["mono"]
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        self.theme.style_text(self.input_text)
        
        # 转换按钮
        convert_btn = tk.Button(
            left_frame,
            text="转换",
            command=self.convert_dates,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief='flat',
            cursor='hand2'
        )
        convert_btn.pack(pady=10)
        self.theme.style_button(convert_btn, variant="primary")
        
        # 右侧输出区域
        output_label = tk.Label(
            right_frame,
            text="转换结果：",
            font=fonts["body_bold"],
            fg=colors.text,
            bg=colors.surface
        )
        output_label.pack(anchor='w')
        
        self.output_text = scrolledtext.ScrolledText(
            right_frame,
            width=50,
            height=20,
            font=fonts["mono"]
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        self.theme.style_text(self.output_text)
        
        # 复制按钮
        copy_btn = tk.Button(
            right_frame,
            text="复制全部",
            command=self.copy_all,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief='flat',
            cursor='hand2'
        )
        copy_btn.pack(pady=10)
        self.theme.style_button(copy_btn, variant="secondary")
    
    def back_to_main(self):
        """返回主界面"""
        self.window.destroy()
        self.main_window.show()
    
    def convert_dates(self):
        input_text = self.input_text.get("1.0", tk.END)
        lines = input_text.split('\n')
        result = [convert_to_iso8601(line.strip()) for line in lines]
        
        # 显示结果
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", '\n'.join(result))
    
    def copy_all(self):
        """复制所有转换结果到剪贴板"""
        result = self.output_text.get("1.0", tk.END).strip()
        self.window.clipboard_clear()
        self.window.clipboard_append(result)
        self.window.update()
    
    def on_closing(self):
        """处理窗口关闭事件"""
        self.window.destroy()
        self.main_window.show() 
