# DataForge Studio 界面规范

适用版本：3.0.0。

本规范适用于 `src/dataforge/ui/` 下的全部界面代码。它取代 v2 的界面规范：v2 那份把"强制浅色主题、hex 调色板、靠 processEvents 维持界面响应"写成了规范，v3 全部反过来，原因见各条。v2 的写法不再适用，不要参照。

一句话原则：**外观交给 QFluentWidgets 和系统，页面只管排版和交互。**

## 1. 主题

- 默认 `Theme.AUTO`，跟随 Windows 的浅色 / 深色设置。设置页可以改为"浅色"或"深色"，选择保存在配置的 `app.theme` 中。
  - 原因：同事的系统有浅色也有深色，强制浅色在深色系统下非常刺眼，也和标题栏、文件对话框不一致。
- 切换主题统一调用 `dataforge.ui.theme.apply_theme_mode(mode)`，`mode` 为 `auto`、`light`、`dark`。不要在别处直接调用 `setTheme`。
- 跟随系统由 `start_system_theme_listener` 负责：守护线程监听系统主题，变化时只发信号，主线程重新应用主题。
- 主窗口开启 Mica 效果（`setMicaEffectEnabled(True)`），在 Windows 11 上背景透出淡淡的桌面色调。
- 文件 / 文件夹选择一律使用系统原生对话框。
  - 原因：原生对话框自带最近位置、收藏夹、网络路径，样式也自动跟随系统主题。
- 所有控件使用 Fluent 组件，它们会随主题自动换色：`SmoothScrollArea`、`SimpleCardWidget`、`CardWidget`、`PlainTextEdit`、`TableWidget`、`ListWidget`、`ComboBox`、`SpinBox`、`CheckBox`、`RadioButton`、`SegmentedWidget`、`MessageBoxBase`、`InfoBar`，以及 `BodyLabel`、`CaptionLabel`、`StrongBodyLabel`、`SubtitleLabel`、`TitleLabel` 等文字标签。

## 2. 禁用清单

以下写法在 `src/dataforge/ui/` 中禁止出现，发版前用 grep 检查。与 [AGENTS.md](../AGENTS.md) 的"界面规则"一致。

| 禁止的写法 | 原因 |
| --- | --- |
| 禁止 `setStyleSheet`、QSS 字符串、hex 颜色（`#RRGGBB`） | 写死的样式不会随主题切换。v2 正是靠几百行 QSS 才把界面强制成浅色，换到深色就全乱了。 |
| 禁止 `setTextColor(x, x)` 这种亮色、暗色同值的写法 | 同一个颜色在浅色和深色背景下总有一边看不清。需要语义色时见第 3 节。 |
| 禁止 `setFixedWidth` 和按像素写死的宽度（图标尺寸除外：图标用 `setFixedSize` 固定大小，见 `ui/home.py`） | 工具页要在宽 / 中 / 窄三档宽度下自动排版，写死宽度会在窄窗口里被截断或出现横向滚动条。 |
| 禁止 `processEvents` | 它会在事件处理中途重入，引起难以复现的问题；耗时操作一律放进后台任务（见第 6 节），界面自然保持响应。 |
| 禁止 `AA_DontUseNativeDialogs`、`DontUseNativeDialog` 和标题栏 DWM 补丁 | 使用原生对话框，主题交给 QFluentWidgets 和系统。v2 为了强制浅色才关掉原生对话框、修改标题栏。 |
| 禁止强制某一种主题 | 默认跟随系统，由用户在设置页决定；切换统一走 `apply_theme_mode`。 |
| 禁止调用 keyboard 的 `unhook_all` | 它会清掉程序里所有键盘监听。EDC 的 ESC 热键只注销自己注册的那一个。 |
| 不得混用会脱离主题的原生 Qt 控件（如 `QLabel`、`QTextEdit`、`QScrollArea`、`QMessageBox`） | 原生控件不读取 Fluent 的主题色，在深色主题下会露出浅色底或黑字。用第 1 节列出的 Fluent 组件代替。 |

