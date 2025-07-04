﻿import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from ...utils.data_cleaning import DataCleaner

class DataCleanerWindow:
    """数据清理窗口"""
    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("数据清理工具")
        self.window.geometry("800x600")
        self.window.configure(bg='#f0f0f0')
        
        # 保存主窗口引用
        self.main_window = main_window
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置拖放
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind('<<Drop>>', self.handle_drop)
        
        # 初始化输出路径
        self.output_path = None
        
        # 初始化转换器
        self.converter = DataCleaner()
        
        self._create_widgets()
        
        # 设置窗口最小尺寸
        self.window.update()
        self.window.minsize(800, 600)
    
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
            text="数据清理工具",
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
        
        # 创建文件选择区域
        file_frame = tk.Frame(main_frame, bg='#f0f0f0')
        file_frame.pack(fill=tk.X, pady=(0, 20))
        
        upload_rule_btn = tk.Button(
            file_frame,
            text="上传仕样书",
            command=self.select_rule_file,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#f1c40f',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        upload_rule_btn.pack(side=tk.LEFT, padx=5)
        
        
        # 文件选择按钮
        select_file_btn = tk.Button(
            file_frame,
            text="选择文件",
            command=self.select_file,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#3498db',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        select_file_btn.pack(side=tk.LEFT, padx=5)
        
        select_folder_btn = tk.Button(
            file_frame,
            text="选择文件夹",
            command=self.select_folder,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#3498db',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        select_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加清空列表按钮
        clear_list_btn = tk.Button(
            file_frame,
            text="清空列表",
            command=self.clear_file_list,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#e74c3c',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        clear_list_btn.pack(side=tk.LEFT, padx=5)
        
        # 绑定清空列表按钮悬停事件
        clear_list_btn.bind('<Enter>', lambda e: clear_list_btn.configure(bg='#c0392b'))
        clear_list_btn.bind('<Leave>', lambda e: clear_list_btn.configure(bg='#e74c3c'))
        
        # 文件列表标签
        list_label = tk.Label(
            main_frame,
            text="待处理文件：",
            font=('Microsoft YaHei UI', 12),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        list_label.pack(anchor='w')
        
        # 创建列表框架
        list_frame = tk.Frame(main_frame, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # 文件列表
        self.file_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 10),
            selectmode=tk.EXTENDED
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 输出路径选择区域
        output_frame = tk.Frame(main_frame, bg='#f0f0f0')
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 输出路径标签
        output_label = tk.Label(
            output_frame,
            text="输出路径：",
            font=('Microsoft YaHei UI', 11),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        output_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 输出路径显示
        self.output_path_var = tk.StringVar(value="默认输出到原文件所在目录")
        self.output_path_label = tk.Label(
            output_frame,
            textvariable=self.output_path_var,
            font=('Microsoft YaHei UI', 10),
            fg='#7f8c8d',
            bg='#f0f0f0',
            anchor=tk.W
        )
        self.output_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 选择输出路径按钮
        select_output_btn = tk.Button(
            output_frame,
            text="选择输出路径",
            command=self.select_output_path,
            width=15,
            height=1,
            font=('Microsoft YaHei UI', 11),
            bg='#3498db',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        select_output_btn.pack(side=tk.RIGHT)
        
        # 进度显示区域
        progress_frame = tk.Frame(main_frame, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=(10, 5))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 进度详情标签
        self.progress_label = tk.Label(
            progress_frame,
            text="",
            font=('Microsoft YaHei UI', 10),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        self.progress_label.pack(fill=tk.X)
        
        # 转换按钮
        self.convert_btn = tk.Button(
            main_frame,
            text="开始转换",
            command=self.convert_files,
            width=20,
            height=2,
            font=('Microsoft YaHei UI', 11),
            bg='#2ecc71',
            fg='white',
            relief='flat',
            cursor='hand2'
        )
        self.convert_btn.pack(pady=10)
        
        # 状态标签
        self.status_label = tk.Label(
            main_frame,
            text="",
            font=('Microsoft YaHei UI', 10),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        self.status_label.pack(pady=(5, 0))
        
        # 绑定按钮悬停事件
        select_file_btn.bind('<Enter>', lambda e: select_file_btn.configure(bg='#2980b9'))
        select_file_btn.bind('<Leave>', lambda e: select_file_btn.configure(bg='#3498db'))
        select_folder_btn.bind('<Enter>', lambda e: select_folder_btn.configure(bg='#2980b9'))
        select_folder_btn.bind('<Leave>', lambda e: select_folder_btn.configure(bg='#3498db'))
        select_output_btn.bind('<Enter>', lambda e: select_output_btn.configure(bg='#2980b9'))
        select_output_btn.bind('<Leave>', lambda e: select_output_btn.configure(bg='#3498db'))
        self.convert_btn.bind('<Enter>', lambda e: self.convert_btn.configure(bg='#27ae60'))
        self.convert_btn.bind('<Leave>', lambda e: self.convert_btn.configure(bg='#2ecc71'))
        back_btn.bind('<Enter>', lambda e: back_btn.configure(bg='#c0392b'))
        back_btn.bind('<Leave>', lambda e: back_btn.configure(bg='#e74c3c'))
    
    def back_to_main(self):
        """返回主界面"""
        self.window.destroy()
        self.main_window.show()
    
    def on_closing(self):
        """处理窗口关闭事件"""
        self.window.destroy()
        self.main_window.show()
    
    def update_progress(self, current: int, total: int, current_file: str):
        """更新进度显示"""
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_label.config(text=f"正在处理: {current_file} ({current}/{total})")
        self.window.update()
    
    def handle_drop(self, event):
        """处理文件拖放"""
        files = self.window.tk.splitlist(event.data)
        for file in files:
            if os.path.isfile(file) and file.lower().endswith('.csv'):
                if file not in self.file_listbox.get(0, tk.END):
                    self.file_listbox.insert(tk.END, file)
            elif os.path.isdir(file):
                # 如果是文件夹，添加所有CSV文件
                for root, _, filenames in os.walk(file):
                    for filename in filenames:
                        if filename.lower().endswith('.csv'):
                            full_path = os.path.join(root, filename)
                            if full_path not in self.file_listbox.get(0, tk.END):
                                self.file_listbox.insert(tk.END, full_path)
    
    def select_file(self):
        """选择单个或多个文件"""
        files = filedialog.askopenfilenames(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv")]
        )
        for file in files:
            if file not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, file)
                
    def select_rule_file(self):
        """选择EXCEL仕样书文件"""
        file_path = filedialog.askopenfilename(
            title="选择仕样书文件",
            filetypes=[("Excel files", "*.xlsx")]
            )
        if file_path:
            try:
                # 调用DataCleaner的select_rule_file方法处理仕样书文件
                self.converter.select_rule_file(file_path)
                self.rule_file = file_path
                self.status_label.config(text=f"已加载仕样书: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("错误", f"加载仕样书时发生错误: {str(e)}")

    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择包含CSV文件的文件夹")
        if folder:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.csv'):
                        full_path = os.path.join(root, file)
                        if full_path not in self.file_listbox.get(0, tk.END):
                            self.file_listbox.insert(tk.END, full_path)
    
    def select_output_path(self):
        """选择输出路径"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_path_var.set(f"输出到: {folder}")
    
    def convert_files(self):
        """转换文件"""
        files = list(self.file_listbox.get(0, tk.END))
        if not files:
            messagebox.showwarning("警告", "请先选择要转换的CSV文件！")
            return
        
        # 检查是否已加载仕样书
        if not hasattr(self.converter, 'rule_file') or self.converter.rule_file is None:
            messagebox.showwarning("警告", "请先上传仕样书！")
            return
        
        # 禁用转换按钮
        self.convert_btn.config(state=tk.DISABLED)
        
        try:
            # 开始转换
            total = len(files)
            success_count = 0
            error_files = []
            
            for i, file in enumerate(files, 1):
                try:
                    # 更新进度
                    filename = os.path.basename(file)
                    self.update_progress(i, total, filename)
                    
                    # 转换文件
                    success = self.converter.clean_csv_file(file, self.output_path)
                    if success:
                        success_count += 1
                    else:
                        error_files.append(file)
                    
                except Exception as e:
                    error_files.append(f"{file} (错误: {str(e)})")
            
            # 显示结果
            if error_files:
                error_msg = "以下文件转换失败：\n\n" + "\n".join(error_files)
                messagebox.showwarning("转换完成", f"成功转换 {success_count}/{total} 个文件\n\n{error_msg}")
            else:
                messagebox.showinfo("转换完成", f"成功转换所有 {total} 个文件！")
            
            # 清空进度显示
            self.progress_var.set(0)
            self.progress_label.config(text="")
            
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中发生错误：{str(e)}")
        
        finally:
            # 恢复按钮
            self.convert_btn.configure(state=tk.NORMAL) 
    
    def clear_file_list(self):
        """清空文件列表"""
        self.file_listbox.delete(0, tk.END)
        self.status_label.config(text="") 
        
