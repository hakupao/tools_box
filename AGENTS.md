# 给编码代理的说明（tools_box / DataForge Studio v3）

本文件写给在本仓库改代码的代理。每条规则后面写了原因；不确定时以原因判断。

## 项目概况

- Windows 桌面数据工具箱，PySide6 + QFluentWidgets（`PySide6-Fluent-Widgets`），Excel 读写用 openpyxl，EDC 用 pywin32 COM、pyautogui、keyboard、mouse、pyperclip。
- 包名 `dataforge`，源码在 `src/dataforge/`，版本号只写在 `src/dataforge/__init__.py` 的 `__version__`（当前 3.0.0）。`pyproject.toml` 的 `version` 和 `CHANGELOG.md` 的版本标题跟它保持一致，由 `tests/dataforge/test_release.py` 锁定；`packaging/scripts/build_installer.ps1` 打包时直接读取它。
- 入口：`python -m dataforge`（`src/dataforge/__main__.py` → `dataforge.app.main`）。
- 设计文档：`docs/superpowers/specs/2026-10-29-dataforge-v3-rebuild-design.md`。工具规则的唯一出处：`docs/tools/*.md`。

包结构（分层见下一节）：

```
src/dataforge/
  core/      Result、FileIssue、EncodingQuestion、异常、进度与取消、日志
  fileio/    编码识别、读写 CSV/文本、输出路径、原子写入
  config/    ConfigStore（JSON 分 section）、v2 配置迁移、最近使用
  dates.py   所有日期解析和标准化
  tools/     各工具后端，一个工具一个模块或子包（format_convert、sheet_split、
             field_extract、masking/、edc/、date_convert、width_convert）
  ui/        外壳 shell.py、registry.py、home.py、settings.py、theme.py、layout.py、
             jobs.py（JobRunner）、gc_guard.py、components/（公共组件，含 ToolPage）、
             pages/（各工具页面）
  app.py     QApplication 启动、--self-check
  selfcheck.py  打包自检
```

## 环境与命令