**唯一例外：EDC 录制浮层和回放标记。** 它们是自绘的置顶半透明窗口，盖在浏览器上，与程序主题无关，必须在任何背景上都清楚可见，因此使用固定配色：

- 只能用 `QColor(r, g, b, a)`，写在 `paintEvent` 或控件调色板里；
- 仍然不得写 hex 颜色，不得调用 `setStyleSheet`；
- 代码位置：`ui/pages/edc/overlay.py`。

## 3. 语义色

- 成功、警告、错误这类状态，优先用 `InfoBar.success / warning / error` 表达，不给文字上色。目前所有页面都是这样做的，没有定义任何自定义颜色。
- 以后确实需要给文字上语义色时：
  - 用 `setTextColor(亮色, 暗色)` 成对写，分别给浅色主题和深色主题；
  - 颜色常量集中定义在 `src/dataforge/ui/theme.py`，页面只引用常量名，不在页面里写颜色值。
- 主题强调色用 QFluentWidgets 自带的 `themeColor()`，不要自己写。

## 4. 布局

### 4.1 外壳

- `FluentWindow`。侧边栏依次是"主页"、文件处理 / 业务 / 小工具三组工具，底部是"设置"。工具顺序和名称全部来自 `ui/registry.py` 的 `TOOLS`。
- 页面延迟加载：第一次进入某个工具时才创建页面。页面不提供"返回主页"按钮，侧边栏已经承担这个作用。
- 窗口最小宽度 640 px；宽度小于 1100 px 时侧边栏自动收成图标。

### 4.2 三档宽度

断点定义在 `ui/layout.py`，页面不要另写数值：

| 档位 | 窗口宽度 | 工具页的排法 |
| --- | --- | --- |
| 宽 | ≥ 1100 px | 左侧"输入 + 参数"卡片，右侧结果区（约 55 : 45），底部操作条 |
| 中 | 750–1100 px | 上下排列：输入 → 参数 → 结果，底部操作条 |
| 窄 | < 750 px | 单列；参数表单改为标签在上、输入在下；结果区折叠成一行摘要（"N 个输出 · M 个问题"），点击展开 |

`ToolPage` 在窗口尺寸变化时自动切换档位，页面不需要处理 `resizeEvent`。

### 4.3 参数表单：ResponsiveForm

- 所有参数用 `ResponsiveForm.add_row(标签, 控件, 提示)` 添加，不要自己写 `QGridLayout` 或 `QFormLayout`。
- 宽、中两档是"标签 | 输入"两列，提示文字在输入下方；窄档改为单列。
- 某个参数只在特定条件下有效时，用 `set_row_visible(控件, 是否显示)` 整行显示或隐藏。

### 4.4 结果区：三个标签页

结果区固定为三个标签页，由 `ResultPanel` 提供：

| 标签页 | 内容 |
| --- | --- |
| 结果 (N) | 生成的文件路径，以及统计数字 |
| 警告 (N) | 警告、出错的文件，以及需要选择编码的文件 |
| 日志 | 运行期间的日志，实时追加 |

### 4.5 滚动区

- 用 `SmoothScrollArea`。
- `setWidget()` 会打开内容控件的 `autoFillBackground`，放进滚动区后要对内容控件调用 `setAutoFillBackground(False)`，否则深色主题下会露出浅色底。
- 滚动区本身的背景有两种做法：
  - 工具页（`ToolPage`）再对 `viewport()` 调用 `setAutoFillBackground(False)`；
  - 主页（`ui/home.py`）调用 QFluentWidgets 自带的 `enableTransparentBackground()`，必须在 `setWidget()` 之前调用，否则卡片也会变透明。

## 5. 交互

