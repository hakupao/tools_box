import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from tkinterdnd2 import DND_FILES

from ...utils.file_field_extractor import FileFieldExtractor


class FileFieldExtractorWindow:
    """GUI window for file field extraction."""

    def __init__(self, parent, main_window):
        self.window = tk.Toplevel(parent)
        self.window.title("获取文件字段")
        self.window.geometry("900x600")
        self.window.configure(bg="#f0f0f0")

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
        self.last_output_file: str | None = None

        self._create_widgets()

        self.window.update()
        self.window.minsize(900, 600)

    def _create_widgets(self):
        main_frame = tk.Frame(self.window, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            title_frame,
            text="获取文件字段",
            font=("Microsoft YaHei UI", 20, "bold"),
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

        path_frame = tk.Frame(main_frame, bg="#f0f0f0")
        path_frame.pack(fill=tk.X, pady=(0, 15))

        path_label = tk.Label(
            path_frame,
            text="文件夹路径：",
            font=("Microsoft YaHei UI", 11),
            bg="#f0f0f0",
            fg="#2c3e50",
        )
        path_label.pack(side=tk.LEFT, padx=(0, 10))

        path_entry = tk.Entry(
            path_frame,
            textvariable=self.folder_path_var,
            font=("Microsoft YaHei UI", 11),
            width=50,
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        select_folder_btn = tk.Button(
            path_frame,
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
        select_folder_btn.pack(side=tk.LEFT, padx=(0, 5))

        clear_btn = tk.Button(
            path_frame,
            text="清空",
            command=self.clear_folder_path,
            width=10,
            height=1,
            font=("Microsoft YaHei UI", 11),
            bg="#95a5a6",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        clear_btn.pack(side=tk.LEFT)

        option_frame = tk.Frame(main_frame, bg="#f0f0f0")
        option_frame.pack(fill=tk.X, pady=(0, 15))

        include_subfolders_cb = tk.Checkbutton(
            option_frame,
            text="包含子文件夹",
            variable=self.include_subfolders_var,
            font=("Microsoft YaHei UI", 10),
            bg="#f0f0f0",
            fg="#2c3e50",
            activebackground="#f0f0f0",
            selectcolor="#f0f0f0",
        )
        include_subfolders_cb.pack(side=tk.LEFT)

        progress_frame = tk.Frame(main_frame, bg="#f0f0f0")
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
            font=("Microsoft YaHei UI", 10),
            fg="#7f8c8d",
            bg="#f0f0f0",
        )
        progress_label.pack(anchor=tk.W, pady=(5, 0))

        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=(0, 15))

        self.extract_btn = tk.Button(
            button_frame,
            text="开始提取字段",
            command=self.start_extraction,
            width=20,
            height=2,
            font=("Microsoft YaHei UI", 11),
            bg="#2ecc71",
            fg="white",
            relief="flat",
            cursor="hand2",
        )
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.open_output_btn = tk.Button(
            button_frame,
            text="打开结果文件夹",
            command=self.open_output_folder,
            width=20,
            height=2,
            font=("Microsoft YaHei UI", 11),
            bg="#9b59b6",
            fg="white",
            relief="flat",
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.open_output_btn.pack(side=tk.LEFT)

        log_frame = tk.Frame(main_frame, bg="#f0f0f0")
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label = tk.Label(
            log_frame,
            text="字段预览：",
            font=("Microsoft YaHei UI", 11),
            fg="#2c3e50",
            bg="#f0f0f0",
        )
        log_label.pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Microsoft YaHei UI", 10),
            height=15,
            wrap=tk.NONE,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 悬停效果
        select_folder_btn.bind(
            "<Enter>", lambda e: select_folder_btn.configure(bg="#2980b9")
        )
        select_folder_btn.bind(
            "<Leave>", lambda e: select_folder_btn.configure(bg="#3498db")
        )
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(bg="#7f8c8d"))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(bg="#95a5a6"))
        self.extract_btn.bind(
            "<Enter>", lambda e: self.extract_btn.configure(bg="#27ae60")
        )
        self.extract_btn.bind(
            "<Leave>", lambda e: self.extract_btn.configure(bg="#2ecc71")
        )
        self.open_output_btn.bind(
            "<Enter>", lambda e: self.open_output_btn.configure(bg="#8e44ad")
        )
        self.open_output_btn.bind(
            "<Leave>", lambda e: self.open_output_btn.configure(bg="#9b59b6")
        )
        back_btn.bind("<Enter>", lambda e: back_btn.configure(bg="#c0392b"))
        back_btn.bind("<Leave>", lambda e: back_btn.configure(bg="#e74c3c"))

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择包含数据文件的文件夹")
        if folder:
            self.folder_path_var.set(folder)

    def clear_folder_path(self):
        self.folder_path_var.set("")
        self.progress_var.set(0)
        self.progress_text.set("")
        self._update_log("")
        self.open_output_btn.configure(state=tk.DISABLED)
        self.last_output_file = None

    def start_extraction(self):
        folder_path = self.folder_path_var.get().strip()
        if not folder_path:
            messagebox.showwarning("提示", "请先选择文件夹路径。")
            return

        self.last_output_file = None
        try:
            self.extract_btn.configure(state=tk.DISABLED)
            self.open_output_btn.configure(state=tk.DISABLED)
            self.progress_var.set(0)
            self.progress_text.set("")
            self._update_log("开始提取字段...\n")

            result = self.extractor.extract_fields(
                folder_path,
                include_subfolders=self.include_subfolders_var.get(),
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
            self.last_output_file = output_file
            self.open_output_btn.configure(state=tk.NORMAL)

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

    def open_output_folder(self):
        if not self.last_output_file:
            return
        output_folder = os.path.dirname(self.last_output_file)
        if os.path.isdir(output_folder):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(output_folder)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", output_folder])
                else:
                    subprocess.Popen(["xdg-open", output_folder])
            except OSError:
                messagebox.showwarning("提示", f"无法打开目录：{output_folder}")

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