在仓库根目录执行（PowerShell）：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m dataforge
```

- `pip install -e .` 必须做：`python -m dataforge` 和 `build_onedir.ps1`（用 venv 的 Python 取日志目录）都依赖它。
- 全部测试：`.venv/Scripts/python.exe -m pytest tests -q`
- 单个文件：`.venv/Scripts/python.exe -m pytest tests/dataforge/test_format_convert.py -q`
- 打包：`powershell -ExecutionPolicy Bypass -File .\packaging\scripts\build_onedir.ps1 -Clean`，再 `build_installer.ps1`，详见 `packaging/README.md`。
- README 截图：`.venv\Scripts\python scripts\capture_screenshots.py`（必须在真实桌面运行，会短暂打开窗口，使用临时配置）。
- 提交前至少跑一遍与改动相关的测试；改了公共组件、配置或 IO 就跑全部测试。

## 分层规则

- 后端（`core`、`fileio`、`config`、`dates.py`、`tools`）禁止导入 PySide6 / qfluentwidgets。原因：规则要能脱离界面测试，也要能照着移植到 C#/Rust。`tests/dataforge/test_package.py` 会检查。
- 后端禁止 `print(`，一律用 `logging.getLogger(__name__)`。原因：日志写入文件，并同步显示在页面的"日志"标签页。
- 文件类工具的入口形如 `run(inputs, options, progress, cancel) -> Result`：
  - `options` 是该工具的 dataclass，默认值只在这里写一份，页面不得再写一份默认值；
  - `progress(current, total, label)` 报告进度；`cancel` 是 `CancelToken`，在每个文件或每批行之间调用 `cancel.raise_if_cancelled()`；
  - 非法输入抛 `DataForgeError`（`ValueError` 子类）；单个文件失败记入 `Result` 的错误列表后继续处理下一个；
  - 不读应用配置，配置由页面读出后作为参数传入。
- `Cancelled` 继承 `BaseException`。工具代码不得捕获 `BaseException`、不得写裸 `except:`，唯一例外是清理临时文件后立即原样 `raise`。原因：逐文件的 `except Exception` 不能吞掉取消。
- 业务规则只写在 `tools/`，页面只负责收集输入、提交任务、显示结果。原因：规则写进页面会和规则说明对不上。
- 编码识别、CSV 读写、输出命名、原子写入一律调用 `fileio`，日期一律调用 `dates.py`，不得在工具里另写一套。
- 输出：CSV 用 `utf-8-sig`、行尾 `\r\n`；默认输出新文件，同名时加 `_1`、`_2`；只有用户勾选"覆盖原文件"并确认后才改写原文件；所有写出先写同目录临时文件再替换。

## 界面规则

以下写法在 `src/dataforge/ui/` 中禁止出现（发版前用 grep 检查）：

- 禁止 `setStyleSheet`、QSS 字符串、hex 颜色（`#RRGGBB`）。原因：它们不随主题切换，v2 就是靠几百行 QSS 强制浅色。
- 禁止 `setTextColor(x, x)` 这种亮暗同值的写法；确实需要语义色时用 `setTextColor(亮色, 暗色)` 成对写，并集中在一个模块里定义。
- 禁止 `setFixedWidth` 和按像素写死的宽度（图标尺寸除外：图标用 `setFixedSize` 固定大小）。原因：工具页要在宽 / 中 / 窄三档宽度下自动排版（断点在 `ui/layout.py`：1100、750，最小宽度 640）。
- 禁止 `processEvents`。原因：耗时操作全部放到后台任务里，不靠它维持界面。
- 禁止 `AA_DontUseNativeDialogs`、`DontUseNativeDialog` 和标题栏 DWM 补丁。原因：使用原生文件对话框，主题交给 QFluentWidgets。
- 禁止强制某一种主题。主题默认 `Theme.AUTO`，设置页可改，切换统一调用 `dataforge.ui.theme.apply_theme_mode`。
- 禁止调用 keyboard 的 `unhook_all`。原因：它会清掉程序里全部键盘监听；ESC 热键只注销自己注册的那一个。
- 不得混用会脱离主题的原生 Qt 控件，用 Fluent 组件（`SmoothScrollArea`、`SimpleCardWidget`、`PlainTextEdit`、`TableWidget`、`MessageBoxBase`、`InfoBar` 等）。
- 唯一例外：EDC 录制浮层和回放标记是自绘的，可以用 `QColor(r, g, b, a)` 写在 `paintEvent` 或调色板里，仍然不得写 hex、不得调用 `setStyleSheet`。

其他约定：

- 工具统一登记在 `ui/registry.py` 的 `TOOLS`（id、名称、简介、分组、图标、页面类路径）。主页卡片、侧边栏、页面标题都从这里生成，名称只写一次。页面按需用 `importlib` 加载，所以新页面必须能被 `selfcheck.py` 导入。
- 文件类工具页继承 `ui/components/tool_page.py` 的 `ToolPage`，参数表单用 `ResponsiveForm`，结果区固定为"结果 / 警告 / 日志"三个标签页。
- 结果提示一律用 `InfoBar`；模态对话框只用于需要用户确认的场景，例如覆盖原文件。对话框用完 `deleteLater()`。
- 运行期间锁定输入区和参数区。
- `QScrollArea.setWidget()` 会打开内容控件的 `autoFillBackground`，加入滚动区后要关掉，否则暗色主题下会露出浅色底。

## 后台任务规则

- 所有耗时工作都通过全局唯一的 `JobRunner`（`ui/jobs.py`）提交，同一时间只运行一个任务。原因：EDC 会实际控制鼠标和键盘，不能和其他任务并行。
- 页面不得自己创建线程或 `QThread`。扫描、EDC 分段这类"不是主操作"的工作也走同一个 `JobRunner`，作为辅助任务提交（`current_job_kind()` 返回非 `"run"` 的值，完成后进 `on_aux_finished`）。辅助任务完成时 runner 仍处于忙碌状态，要接着提交下一个任务只能用 `submit_job_when_idle()`。
- 任务函数里不得创建 QObject、不得操作控件、不得调用 `gc.collect()`。原因：自动垃圾回收已关闭，由 `MainThreadGarbageCollector` 在主线程定时回收；在工作线程销毁 Qt 对象会导致崩溃。任务只能通过返回值和信号把结果带回主线程。
- 每个 QObject 都要有父对象或显式 `deleteLater()`。
- 钩子线程（EDC 的鼠标、键盘监听）里的回调只发信号，不直接改界面。

## 配置

- 配置统一由 `config/store.py` 的 `ConfigStore` 读写：一个 JSON 文件，按 section 存储（例如 `app`、`recent`、`data_masking_pattern1`、`edc_site_adder`）。用 `section(name)` 读、`update_section(name, data)` 写，只改自己的 section。
- 路径：`platformdirs.user_config_dir("dataforge_studio", appauthor=False, roaming=False)/dataforge_studio_config.json`；环境变量 `DATAFORGE_STUDIO_CONFIG_PATH`（或旧的 `TOOLS_BOX_CONFIG_PATH`）可以覆盖。测试和截图脚本都要用临时配置，不得读写真实配置。
- 保存是原子的；文件损坏时先备份为 `.corrupt-<时间>.bak` 再用默认值。
- v2 配置迁移统一走 `config/legacy.py` 的 `load_section_with_legacy` / `legacy_file_candidates`，不得另写迁移代码。v2 的 section 名和旧文件名不能改，否则同事升级后要重新配置。
- 已废弃的配置项（数据模糊化的 `subject_sort`、`date_output_format`、`partial_date_policy`，EDC 的 `retry_count`）读取时忽略、保存时不写。
- 修改配置结构要向后兼容：新增键给默认值，旧配置照样能读。

## 测试

- 测试放在 `tests/dataforge/test_<主题>.py`，用 `unittest.TestCase` 风格，由 pytest 运行。
- Qt 测试由 `tests/dataforge/__init__.py` 设为 offscreen，用 `tests/dataforge/qt_helpers.py` 的 `qapp()`。
- 测试中不得导入 pyautogui、keyboard、mouse，不得操作真实的鼠标、键盘、剪贴板或 Excel，用假实现或 patch。唯一例外是 `test_selfcheck.py`，它在子进程里验证这些库能否导入。
- IO 测试用临时目录，断言具体的输出内容，不只断言成功标志。
- 标准样例在 `tests/golden/<tool_id>/<case>/`（`params.json`、`input/`、`expected/`），由 `tests/dataforge/test_golden.py` 对照。格式见 `docs/tools/README.md`。
- 期望输出必须是手写的字面值：Excel 等二进制样例由各目录下的 `make_fixtures.py` 用字面值生成，不得调用被测代码生成期望输出。原因：否则样例只能证明"代码和自己一致"。
- 数据模糊化的样例数据必须是虚构的。

## 规则说明

- `docs/tools/<tool>.md` 是工具规则的唯一出处，写法与编程语言无关，供以后的 C#/Rust 版本对照。
- 改任何工具的行为，必须在同一次提交里同步修改对应的规则说明和标准样例（`tests/golden/`）。原因：三者不一致时，移植版无法验收。
- 其他文档（README、用户手册、开发文档）只链接规则说明，不复制规则内容。

## 文档

- 文档用简体中文。例外：`README.md` 是英文版，`README_CN.md` 是它的中文版，两者内容要对应，改一份就同步改另一份。
- `tests/dataforge/test_release.py` 会扫描 README.md、README_CN.md、AGENTS.md、packaging/README.md 和 `docs/*.md` 中的过期内容（v2 的入口和目录、已移除的依赖、已禁止的 API 名）。确实需要提到时，同一行要写明"禁止 / 不用 / 不得 / 不再 / 移除"。英文的 README.md 写不了这些词，所以其中不得出现这些名称。

## v2 内容

v2 的界面目录、`*_service.py` 服务模块、旧入口脚本、强制浅色主题和配套 QSS 都已移除，不要参照 v2 的写法，也不要恢复这些文件。