- **结果提示一律用 InfoBar**，显示在窗口右上角（`InfoBarPosition.TOP_RIGHT`），父对象用页面所在的窗口。完成、部分失败、未生成文件、失败、已取消都用 InfoBar，不弹模态框。例外：日期转换页的"已复制"提示显示在页面顶部（`InfoBarPosition.TOP`，父对象是页面本身）。
- **模态对话框只用于需要用户做决定的场景**：
  - 勾选"覆盖原文件"后开始运行前的二次确认；
  - 编码有歧义时选择编码；
  - EDC 某一行停下后选择"重做本行 / 跳到下一行 / 结束"；
  - EDC 点"选择窗口…"后从列表中选择目标窗口；
  - 任务运行中关闭窗口时的确认。
- 对话框用 Fluent 的 `MessageBox` / `MessageBoxBase`。`MessageBox` 先经过 `components/confirm.py` 的 `use_chinese_buttons()` 把按钮改为"确定 / 取消"。用完在 `exec()` 返回后调用 `deleteLater()`。
- **运行时锁定输入**：任务开始时 `ToolPage` 调用页面的 `set_inputs_locked(True)`，输入区和参数区不可编辑；结束后解锁。切换侧边栏不受限制，任务在后台继续。
- 全局同一时间只运行一个任务。其他工具在运行时，本页主按钮不可用，按钮旁边显示"<工具名> 正在运行"。
- 主按钮写具体动作，例如"开始转换"、"开始拆分"，用 `run_bar.set_primary_text()`（或 `run_bar.primary_button().setText()`）设置。
- 输入不全时（例如没选文件），用 `InfoBar.warning` 说明缺什么，不开始运行。
- 文件输入用 `FileInputCard`（支持拖放、选择文件、选择文件夹、清空），文件夹输入用 `FolderPicker`，输出位置用 `OutputLocationField`，编码选择用 `EncodingField`。

## 6. 后台任务与线程

- 所有耗时工作通过全局唯一的 `JobRunner` 提交，不得自己创建线程或 `QThread`，也禁止用 `processEvents` 代替后台任务。
- 任务函数里不得创建 QObject、不得操作控件、不得调用 `gc.collect()`，只能通过返回值和进度回调把结果带回主线程。
- 每个 QObject 都要有父对象，或者显式 `deleteLater()`。
- 系统钩子线程（EDC 的鼠标、键盘监听，跟随系统主题的监听）里的回调只发信号，不直接改界面。

详细机制见 [开发文档的"后台任务"](开发文档.md#5-后台任务)。

## 7. 新页面检查清单

提交新页面或修改页面前逐项检查：

- [ ] 在 `ui/registry.py` 的 `TOOLS` 中登记，名称、简介只写在这里。
- [ ] 文件类工具继承 `ToolPage`，输入、参数用 `add_section()` 放进卡片，参数用 `ResponsiveForm`。
- [ ] 窗口拉到 640、900、1300 px 宽时排版都正常，没有横向滚动条，没有被截断的控件。
- [ ] 浅色、深色两种主题下都看一遍，没有浅色底块、看不清的文字。
- [ ] `grep` 检查本页没有禁用清单中的写法：`setStyleSheet`、`#` 开头的颜色值、`setFixedWidth`、`processEvents`（此项禁止）、`DontUseNativeDialog`、`unhook_all`。
- [ ] 没有原生 Qt 控件（EDC 浮层除外）。
- [ ] 结果和错误都用 InfoBar 提示；模态对话框只用于需要确认的场景，用完 `deleteLater()`。
- [ ] 运行时输入区、参数区被锁定，结束后解锁。
- [ ] 耗时工作都在 `build_job()` 返回的任务函数里，任务函数不碰控件。
- [ ] `capture_state()` / `restore_state()` 能恢复"最近使用"中的输入和参数；输入文件已不存在时只恢复参数。
- [ ] `test_shell_smoke.py` 和本页的页面测试通过。
