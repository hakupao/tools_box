import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from tkinterdnd2 import DND_FILES

from ...utils.file_field_extractor import FileFieldExtractor
from ..theme import get_theme


class FileFieldExtractorWindow:
    """GUI window for file field extraction."""

    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("获取文件字段")
        self.window.geometry("900x600")
        self.theme = get_theme(self.window)
        self.colors = self.theme.colors
        self.fonts = self.theme.fonts
        self.window.configure(bg=self.colors.bg)

        self.main_window = main_window
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 拖拽支持
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind("<<Drop>>", self.handle_drop)

        self.extractor = FileFieldExtractor()

        self.folder_path_var = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar()
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.header_row_var = tk.StringVar(value="1")

        self._create_widgets()

        self.window.update()
        self.window.minsize(900, 600)

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
            text="获取文件字段",
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

        path_frame = tk.Frame(main_frame, bg=colors.surface)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        path_label = tk.Label(
            path_frame,
            text="文件夹路径：",
            font=fonts["body"],
            bg=colors.surface,
            fg=colors.text,
        )
        path_label.pack(side=tk.LEFT, padx=(0, 10))

        path_entry = tk.Entry(
            path_frame,
            textvariable=self.folder_path_var,
            font=fonts["body"],
            width=50,
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.theme.style_entry(path_entry)

        select_folder_btn = tk.Button(
            path_frame,
            text="选择文件夹",
            command=self.select_folder,
            width=15,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        select_folder_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.theme.style_button(select_folder_btn, variant="secondary")

        clear_btn = tk.Button(
            path_frame,
            text="清空",
            command=self.clear_folder_path,
            width=10,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        clear_btn.pack(side=tk.LEFT)
        self.theme.style_button(clear_btn, variant="ghost")

        option_frame = tk.Frame(main_frame, bg=colors.surface)
        option_frame.pack(fill=tk.X, pady=(0, 15))

        include_subfolders_cb = tk.Checkbutton(
            option_frame,
            text="包含子文件夹",
            variable=self.include_subfolders_var,
            font=fonts["small"],
        )
        include_subfolders_cb.pack(side=tk.LEFT)
        self.theme.style_checkbutton(include_subfolders_cb)

        header_frame = tk.Frame(option_frame, bg=colors.surface)
        header_frame.pack(side=tk.LEFT, padx=(20, 0))

        header_label = tk.Label(
            header_frame,
            text="列名行：",
            font=fonts["small"],
            fg=colors.text,
            bg=colors.surface,
        )
        header_label.pack(side=tk.LEFT)

        header_spin = tk.Spinbox(
            header_frame,
            from_=1,
            to=999,
            width=5,
            textvariable=self.header_row_var,
            font=fonts["small"],
        )
        header_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.theme.style_spinbox(header_spin)

        progress_frame = tk.Frame(main_frame, bg=colors.surface)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        progress_bar.pack(fill=tk.X, expand=True)

        progress_label = tk.Label(
            progress_frame,
            textvariable=self.progress_text,
            font=fonts["small"],
            fg=colors.text_muted,
            bg=colors.surface,
        )
        progress_label.pack(anchor=tk.W, pady=(5, 0))

        button_frame = tk.Frame(main_frame, bg=colors.surface)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        self.extract_btn = tk.Button(
            button_frame,
            text="开始提取字段",
            command=self.start_extraction,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief="flat",
            cursor="hand2",
        )
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.theme.style_button(self.extract_btn, variant="primary")

        log_frame = tk.Frame(main_frame, bg=colors.surface)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label = tk.Label(
            log_frame,
            text="字段预览：",
            font=fonts["body_bold"],
            fg=colors.text,
            bg=colors.surface,
        )
        log_label.pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=fonts["mono"],
            height=15,
            wrap=tk.NONE,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.theme.style_text(self.log_text)

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择包含数据文件的文件夹")
        if folder:
            self.folder_path_var.set(folder)

    def clear_folder_path(self):
        self.folder_path_var.set("")
        self.progress_var.set(0)
        self.progress_text.set("")
        self._update_log("")

    def start_extraction(self):
        folder_path = self.folder_path_var.get().strip()
        if not folder_path:
            messagebox.showwarning("提示", "请先选择文件夹路径。")
            return

        try:
            self.extract_btn.configure(state=tk.DISABLED)
            self.progress_var.set(0)
            self.progress_text.set("")
            self._update_log("开始提取字段...\n")

            try:
                header_row = int(self.header_row_var.get())
            except ValueError:
                messagebox.showwarning("提示", "列名行请输入有效的数字。")
                return

            if header_row < 1:
                messagebox.showwarning("提示", "列名行必须大于等于 1。")
                return

            result = self.extractor.extract_fields(
                folder_path,
                include_subfolders=self.include_subfolders_var.get(),
                header_row=header_row,
                progress_callback=self.update_progress,
            )

            output_file = result["output_file"]
            errors = result["errors"]
            details = result["details"]
            total_fields = result["total_fields"]
            processed_files = result["processed_files"]

            preview_lines = [f"输出文件：{output_file}"]
            preview_lines.append(
                f"共处理 {processed_files} 个文件，提取字段 {total_fields} 个。"
            )
            if errors:
                preview_lines.append("\n出现问题的文件：")
                preview_lines.extend(f"- {err}" for err in errors)

            preview_lines.append("\n字段列表预览：")
            for rel_path, fields in self._format_details(folder_path, details):
                if not fields:
                    preview_lines.append(f"{rel_path} -> 未检测到字段")
                else:
                    preview_lines.append(f"{rel_path}:")
                    preview_lines.extend(f"  - {field}" for field in fields[:20])
                    if len(fields) > 20:
                        preview_lines.append("  ...")

            self._update_log("\n".join(preview_lines))
            messagebox.showinfo("完成", f"字段提取完成！结果已保存至：\n{output_file}")

        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("错误", f"提取字段时发生错误：{exc}")
            self._update_log(f"提取失败：{exc}")
        finally:
            self.extract_btn.configure(state=tk.NORMAL)
            self.progress_text.set("")
            self.progress_var.set(0)

    def update_progress(self, current: int, total: int, filename: str):
        if total <= 0:
            return
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_text.set(f"正在处理：{filename} ({current}/{total})")
        self.window.update_idletasks()

    def handle_drop(self, event):
        paths = self.window.tk.splitlist(event.data)
        for path in paths:
            if os.path.isdir(path):
                self.folder_path_var.set(path)
                break

    def back_to_main(self):
        self.window.destroy()
        self.main_window.show()

    def on_closing(self):
        self.window.destroy()
        self.main_window.show()

    def _update_log(self, content: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        if content:
            self.log_text.insert(tk.END, content)
        self.log_text.configure(state=tk.DISABLED)

    def _format_details(self, folder_path: str, details):
        formatted = []
        for absolute_path, fields in details.items():
            rel = os.path.relpath(absolute_path, folder_path)
            formatted.append((rel, fields))
        formatted.sort()
        return formatted
