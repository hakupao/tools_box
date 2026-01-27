import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES

from ...utils.xlsx_sheet_splitter import XlsxSheetSplitter
from ..theme import get_theme


class XlsxSheetSplitterWindow:
    """Excel 工作表拆分工具窗口。"""

    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("工作表拆分工具")
        self.window.geometry("850x600")
        self.theme = get_theme(self.window)
        self.colors = self.theme.colors
        self.fonts = self.theme.fonts
        self.window.configure(bg=self.colors.bg)

        self.main_window = main_window
        self.output_path = None

        self.sheet_splitter = XlsxSheetSplitter()

        self.input_file_var = tk.StringVar()
        self.output_path_var = tk.StringVar(value="默认输出到原文件所在目录")
        self.progress_var = tk.DoubleVar()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind("<<Drop>>", self.handle_drop)

        self._create_widgets()
        self.window.update()
        self.window.minsize(850, 600)

    def _create_widgets(self):
        colors = self.colors
        fonts = self.fonts

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

        title_frame = tk.Frame(main_frame, bg=colors.surface)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            title_frame,
            text="工作表拆分工具",
            font=fonts["title"],
            fg=colors.text,
            bg=colors.surface,
        )
        title_label.pack(side=tk.LEFT)

        back_btn = tk.Button(
            title_frame,
            text="返回主界面",
            command=self.back_to_main,
            width=15,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        back_btn.pack(side=tk.RIGHT)
        self.theme.style_button(back_btn, variant="secondary")

        info_label = tk.Label(
            main_frame,
            text="提示：每次只支持处理一个 Excel 文件",
            font=fonts["small"],
            fg=colors.text_muted,
            bg=colors.surface,
            anchor="w",
        )
        info_label.pack(fill=tk.X, pady=(0, 10))

        file_frame = tk.Frame(main_frame, bg=colors.surface)
        file_frame.pack(fill=tk.X, pady=(0, 15))

        file_label = tk.Label(
            file_frame,
            text="Excel 文件：",
            font=fonts["body"],
            fg=colors.text,
            bg=colors.surface,
        )
        file_label.pack(side=tk.LEFT, padx=(0, 10))

        file_entry = tk.Entry(
            file_frame,
            textvariable=self.input_file_var,
            font=fonts["small"],
            state="readonly",
        )
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.theme.style_entry(file_entry)

        select_file_btn = tk.Button(
            file_frame,
            text="选择文件",
            command=self.select_file,
            width=12,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        select_file_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.theme.style_button(select_file_btn, variant="secondary")

        clear_btn = tk.Button(
            file_frame,
            text="清空",
            command=self.clear_file,
            width=8,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        clear_btn.pack(side=tk.LEFT)
        self.theme.style_button(clear_btn, variant="ghost")

        output_frame = tk.Frame(main_frame, bg=colors.surface)
        output_frame.pack(fill=tk.X, pady=(0, 10))

        output_label = tk.Label(
            output_frame,
            text="输出路径：",
            font=fonts["body"],
            fg=colors.text,
            bg=colors.surface,
        )
        output_label.pack(side=tk.LEFT, padx=(0, 10))

        output_path_label = tk.Label(
            output_frame,
            textvariable=self.output_path_var,
            font=fonts["small"],
            fg=colors.text_muted,
            bg=colors.surface,
            anchor=tk.W,
        )
        output_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        select_output_btn = tk.Button(
            output_frame,
            text="选择输出路径",
            command=self.select_output_path,
            width=15,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        select_output_btn.pack(side=tk.RIGHT)
        self.theme.style_button(select_output_btn, variant="secondary")

        progress_frame = tk.Frame(main_frame, bg=colors.surface)
        progress_frame.pack(fill=tk.X, pady=(10, 5))

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
            font=fonts["small"],
            fg=colors.text_muted,
            bg=colors.surface,
        )
        self.progress_label.pack(fill=tk.X)

        self.split_btn = tk.Button(
            main_frame,
            text="开始拆分",
            command=self.split_file,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief="flat",
            cursor="hand2",
        )
        self.split_btn.pack(pady=10)
        self.theme.style_button(self.split_btn, variant="primary")

        self.status_label = tk.Label(
            main_frame,
            text="",
            font=fonts["small"],
            fg=colors.text_muted,
            bg=colors.surface,
        )
        self.status_label.pack(pady=(5, 0))

    def back_to_main(self):
        self.window.destroy()
        self.main_window.show()

    def on_closing(self):
        self.window.destroy()
        self.main_window.show()

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx")],
        )
        if file_path:
            self._set_file(file_path)

    def clear_file(self):
        self.input_file_var.set("")
        self.status_label.config(text="")
        self.progress_var.set(0)
        self.progress_label.config(text="")

    def select_output_path(self):
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_path = folder
            self.output_path_var.set(f"输出到: {folder}")

    def handle_drop(self, event):
        files = self.window.tk.splitlist(event.data)
        xlsx_files = [
            path
            for path in files
            if os.path.isfile(path) and path.lower().endswith(".xlsx")
        ]
        if not xlsx_files:
            return

        if len(xlsx_files) > 1:
            messagebox.showwarning("提示", "仅支持一次处理一个Excel文件，已选择第一个文件。")

        self._set_file(xlsx_files[0])

    def _set_file(self, file_path: str):
        self.input_file_var.set(file_path)
        self.status_label.config(text=f"已选择: {os.path.basename(file_path)}")

    def update_progress(self, current: int, total: int, sheet_name: str):
        if total <= 0:
            return
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_label.config(text=f"正在处理: {sheet_name} ({current}/{total})")
        self.window.update_idletasks()

    def split_file(self):
        input_file = self.input_file_var.get().strip()
        if not input_file:
            messagebox.showwarning("提示", "请先选择要处理的 Excel 文件。")
            return

        self.split_btn.configure(state=tk.DISABLED)
        try:
            self.progress_var.set(0)
            self.progress_label.config(text="")

            result = self.sheet_splitter.split_file(
                input_file,
                output_path=self.output_path,
                progress_callback=self.update_progress,
            )

            total = result["total_sheets"]
            output_files = result["output_files"]
            errors = result["errors"]
            output_dir = result["output_dir"]

            if errors:
                error_msg = "\n".join(errors)
                messagebox.showwarning(
                    "处理完成",
                    f"已生成 {len(output_files)}/{total} 个 CSV 文件。\n\n"
                    f"输出目录：{output_dir}\n\n错误详情：\n{error_msg}",
                )
            else:
                messagebox.showinfo(
                    "处理完成",
                    f"成功拆分 {total} 个工作表！\n\n输出目录：{output_dir}",
                )

            self.status_label.config(text=f"输出目录: {output_dir}")
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("错误", f"拆分过程中发生错误：{exc}")
        finally:
            self.split_btn.configure(state=tk.NORMAL)
            self.progress_var.set(0)
            self.progress_label.config(text="")
