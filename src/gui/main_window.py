import tkinter as tk
from tkinter import ttk
from src.gui.widgets.date_converter import DateConverterWindow
from src.gui.widgets.edc_site_adder import EdcSiteAdderWindow
from src.gui.widgets.xlsx_file_restructuring import FileRestructureWindow
from src.gui.widgets.data_cleaner import DataCleanerWindow
from src.gui.widgets.codelist_processor import CodelistProcessorWindow
from src.gui.widgets.data_masking import DataMaskingWindow
from src.gui.widgets.csv_quote_remover import CsvQuoteRemoverWindow
from src.gui.widgets.fullwidth_halfwidth_converter import FullwidthHalfwidthConverterWindow
from src.gui.widgets.file_field_extractor import FileFieldExtractorWindow
from src.gui.widgets.file_format_converter import FileFormatConverterWindow
from src.gui.widgets.dead_link_checker import DeadLinkCheckerWindow
from src.version import VERSION


class MainWindow:
    """
    主窗口类 - 工具箱的主界面
    采用现代卡片式布局，按功能分类展示工具
    """
    
    # 配色方案 - 浅色主题
    COLORS = {
        'bg_primary': '#f8fafc',       # 浅灰白背景
        'bg_secondary': '#ffffff',      # 纯白次级背景
        'bg_card': '#ffffff',           # 白色卡片背景
        'accent_blue': '#3b82f6',       # 强调色蓝
        'accent_cyan': '#06b6d4',       # 强调色青
        'accent_purple': '#8b5cf6',     # 强调色紫
        'accent_pink': '#ec4899',       # 强调色粉
        'accent_green': '#10b981',      # 强调色绿
        'accent_orange': '#f97316',     # 强调色橙
        'text_primary': '#1e293b',      # 深色主文字
        'text_secondary': '#64748b',    # 灰色次级文字
        'text_muted': '#94a3b8',        # 弱化文字
        'border': '#e2e8f0',            # 浅色边框
        'hover': '#f1f5f9',             # 浅色悬停
        'shadow': '#cbd5e1',            # 阴影色
    }
    
    # 工具分类配置
    TOOL_CATEGORIES = [
        {
            'name': '📁 文件处理',
            'description': '文件格式、结构和内容处理工具',
            'color': 'accent_blue',
            'tools': [
                {
                    'name': '文件格式转换',
                    'icon': '🔄',
                    'desc': '支持CSV、Excel、SAS等多种格式互转',
                    'func': 'function_two'
                },
                {
                    'name': '生成Data Set',
                    'icon': '📊',
                    'desc': '快速生成标准化数据集结构',
                    'func': 'function_five'
                },
                {
                    'name': '获取文件字段',
                    'icon': '📋',
                    'desc': '提取文件中的字段信息列表',
                    'func': 'function_eleven'
                },
                {
                    'name': '死链检测',
                    'icon': '🔗',
                    'desc': '检测文件或网页中的无效链接',
                    'func': 'function_twelve'
                },
            ]
        },
        {
            'name': '🔧 数据处理',
            'description': '数据清洗、转换和处理工具',
            'color': 'accent_purple',
            'tools': [
                {
                    'name': '数据清洗',
                    'icon': '🧹',
                    'desc': '清理数据中的异常值和空白',
                    'func': 'function_six'
                },
                {
                    'name': '数据模糊化',
                    'icon': '🔒',
                    'desc': '对敏感数据进行脱敏处理',
                    'func': 'function_eight'
                },
                {
                    'name': 'Codelist处理',
                    'icon': '📝',
                    'desc': '处理和管理代码列表数据',
                    'func': 'function_seven'
                },
                {
                    'name': 'EDC施设添加',
                    'icon': '🏥',
                    'desc': 'EDC系统施设信息批量添加',
                    'func': 'function_four'
                },
            ]
        },
        {
            'name': '✨ 格式转换',
            'description': '文本和格式快速转换工具',
            'color': 'accent_green',
            'tools': [
                {
                    'name': '日期转换',
                    'icon': '📅',
                    'desc': '多种日期格式智能转换',
                    'func': 'function_one'
                },
                {
                    'name': '全角转半角',
                    'icon': '🔡',
                    'desc': '全角半角字符快速转换',
                    'func': 'function_ten'
                },
                {
                    'name': 'CSV引号去除',
                    'icon': '✂️',
                    'desc': '批量去除CSV文件中的引号',
                    'func': 'function_nine'
                },
            ]
        },
    ]
    
    def __init__(self, root):
        """初始化主窗口"""
        self.root = root
        self.root.title("工具集合")
        self.root.geometry("1200x850")
        self.root.configure(bg=self.COLORS['bg_primary'])
        
        # 设置窗口最小尺寸
        self.root.update()
        self.root.minsize(1100, 800)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 存储按钮引用用于悬停效果
        self.tool_buttons = {}
        
        # 创建界面
        self._create_ui()
    
    def _create_ui(self):
        """创建主界面"""
        # 创建主容器，支持滚动
        self.canvas = tk.Canvas(
            self.root,
            bg=self.COLORS['bg_primary'],
            highlightthickness=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.root,
            orient="vertical",
            command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(
            self.canvas,
            bg=self.COLORS['bg_primary']
        )
        
        # 配置滚动
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # 创建窗口并让它随父容器宽度调整
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 绑定canvas尺寸变化事件，让内容宽度跟随canvas
        self.canvas.bind(
            "<Configure>",
            self._on_canvas_configure
        )
        
        # 绑定鼠标滚轮
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        )
        
        # 布局滚动组件
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 创建内容容器，使用固定内边距
        self.content_frame = tk.Frame(
            self.scrollable_frame,
            bg=self.COLORS['bg_primary'],
            padx=50,
            pady=30
        )
        self.content_frame.pack(fill="both", expand=True)
        
        # 创建头部区域
        self._create_header(self.content_frame)
        
        # 创建工具分类卡片
        self._create_tool_categories(self.content_frame)
        
        # 创建页脚
        self._create_footer(self.content_frame)
    
    def _on_canvas_configure(self, event):
        """当canvas尺寸变化时，调整内容宽度"""
        # 让内容宽度跟随canvas宽度
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _create_header(self, parent):
        """创建头部区域"""
        header_frame = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        header_frame.pack(fill="x", pady=(0, 40))
        
        # 左侧标题区域
        title_container = tk.Frame(header_frame, bg=self.COLORS['bg_primary'])
        title_container.pack(anchor="w")
        
        # 主标题
        title_label = tk.Label(
            title_container,
            text="🛠️ 工具箱",
            font=('Microsoft YaHei UI', 36, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_primary']
        )
        title_label.pack(anchor="w")
        
        # 副标题
        subtitle_label = tk.Label(
            title_container,
            text=f"实用工具集合  •  v{VERSION}  •  提升工作效率的好帮手",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_primary']
        )
        subtitle_label.pack(anchor="w", pady=(8, 0))
        
        # 分隔线
        separator = tk.Frame(
            header_frame,
            bg=self.COLORS['border'],
            height=1
        )
        separator.pack(fill="x", pady=(25, 0))
    
    def _create_tool_categories(self, parent):
        """创建工具分类卡片区域"""
        categories_frame = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        categories_frame.pack(fill="both", expand=True)
        
        for category in self.TOOL_CATEGORIES:
            self._create_category_card(categories_frame, category)
    
    def _create_category_card(self, parent, category):
        """创建单个分类卡片"""
        accent_color = self.COLORS[category['color']]
        
        # 分类容器，添加边框效果
        category_frame = tk.Frame(
            parent,
            bg=self.COLORS['bg_secondary'],
            padx=25,
            pady=20,
            highlightbackground=self.COLORS['border'],
            highlightthickness=1
        )
        category_frame.pack(fill="x", pady=(0, 20))
        
        # 分类标题栏
        header_frame = tk.Frame(category_frame, bg=self.COLORS['bg_secondary'])
        header_frame.pack(fill="x", pady=(0, 15))
        
        # 分类名称
        name_label = tk.Label(
            header_frame,
            text=category['name'],
            font=('Microsoft YaHei UI', 16, 'bold'),
            fg=accent_color,
            bg=self.COLORS['bg_secondary']
        )
        name_label.pack(side="left")
        
        # 分类描述
        desc_label = tk.Label(
            header_frame,
            text=category['description'],
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_muted'],
            bg=self.COLORS['bg_secondary']
        )
        desc_label.pack(side="left", padx=(15, 0))
        
        # 工具卡片网格容器
        tools_frame = tk.Frame(category_frame, bg=self.COLORS['bg_secondary'])
        tools_frame.pack(fill="x", expand=True)
        
        # 配置4列，均匀分布
        num_cols = 4
        for col in range(num_cols):
            tools_frame.grid_columnconfigure(col, weight=1, uniform="tool_col")
        
        # 配置行高度一致
        num_tools = len(category['tools'])
        num_rows = (num_tools + num_cols - 1) // num_cols
        for row in range(num_rows):
            tools_frame.grid_rowconfigure(row, weight=1, uniform="tool_row")
        
        # 创建工具卡片
        for idx, tool in enumerate(category['tools']):
            self._create_tool_card(
                tools_frame,
                tool,
                accent_color,
                row=idx // num_cols,
                col=idx % num_cols
            )
    
    def _create_tool_card(self, parent, tool, accent_color, row, col):
        """创建单个工具卡片"""
        # 卡片外框，添加边框
        card_frame = tk.Frame(
            parent,
            bg=self.COLORS['bg_card'],
            padx=18,
            pady=15,
            highlightbackground=self.COLORS['border'],
            highlightthickness=1
        )
        card_frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        
        # 图标
        icon_label = tk.Label(
            card_frame,
            text=tool['icon'],
            font=('Segoe UI Emoji', 26),
            fg=accent_color,
            bg=self.COLORS['bg_card'],
            anchor="w"
        )
        icon_label.pack(anchor="w", fill="x")
        
        # 工具名称
        name_label = tk.Label(
            card_frame,
            text=tool['name'],
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_card'],
            anchor="w"
        )
        name_label.pack(anchor="w", fill="x", pady=(6, 3))
        
        # 工具描述 - 固定高度确保对齐
        desc_frame = tk.Frame(
            card_frame,
            bg=self.COLORS['bg_card'],
            height=40  # 固定高度
        )
        desc_frame.pack(anchor="w", fill="x")
        desc_frame.pack_propagate(False)  # 保持固定高度
        
        desc_label = tk.Label(
            desc_frame,
            text=tool['desc'],
            font=('Microsoft YaHei UI', 9),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_card'],
            wraplength=160,
            justify="left",
            anchor="nw"
        )
        desc_label.pack(anchor="nw", fill="both", expand=True)
        
        # 打开按钮
        open_btn = tk.Button(
            card_frame,
            text="打开工具 →",
            font=('Microsoft YaHei UI', 9),
            fg='#ffffff',
            bg=accent_color,
            activeforeground='#ffffff',
            activebackground=accent_color,
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=4,
            command=getattr(self, tool['func'])
        )
        open_btn.pack(anchor="w", pady=(10, 0))
        
        # 存储按钮和颜色信息用于悬停效果
        button_id = f"{tool['name']}_{id(open_btn)}"
        self.tool_buttons[button_id] = {
            'button': open_btn,
            'card': card_frame,
            'accent': accent_color,
            'components': [icon_label, name_label, desc_frame, desc_label]
        }
        
        # 绑定卡片悬停效果
        for widget in [card_frame, icon_label, name_label, desc_frame, desc_label]:
            widget.bind('<Enter>', lambda e, bid=button_id: self._on_card_enter(bid))
            widget.bind('<Leave>', lambda e, bid=button_id: self._on_card_leave(bid))
        
        # 按钮悬停效果
        open_btn.bind('<Enter>', lambda e, btn=open_btn: self._on_button_enter(btn))
        open_btn.bind('<Leave>', lambda e, btn=open_btn, ac=accent_color: 
                      self._on_button_leave(btn, ac))
    
    def _on_card_enter(self, button_id):
        """卡片悬停进入效果"""
        if button_id in self.tool_buttons:
            info = self.tool_buttons[button_id]
            info['card'].configure(bg=self.COLORS['hover'])
            for comp in info['components']:
                comp.configure(bg=self.COLORS['hover'])
    
    def _on_card_leave(self, button_id):
        """卡片悬停离开效果"""
        if button_id in self.tool_buttons:
            info = self.tool_buttons[button_id]
            info['card'].configure(bg=self.COLORS['bg_card'])
            for comp in info['components']:
                comp.configure(bg=self.COLORS['bg_card'])
    
    def _on_button_enter(self, button):
        """按钮悬停进入效果"""
        button.configure(bg='#1e293b', fg='#ffffff')
    
    def _on_button_leave(self, button, accent_color):
        """按钮悬停离开效果"""
        button.configure(bg=accent_color, fg='#ffffff')
    
    def _create_footer(self, parent):
        """创建页脚"""
        footer_frame = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        footer_frame.pack(fill="x", pady=(30, 10))
        
        # 分隔线
        separator = tk.Frame(
            footer_frame,
            bg=self.COLORS['border'],
            height=1
        )
        separator.pack(fill="x", pady=(0, 15))
        
        # 版权信息
        copyright_label = tk.Label(
            footer_frame,
            text=f"© 2026 工具箱  •  版本 {VERSION}  •  Made with ❤️",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_muted'],
            bg=self.COLORS['bg_primary']
        )
        copyright_label.pack()
    
    def hide(self):
        """隐藏主窗口"""
        self.root.withdraw()
    
    def show(self):
        """显示主窗口"""
        self.root.deiconify()
    
    def function_one(self):
        # 隐藏主窗口
        self.hide()
        # 打开日期转换窗口
        DateConverterWindow(self.root, self)
    
    def function_two(self):
        # 隐藏主窗口
        self.hide()
        # 打开文件格式转换窗口
        FileFormatConverterWindow(self.root, self)
    
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
        self.hide()
        # 打开数据清洗窗口
        DataCleanerWindow(self.root, self)
    
    def function_seven(self):
        # 隐藏主窗口
        self.hide()
        # 打开Codelist处理窗口
        CodelistProcessorWindow(self.root, self)
    
    def function_eight(self):
        # 隐藏主窗口
        self.hide()
        # 打开数据模糊化窗口
        DataMaskingWindow(self.root, self)
    
    def function_nine(self):
        # 隐藏主窗口
        self.hide()
        # 打开CSV引号去除窗口
        CsvQuoteRemoverWindow(self.root, self)
    
    def function_ten(self):
        # 隐藏主窗口
        self.hide()
        # 打开全角转半角转换窗口
        FullwidthHalfwidthConverterWindow(self.root, self)

    def function_eleven(self):
        # 隐藏主窗口
        self.hide()
        # 打开获取文件字段窗口
        FileFieldExtractorWindow(self.root, self)

    def function_twelve(self):
        # 隐藏主窗口
        self.hide()
        # 打开死链检测窗口
        DeadLinkCheckerWindow(self.root, self)

    def on_closing(self):
        """处理窗口关闭事件"""
        # 强制退出程序
        import os
        os._exit(0)
