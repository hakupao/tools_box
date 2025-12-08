import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES

from ...utils.csv_to_xlsx_converter import CsvToXlsxConverter
from ...utils.xlsx_to_csv_converter import XlsxToCsvConverter
from ...utils.csv_encoding_converter import CsvEncodingConverter


class FileFormatConverterWindow:
    """合并的文件格式转换窗口，支持 CSV<->XLSX 和 CSV UTF-8(BOM) 转换。"""

    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("文件格式转换")
        self.window.geometry("850x650")
        self.window.configure(bg="#f0f0f0")

        self.main_window = main_window
        self.output_path = None

        self.csv_to_xlsx = CsvToXlsxConverter()
        self.xlsx_to_csv = XlsxToCsvConverter()
        self.csv_bom = CsvEncodingConverter()

        self.mode_config = {
            "csv_to_xlsx": {
                "label": "CSV 转 XLSX",
                "input_exts": [".csv"],
                "output_note": "默认输出到原文件所在目录",
            },
            "xlsx_to_csv": {
                "label": "XLSX 转 CSV（UTF-8 BOM）",
                "input_exts": [".xlsx"],
                "output_note": "默认输出到原文件所在目录（UTF-8 BOM）",
            },
            "csv_bom": {
                "label": "CSV 转 UTF-8(BOM)",
                "input_exts": [".csv"],
                "output_note": "默认覆盖原文件；选择输出路径则另存",
            },
        }

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind("<<Drop>>", self.handle_drop)

        self._create_widgets()
        self.window.update()
        self.window.minsize(850, 650)

    def _create_widgets(self):
        main_frame = tk.Frame(self.window, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            title_frame,
            text="文件格式转换",
            font=("Microsoft YaHei UI", 22, "bold"),
            fg="#2c3e50",
            bg="#f0f0f0",
        )
        title_label.pack(side=tk.LEFT)

        back_btn = tk.Button(
            title_frame,
            text="返回主界面",
            command=self.back_to_main,
            width=15,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#e74c3c",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        back_btn.pack(side=tk.RIGHT)

        mode_frame = tk.LabelFrame(
            main_frame,
            text="转换类型",
            font=("Microsoft YaHei UI", 11, "bold"),
            fg="#2c3e50",
            bg="#f0f0f0",
            padx=10,
            pady=10,
        )
        mode_frame.pack(fill=tk.X, pady=(0, 15))

        self.mode_var = tk.StringVar(value="csv_to_xlsx")
        for idx, (mode_key, cfg) in enumerate(self.mode_config.items()):
            radio = tk.Radiobutton(
                mode_frame,
                text=cfg["label"],
                variable=self.mode_var,
                value=mode_key,
                font=("Microsoft YaHei UI", 11),
                bg="#f0f0f0",
                anchor="w",
                command=self.on_mode_change,
            )
            radio.grid(row=0, column=idx, padx=10, sticky="w")

        info_frame = tk.Frame(main_frame, bg="#ecf0f1", relief="solid", bd=1)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        self.info_label = tk.Label(
            info_frame,
            text="当前模式：CSV 转 XLSX",
            font=("Microsoft YaHei UI", 10),
            fg="#2c3e50",
            bg="#ecf0f1",
            pady=10,
            anchor="w",
            justify=tk.LEFT,
        )
        self.info_label.pack(fill=tk.X, padx=10)

        file_frame = tk.Frame(main_frame, bg="#f0f0f0")
        file_frame.pack(fill=tk.X, pady=(0, 20))

        select_folder_btn = tk.Button(
            file_frame,
            text="选择文件夹",
            command=self.select_folder,
            width=15,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#3498db",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        select_folder_btn.pack(side=tk.LEFT, padx=5)

        select_file_btn = tk.Button(
            file_frame,
            text="选择文件",
            command=self.select_file,
            width=15,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#3498db",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        select_file_btn.pack(side=tk.LEFT, padx=5)

        clear_list_btn = tk.Button(
            file_frame,
            text="清空列表",
            command=self.clear_file_list,
            width=15,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#e74c3c",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        clear_list_btn.pack(side=tk.LEFT, padx=5)

        list_label = tk.Label(
            main_frame,
            text="待处理文件：",
            font=("Microsoft YaHei UI", 12),
            fg="#2c3e50",
            bg="#f0f0f0",
        )
        list_label.pack(anchor="w")

        list_frame = tk.Frame(main_frame, bg="#f0f0f0")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        self.file_listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            selectmode=tk.EXTENDED,
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        output_frame = tk.Frame(main_frame, bg="#f0f0f0")
        output_frame.pack(fill=tk.X, pady=(0, 10))

        output_label = tk.Label(
            output_frame,
            text="输出路径：",
            font=("Microsoft YaHei UI", 11),
            fg="#2c3e50",
            bg="#f0f0f0",
        )
        output_label.pack(side=tk.LEFT, padx=(0, 10))

        self.output_path_var = tk.StringVar(value=self.mode_config["csv_to_xlsx"]["output_note"])
        self.output_path_label = tk.Label(
            output_frame,
            textvariable=self.output_path_var,
            font=("Microsoft YaHei UI", 10),
            fg="#7f8c8d",
            bg="#f0f0f0",
            anchor=tk.W,
        )
        self.output_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        select_output_btn = tk.Button(
            output_frame,
            text="选择输出路径",
            command=self.select_output_path,
            width=15,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#3498db",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        select_output_btn.pack(side=tk.RIGHT)

        progress_frame = tk.Frame(main_frame, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, pady=(10, 5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.progress_label = tk.Label(
            progress_frame,
            text="",
            font=("Microsoft YaHei UI", 10),
            fg="#7f8c8d",
            bg="#f0f0f0",
        )
        self.progress_label.pack(fill=tk.X)

        self.convert_btn = tk.Button(
            main_frame,
            text="开始转换",
            command=self.convert_files,
            width=20,
            height=2,
            font=("Microsoft YaHei UI", 11),
            bg="#2ecc71",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        self.convert_btn.pack(pady=10)

        self.status_label = tk.Label(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 10),
            fg="#7f8c8d",
            bg="#f0f0f0",
        )
        self.status_label.pack(pady=(5, 0))

        select_folder_btn.bind("<Enter>", lambda e: select_folder_btn.configure(bg="#2980b9"))
        select_folder_btn.bind("<Leave>", lambda e: select_folder_btn.configure(bg="#3498db"))
        select_file_btn.bind("<Enter>", lambda e: select_file_btn.configure(bg="#2980b9"))
        select_file_btn.bind("<Leave>", lambda e: select_file_btn.configure(bg="#3498db"))
        select_output_btn.bind("<Enter>", lambda e: select_output_btn.configure(bg="#2980b9"))
        select_output_btn.bind("<Leave>", lambda e: select_output_btn.configure(bg="#3498db"))
        clear_list_btn.bind("<Enter>", lambda e: clear_list_btn.configure(bg="#c0392b"))
        clear_list_btn.bind("<Leave>", lambda e: clear_list_btn.configure(bg="#e74c3c"))
        self.convert_btn.bind("<Enter>", lambda e: self.convert_btn.configure(bg="#27ae60"))
        self.convert_btn.bind("<Leave>", lambda e: self.convert_btn.configure(bg="#2ecc71"))
        back_btn.bind("<Enter>", lambda e: back_btn.configure(bg="#c0392b"))
        back_btn.bind("<Leave>", lambda e: back_btn.configure(bg="#e74c3c"))

    def on_mode_change(self):
        mode = self.mode_var.get()
        cfg = self.mode_config[mode]
        self.info_label.config(text=f"当前模式：{cfg['label']}")
        if self.output_path:
            self.output_path_var.set(f"输出到: {self.output_path}")
        else:
            self.output_path_var.set(cfg["output_note"])
        removed = self._filter_list_by_mode()
        if removed:
            self.status_label.config(text=f"已移除 {removed} 个不符合当前模式的文件")
        else:
            self.status_label.config(text="")

    def _filter_list_by_mode(self) -> int:
        """移除列表中与当前模式扩展名不匹配的文件。"""
        mode = self.mode_var.get()
        allowed_exts = self.mode_config[mode]["input_exts"]
        files = list(self.file_listbox.get(0, tk.END))
        self.file_listbox.delete(0, tk.END)
        removed = 0
        for file in files:
            if self._is_allowed(file, allowed_exts):
                self.file_listbox.insert(tk.END, file)
            else:
                removed += 1
        return removed

    def back_to_main(self):
        self.window.destroy()
        self.main_window.show()

    def on_closing(self):
        self.window.destroy()
        self.main_window.show()

    def _is_allowed(self, path: str, allowed_exts) -> bool:
        return any(path.lower().endswith(ext) for ext in allowed_exts)

    def handle_drop(self, event):
        files = self.window.tk.splitlist(event.data)
        allowed_exts = self.mode_config[self.mode_var.get()]["input_exts"]
        for file in files:
            if os.path.isfile(file):
                if self._is_allowed(file, allowed_exts) and file not in self.file_listbox.get(0, tk.END):
                    self.file_listbox.insert(tk.END, file)
            elif os.path.isdir(file):
                for root, _, filenames in os.walk(file):
                    for filename in filenames:
                        full_path = os.path.join(root, filename)
                        if self._is_allowed(full_path, allowed_exts) and full_path not in self.file_listbox.get(0, tk.END):
                            self.file_listbox.insert(tk.END, full_path)

    def select_file(self):
        mode = self.mode_var.get()
        allowed_exts = self.mode_config[mode]["input_exts"]
        filetypes = [("CSV文件", "*.csv")] if ".csv" in allowed_exts else [("Excel文件", "*.xlsx")]

        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=filetypes,
        )
        for file in files:
            if self._is_allowed(file, allowed_exts) and file not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, file)

    def select_folder(self):
        mode = self.mode_var.get()
        allowed_exts = self.mode_config[mode]["input_exts"]
        folder = filedialog.askdirectory(title="选择包含文件的文件夹")
        if folder:
            for root, _, files in os.walk(folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    if self._is_allowed(full_path, allowed_exts) and full_path not in self.file_listbox.get(0, tk.END):
                        self.file_listbox.insert(tk.END, full_path)

    def select_output_path(self):
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_path_var.set(f"输出到: {folder}")

    def update_progress(self, current: int, total: int, current_file: str):
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_label.config(text=f"正在处理: {current_file} ({current}/{total})")
        self.window.update()

    def _convert_single(self, file_path: str):
        mode = self.mode_var.get()
        if mode == "csv_to_xlsx":
            return self.csv_to_xlsx.convert_file(file_path, self.output_path)
        if mode == "xlsx_to_csv":
            return self.xlsx_to_csv.convert_file(file_path, self.output_path)
        return self.csv_bom.convert_file(file_path, self.output_path)

    def convert_files(self):
        files = list(self.file_listbox.get(0, tk.END))
        if not files:
            messagebox.showwarning("警告", "请先选择要转换的文件！")
            return

        self.convert_btn.config(state=tk.DISABLED)

        try:
            total = len(files)
            success_count = 0
            error_files = []

            for i, file in enumerate(files, 1):
                try:
                    self.update_progress(i, total, os.path.basename(file))
                    success, error_msg = self._convert_single(file)
                    if success:
                        success_count += 1
                    else:
                        error_files.append(f"{file} (错误: {error_msg})")
                except Exception as e:
                    error_files.append(f"{file} (错误: {str(e)})")

            if error_files:
                error_msg = "以下文件转换失败：\n\n" + "\n".join(error_files)
                messagebox.showwarning("转换完成", f"成功转换 {success_count}/{total} 个文件\n\n{error_msg}")
            else:
                messagebox.showinfo("转换完成", f"成功转换所有 {total} 个文件！")

            self.progress_var.set(0)
            self.progress_label.config(text="")
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中发生错误：{str(e)}")
        finally:
            self.convert_btn.configure(state=tk.NORMAL)

    def clear_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.status_label.config(text="")
