"""
Dead Link Checker GUI Window

This module provides a GUI interface for checking dead links in HTML files.
"""

import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinterdnd2 import DND_FILES

from ...utils.dead_link_checker import DeadLinkChecker
from ..theme import get_theme


class DeadLinkCheckerWindow:
    """GUI window for dead link checking."""

    def __init__(self, parent, main_window):
        """
        Initialize the Dead Link Checker window.

        Args:
            parent: Parent window
            main_window: Reference to main window
        """
        self.window = tk.Toplevel(parent)
        self.window.title("死链检测")
        self.window.geometry("1000x700")
        self.theme = get_theme(self.window)
        self.colors = self.theme.colors
        self.fonts = self.theme.fonts
        self.window.configure(bg=self.colors.bg)

        self.main_window = main_window
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 拖拽支持
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind("<<Drop>>", self.handle_drop)

        self.checker = DeadLinkChecker(timeout=10)

        # Variables
        self.path_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.timeout_var = tk.IntVar(value=10)
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar()
        self.last_output_file: str | None = None
        self.is_checking = False

        self._create_widgets()

        self.window.update()
        self.window.minsize(1000, 700)

    def _create_widgets(self):
        """Create all GUI widgets."""
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

        # Title frame
        title_frame = tk.Frame(main_frame, bg=colors.surface)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(
            title_frame,
            text="死链检测",
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

        # Path selection frame
        path_frame = tk.Frame(main_frame, bg=colors.surface)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        path_label = tk.Label(
            path_frame,
            text="文件/文件夹：",
            font=fonts["body"],
            bg=colors.surface,
            fg=colors.text,
        )
        path_label.pack(side=tk.LEFT, padx=(0, 10))

        path_entry = tk.Entry(
            path_frame,
            textvariable=self.path_var,
            font=fonts["body"],
            width=50,
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.theme.style_entry(path_entry)

        select_file_btn = tk.Button(
            path_frame,
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

        select_folder_btn = tk.Button(
            path_frame,
            text="选择文件夹",
            command=self.select_folder,
            width=12,
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
            command=self.clear_path,
            width=10,
            height=1,
            font=fonts["body"],
            relief="flat",
            cursor="hand2",
        )
        clear_btn.pack(side=tk.LEFT)
        self.theme.style_button(clear_btn, variant="ghost")

        # Base URL frame
        url_frame = tk.Frame(main_frame, bg=colors.surface)
        url_frame.pack(fill=tk.X, pady=(0, 15))

        url_label = tk.Label(
            url_frame,
            text="基础URL (可选)：",
            font=fonts["body"],
            bg=colors.surface,
            fg=colors.text,
        )
        url_label.pack(side=tk.LEFT, padx=(0, 10))

        url_entry = tk.Entry(
            url_frame,
            textvariable=self.base_url_var,
            font=fonts["body"],
        )
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.theme.style_entry(url_entry)

        url_hint = tk.Label(
            url_frame,
            text="用于解析相对链接",
            font=fonts["tiny"],
            fg=colors.text_muted,
            bg=colors.surface,
        )
        url_hint.pack(side=tk.LEFT, padx=(10, 0))

        # Options frame
        option_frame = tk.Frame(main_frame, bg=colors.surface)
        option_frame.pack(fill=tk.X, pady=(0, 15))

        include_subfolders_cb = tk.Checkbutton(
            option_frame,
            text="包含子文件夹",
            variable=self.include_subfolders_var,
            font=fonts["small"],
        )
        include_subfolders_cb.pack(side=tk.LEFT, padx=(0, 20))
        self.theme.style_checkbutton(include_subfolders_cb)

        timeout_label = tk.Label(
            option_frame,
            text="超时时间(秒)：",
            font=fonts["small"],
            bg=colors.surface,
            fg=colors.text,
        )
        timeout_label.pack(side=tk.LEFT, padx=(0, 5))

        timeout_spinbox = tk.Spinbox(
            option_frame,
            from_=5,
            to=60,
            textvariable=self.timeout_var,
            width=10,
            font=fonts["small"],
        )
        timeout_spinbox.pack(side=tk.LEFT)
        self.theme.style_spinbox(timeout_spinbox)

        # Progress frame
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

        # Button frame
        button_frame = tk.Frame(main_frame, bg=colors.surface)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        self.check_btn = tk.Button(
            button_frame,
            text="开始检测",
            command=self.start_checking,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief="flat",
            cursor="hand2",
        )
        self.check_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.theme.style_button(self.check_btn, variant="primary")

        self.open_output_btn = tk.Button(
            button_frame,
            text="打开报告文件夹",
            command=self.open_output_folder,
            width=20,
            height=2,
            font=fonts["body_bold"],
            relief="flat",
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.open_output_btn.pack(side=tk.LEFT)
        self.theme.style_button(self.open_output_btn, variant="secondary")

        # Log frame
        log_frame = tk.Frame(main_frame, bg=colors.surface)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label = tk.Label(
            log_frame,
            text="检测结果：",
            font=fonts["body_bold"],
            fg=colors.text,
            bg=colors.surface,
        )
        log_label.pack(anchor=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=fonts["mono"],
            height=20,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.theme.style_text(self.log_text)

    def select_file(self):
        """Open file dialog to select an HTML file."""
        file = filedialog.askopenfilename(
            title="选择HTML文件",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")]
        )
        if file:
            self.path_var.set(file)

    def select_folder(self):
        """Open folder dialog to select a folder."""
        folder = filedialog.askdirectory(title="选择包含HTML文件的文件夹")
        if folder:
            self.path_var.set(folder)

    def clear_path(self):
        """Clear all input fields and reset state."""
        self.path_var.set("")
        self.base_url_var.set("")
        self.progress_var.set(0)
        self.progress_text.set("")
        self._update_log("")
        self.open_output_btn.configure(state=tk.DISABLED)
        self.last_output_file = None

    def start_checking(self):
        """Start the dead link checking process."""
        if self.is_checking:
            messagebox.showwarning("提示", "正在检测中，请稍候...")
            return

        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择文件或文件夹。")
            return

        if not os.path.exists(path):
            messagebox.showerror("错误", "选择的路径不存在。")
            return

        self.is_checking = True
        self.last_output_file = None

        try:
            self.check_btn.configure(state=tk.DISABLED)
            self.open_output_btn.configure(state=tk.DISABLED)
            self.progress_var.set(0)
            self.progress_text.set("")
            self._update_log("开始检测死链...\n")

            # Update timeout
            self.checker.timeout = self.timeout_var.get()

            base_url = self.base_url_var.get().strip()

            if os.path.isfile(path):
                # Check single file
                self._check_single_file(path, base_url)
            else:
                # Check folder
                self._check_folder(path, base_url)

        except Exception as exc:
            messagebox.showerror("错误", f"检测时发生错误：{exc}")
            self._update_log(f"\n检测失败：{exc}")
        finally:
            self.is_checking = False
            self.check_btn.configure(state=tk.NORMAL)
            self.progress_text.set("")
            self.progress_var.set(0)

    def _check_single_file(self, file_path: str, base_url: str):
        """Check a single HTML file."""
        result = self.checker.check_html_file(
            file_path,
            base_url,
            progress_callback=self.update_progress
        )

        # Generate report
        output_file = self._generate_output_filename(file_path)
        self.checker.generate_report(result, output_file)

        # Display summary
        summary = self._format_summary(result)
        self._update_log(summary)

        messagebox.showinfo("完成", f"检测完成！报告已保存至：\n{output_file}")
        self.last_output_file = output_file
        self.open_output_btn.configure(state=tk.NORMAL)

    def _check_folder(self, folder_path: str, base_url: str):
        """Check all HTML files in a folder."""
        result = self.checker.check_folder(
            folder_path,
            base_url,
            include_subfolders=self.include_subfolders_var.get(),
            progress_callback=self.update_progress
        )

        if result['total_files'] == 0:
            messagebox.showwarning("提示", "未找到HTML文件。")
            self._update_log("未找到HTML文件。")
            return

        # Generate report
        output_file = self._generate_output_filename(folder_path)
        self.checker.generate_report(result, output_file)

        # Display summary
        summary = self._format_folder_summary(result)
        self._update_log(summary)

        messagebox.showinfo("完成", f"检测完成！报告已保存至：\n{output_file}")
        self.last_output_file = output_file
        self.open_output_btn.configure(state=tk.NORMAL)

    def _format_summary(self, result: dict) -> str:
        """Format single file check result as summary text."""
        lines = []
        lines.append(f"文件: {result['file']}")
        lines.append(f"总链接数: {result['total_links']}")
        lines.append(f"唯一链接数: {result['unique_links']}")
        lines.append("")

        summary = result['summary']
        lines.append("检测摘要:")
        lines.append(f"  ✓ 正常: {summary['alive']}")
        lines.append(f"  ✗ 死链: {summary['dead']}")
        lines.append(f"  ⏱ 超时: {summary['timeout']}")
        lines.append(f"  ⚠ 错误: {summary['error']}")
        lines.append(f"  ⊘ 跳过: {summary['skipped']}")
        lines.append("")

        # Separate dead links into confirmed and potential false positives
        confirmed_dead = []
        potential_false_positives = []
        
        for check in result['checks']:
            if check['status'] == 'dead':
                if check['status_code'] == 403 and check.get('error') == 'HEAD blocked, verified with GET':
                    potential_false_positives.append(check)
                else:
                    confirmed_dead.append(check)

        # Show confirmed dead links
        if confirmed_dead:
            lines.append("确认死链（建议检查）:")
            for check in confirmed_dead[:15]:  # Limit to 15
                lines.append(f"  [{check['status_code']}] {check['url']}")
            if len(confirmed_dead) > 15:
                lines.append(f"  ... 还有 {len(confirmed_dead) - 15} 个")
            lines.append("")

        # Show potential false positives
        if potential_false_positives:
            lines.append(f"可能误报（403错误 - 反爬虫保护）: {len(potential_false_positives)}个")
            lines.append("注意: 这些链接在浏览器中可能可以正常访问")
            lines.append("详细列表请查看完整报告")
            lines.append("")

        return "\n".join(lines)

    def _format_folder_summary(self, result: dict) -> str:
        """Format folder check result as summary text."""
        lines = []
        lines.append(f"文件夹: {result['folder']}")
        lines.append(f"总文件数: {result['total_files']}")
        lines.append("")

        total_alive = 0
        total_dead = 0
        total_timeout = 0
        total_error = 0
        total_skipped = 0

        for file_result in result['files']:
            summary = file_result['summary']
            total_alive += summary['alive']
            total_dead += summary['dead']
            total_timeout += summary['timeout']
            total_error += summary['error']
            total_skipped += summary['skipped']

        lines.append("总体摘要:")
        lines.append(f"  ✓ 正常: {total_alive}")
        lines.append(f"  ✗ 死链: {total_dead}")
        lines.append(f"  ⏱ 超时: {total_timeout}")
        lines.append(f"  ⚠ 错误: {total_error}")
        lines.append(f"  ⊘ 跳过: {total_skipped}")
        lines.append("")

        # Show files with dead links
        files_with_dead_links = [
            f for f in result['files'] if f['summary']['dead'] > 0
        ]
        if files_with_dead_links:
            lines.append("包含死链的文件:")
            for file_result in files_with_dead_links[:10]:  # Limit to 10
                file_name = Path(file_result['file']).name
                lines.append(f"  {file_name}: {file_result['summary']['dead']} 个死链")
            if len(files_with_dead_links) > 10:
                lines.append(f"  ... 还有 {len(files_with_dead_links) - 10} 个文件")

        return "\n".join(lines)

    def _generate_output_filename(self, input_path: str) -> str:
        """Generate output filename for the report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.isfile(input_path):
            base_name = Path(input_path).stem
            output_dir = Path(input_path).parent
        else:
            base_name = Path(input_path).name
            output_dir = Path(input_path)

        output_file = output_dir / f"dead_link_report_{base_name}_{timestamp}.txt"
        return str(output_file)

    def update_progress(self, current: int, total: int, item: str):
        """Update progress bar and text."""
        if total <= 0:
            return
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.progress_text.set(f"正在检测: {item} ({current}/{total})")
        self.window.update_idletasks()

    def handle_drop(self, event):
        """Handle drag and drop events."""
        paths = self.window.tk.splitlist(event.data)
        if paths:
            path = paths[0]
            if os.path.isfile(path) and path.lower().endswith(('.html', '.htm')):
                self.path_var.set(path)
            elif os.path.isdir(path):
                self.path_var.set(path)

    def open_output_folder(self):
        """Open the folder containing the output report."""
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
        """Return to main window."""
        self.window.destroy()
        self.main_window.show()

    def on_closing(self):
        """Handle window closing event."""
        if self.is_checking:
            if not messagebox.askokcancel("确认", "正在检测中，确定要关闭吗？"):
                return
        self.window.destroy()
        self.main_window.show()

    def _update_log(self, content: str):
        """Update log text area."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        if content:
            self.log_text.insert(tk.END, content)
        self.log_text.configure(state=tk.DISABLED)
