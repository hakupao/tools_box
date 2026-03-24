# DataForge Studio UI 界面规范（Qt / QFluentWidgets）

本文档基于当前仓库已实现页面总结，可作为后续新增页面的直接参考模板。  
覆盖范围：`src/gui/main_window.py`、`src/gui/qt_common.py`、`src/gui/widgets/*_page.py`。
适用版本：`v2.0.1`（2026-03-24）。

## 1. 全局基线

### 1.1 主题与字体
- 全局固定浅色主题：`setTheme(Theme.LIGHT)`（`src/main.py`）
- 全局禁用原生文件对话框：`QApplication.setAttribute(Qt.AA_DontUseNativeDialogs, True)`（`src/main.py`）
- 全局字体：`app.setFont(QFont(font_family, 10))`（`src/main.py`）
- 优先字体顺序：`Segoe UI Variable Text` -> `Segoe UI Variable Display` -> `Segoe UI` -> `Microsoft YaHei UI`
- 等宽字体（日志/大文本）：统一用 `mono_font()`（`src/gui/qt_common.py`）

### 1.2 颜色基线（现有项目事实标准）
- 页面背景：`#F5F6F8`（主页、数据模糊化、EDC 配置弹窗）
- 主卡片背景：`#FFFFFF`
- 次级卡片 / 输入区域浅底：`#F8FAFC`、`#FBFCFE`
- 主边框：`#E3E8EF`
- 次边框：`#E8EDF4`、`#DCE3ED`
- 主文本：`#0F172A` / `#1F2937` / `#334155`
- 次文本：`#6B7280` / `#7A8190` / `#64748B`
- 说明蓝（字段提示）：`#2563EB`（`dmFieldHint`）
- 强调蓝（选中）：`#DDEBFF`
- 强调青（提示）：`#0E7490`
- 风险红：`#DC2626`

### 1.3 通用列表控件（文件列表）
- 使用 `FileListWidget`（`src/gui/qt_common.py`）
- 样式：
  - 背景 `#F8FAFC`
  - 边框 `1px solid #E3E8EF`
  - 圆角 `10px`
  - 选中背景 `#DDEBFF`
- 支持拖拽文件/文件夹，支持按后缀过滤（`allowed_exts`）

### 1.4 滚动条样式规范（已落地）
- 适用页面：
  - 主界面：`src/gui/main_window.py` 中 `QWidget#home QScrollBar*`
  - 数据模糊化：`src/gui/widgets/data_masking_page.py` 中 `QWidget#data_masking QScrollBar*`
  - 仕样书工作流：`src/gui/widgets/spec_workflow_page.py` 中 `QWidget#spec_workflow QScrollBar*`
- 视觉规则（两页面共用）：
  - 轨道背景：`transparent`
  - 滚动条厚度：纵向 `10px`、横向 `10px`
  - 滑块圆角：`5px`
  - 滑块颜色：默认 `#C7D3E3`、悬停 `#A9BCD6`、按下 `#92ABC9`
  - 隐藏箭头按钮：`add-line/sub-line` 尺寸设为 `0`
  - 分页区：`add-page/sub-page` 使用 `transparent`
- 页面差异（保持现状）：
  - 主界面滑块最小尺寸：`56`；纵向边距 `8 4 8 0`，横向边距 `0 8 4 8`
  - 数据模糊化滑块最小尺寸：`52`；纵向边距 `6 3 6 0`，横向边距 `0 6 3 6`
  - 仕样书工作流滑块最小尺寸：`52`；纵向边距 `6 3 6 0`，横向边距 `0 6 3 6`
- 实现原则：滚动条 QSS 必须使用页面对象名作用域（如 `QWidget#home` / `QWidget#data_masking` / `QWidget#spec_workflow`），避免全局污染其它工具页

### 1.5 弹窗与文件对话框规范（本轮修正重点）
- 统一入口：
  - 普通提示弹窗只允许使用 `show_info/show_warning/show_error/ask_yes_no`（`src/gui/qt_common.py`）
  - 文件选择弹窗只允许使用 `select_open_file/select_open_files/select_existing_directory/select_save_file`（`src/gui/qt_common.py`）
- 禁止项：
  - 页面代码中直接调用 `QMessageBox.*`
  - 页面代码中直接调用 `QFileDialog.getOpenFileName/getOpenFileNames/getExistingDirectory/getSaveFileName`
- 弹窗统一浅色策略：
  - 所有弹窗创建后必须执行 `_apply_light_dialog_style(...)`
  - 同时调用 `ensure_light_title_bar(...)` 强制 Windows 标题栏浅色
  - 全局安装 `LightTitleBarEventFilter` 作为兜底（`QEvent.Show/WinIdChange`）
- 文件对话框样式最低要求：
  - 项目树/列表/表格必须有可见选中态：选中背景 `#DDEBFF`、文字 `#0F172A`
  - 分割条（`QSplitter::handle`）必须是浅色，避免深色竖条
  - 滚动条分页区（`add-page/sub-page`）必须透明，避免深色块
  - 角落区（`QTableCornerButton::section`）必须与表头同色
- 图标可用性规则：
  - `QFileDialog` 顶部导航按钮（后退/前进/上一级/新建/视图切换）必须显示图标
  - 不要为弹窗强制切换全局样式引擎（如强制 `Fusion`），否则可能导致工具按钮图标丢失
  - 若需美化工具按钮，仅对 `QFileDialog QToolButton` 做局部 QSS，不覆盖图标来源

## 2. 页面布局规则（通用型页面）

以下模式适用于绝大多数工具页（如 `file_format`、`spec_workflow`、`xlsx_sheet_splitter`、`file_field_extractor` 等）：

### 2.1 根布局
- `QVBoxLayout(self)`
- 推荐边距：`(32, 28, 32, 28)`  
  - 现有特例：`data_masking` 用 `(32, 24, 32, 24)`，`edc_site_adder` 用 `(32, 20, 32, 24)`
- 推荐间距：`16`  
  - 现有特例：`data_masking` 用 `14`，`edc_site_adder` 用 `12`
- 首屏留白控制：
  - Header 区不应挤占中上部大量空白
  - 推荐结构：`header stretch=0`，主内容区 `stretch=1`

### 2.2 Header 区（页面头）
- 结构：`QHBoxLayout`
  - 左：`QVBoxLayout(title + subtitle + stretch)`
  - 右：返回按钮（通常 `PushButton("返回主页")`）
- 标题：
  - 主标题：`TitleLabel`
  - 副标题：`BodyLabel` 或 `CaptionLabel`
  - 副标题颜色：`#6B7280`
- 对齐：返回按钮 `Qt.AlignRight | Qt.AlignTop`

### 2.3 操作区顺序（标准处理页）
1. 操作按钮行（选文件 / 选文件夹 / 清空）
2. 文件列表（`FileListWidget`，`stretch=1`）
3. 输出路径行（左标题 + 中说明 + 右按钮）
4. 进度条 + 进度文案
5. 主动作按钮（`PrimaryPushButton`，左对齐）
6. 状态文案（`CaptionLabel`）

### 2.4 对齐规则
- 行内控件默认左对齐；尾部留白统一 `addStretch(1)`
- 主动作按钮靠左，不居中
- 次要按钮集中在对应行，不分散到多行

## 3. 控件语义与按钮规则

### 3.1 按钮层级
- `PrimaryPushButton`：单步流程的关键动作（开始处理/转换/扫描/保存）
- `PushButton`：导航、选择文件、清空、取消、导出等次级动作
- 异常：`file_field_extractor_page.py` 中部分次级动作用了 `PrimaryPushButton`，建议后续新页不要沿用该例外

### 3.2 文本控件
- 日志/预览：`TextEdit` 或 `QPlainTextEdit` + `setReadOnly(True)`
- 说明/提示：`CaptionLabel`，颜色统一次文本
- 大段文本建议使用等宽字体增强可读性

### 3.3 进度反馈
- 统一组合：`ProgressBar + CaptionLabel`
- 每次处理循环中调用 `QApplication.processEvents()` 保持 UI 响应

## 4. 交互状态规则

### 4.1 处理过程按钮状态
- 开始执行前：禁用主动作按钮（必要时连同扫描按钮一起禁用）
- 结束（成功/失败）后：恢复按钮可用

### 4.2 校验顺序
- 先校验输入（文件、参数）
- 再校验依赖条件（如规则文件、扫描结果）
- 失败用 `show_warning/show_error`，成功用 `show_info`

### 4.3 拖拽规则
- 支持拖拽的页面必须实现：
  - `setAcceptDrops(True)`
  - `dragEnterEvent`
  - `dropEvent`
- 复杂页面（如 `data_masking`）需要按当前模式限制拖拽生效区域

## 5. DataMasking 页面专项规范

文件：`src/gui/widgets/data_masking_page.py`  
该页面是项目内“复杂多模块页”的标准参考。

### 5.1 页面结构分层
- 顶层：Header + Mode Row + ScrollArea
- 中层：`QStackedWidget(dmPatternStack)` 切换 Pattern1/Pattern2
- Pattern1：5 个步骤卡片串联（输入 -> 扫描 -> 配置 -> 执行 -> 预览）
- Pattern2：占位说明卡片（只读）

### 5.2 样式命名与对象命名规则
- 页面级样式挂在根组件：`QWidget#data_masking`
- 滚动条样式同样使用页面作用域：`QWidget#data_masking QScrollBar*`
- 卡片命名：
  - 主卡片：`dmCard`
  - 子卡片：`dmSubCard`
- 文本语义命名：
  - `dmSectionTitle`（区块标题）
  - `dmFormLabel` / `dmSubFormLabel`（表单标签）
  - `dmMuted`（弱文本）
  - `dmFieldHint`（字段提示，蓝色）
  - `dmAlertNote` / `dmRequired`（警示文本）
  - `dmSubtle` / `dmAccent`（强调提示）

### 5.3 尺寸与表单对齐硬规则
- `FORM_LABEL_WIDTH = 120`
- `FORM_FIELD_WIDTH = 180`
- 表单控件最小高度：`34`
- `QFormLayout`：
  - Label 左对齐
  - Form 左上对齐
  - 水平间距 `10`
  - 垂直间距 `8`
- 标签固定宽度（min=max=120），保证多卡片横向齐线
- 输入域统一固定宽度（默认 `180`），备注文本在其右侧
- DM 双字段并排行（人名/施设）额外规则：
  - `DM_PAIR_LEFT_LABEL_WIDTH = FORM_LABEL_WIDTH + 2`（首个输入框起始位与普通行对齐）
  - `DM_PAIR_RIGHT_LABEL_OFFSET = 40`（`人名替换值/施设替换值` 标签整体右移）
  - `DM_PAIR_FIELD_WIDTH = FORM_FIELD_WIDTH`（两侧 textbox 与“年龄字段”等宽）
  - 尾部 `启用替换` 复选框使用 `addStretch(1)` 后右对齐

### 5.4 可复用构建方法（新增复杂页建议复用同思路）
- `_create_card(title, subtitle)`：统一主卡片外观与标题层
- `_style_form_layout(form)`：统一表单间距与对齐
- `_form_label(text, submodule=False)`：统一标签宽度/字体/缩进
- `_input_with_note(widget, note, required=False, ...)`：输入+提示+必填标识
- `_paired_dm_fields(...)`：DM 专属双字段并排行（字段 + 替换值 + 启用开关）
- `_checkbox_field(checkbox, note=None)`：复选框与输入行对齐

### 5.5 步骤化流程状态机规则
- 文件或扫描参数改动后必须 `_invalidate_scan()`：
  - 清空扫描结果
  - 禁用执行按钮
  - 更新状态提示
- 执行前必须校验：
  1. 文件存在
  2. 已扫描且无错误
  3. 当前配置签名与扫描时一致（防止“扫后改参直接跑”）
- `process_btn` 默认禁用，仅在扫描通过后可用

### 5.6 防误操作细节（复杂表单推荐）
- `NoWheelSpinBox/NoWheelDoubleSpinBox/NoWheelComboBox`：禁用滚轮改值
- 高风险字段用红色提示（`dmAlertNote` + `dmRequired`）
- 高级参数默认折叠（“显示扫描参数”）
- DM 专属设置中：
  - `人名字段 + 人名替换值` 与 `施设字段 + 施设替换值` 同行展示
  - 每行尾部有 `启用替换` 复选框（默认勾选）
  - 取消勾选后即使 DM 对应字段非空也不替换，输出原值

## 6. EDC 页面专项规范（当前实现）

文件：`src/gui/widgets/edc_site_adder_page.py`

- 页面布局：
  - 顶部更紧凑边距 `(32, 20, 32, 24)`
  - 主内容左右比例 `3:1`（即 75% : 25%，使用说明 : 处理日志）
  - 降低顶部留白，优先保证“使用说明”主体尽早进入可视区域
- 配置弹窗：
  - 使用浅色风格（`QDialog#edcConfigDialog`）
  - 表格、表头、选中态、行号区统一浅色
  - 表格支持交替行底色

## 7. 新增页面落地清单（直接照做）

1. 新建 `src/gui/widgets/<tool>_page.py`，类名 `<Tool>Page(QWidget)`  
2. `setObjectName("<tool_id>")`，与主窗口注册 ID 保持一致  
3. 用“通用型页面布局”搭建：Header -> Action Row -> FileList -> Output Row -> Progress -> Primary Action -> Status  
4. 副标题和状态说明使用 `#6B7280/#7A8190` 这组弱文本色  
5. 文件列表优先使用 `FileListWidget`（不要重复造样式）  
6. 主动作只保留一个 `PrimaryPushButton`  
7. 处理期间禁用主动作按钮，结束后恢复  
8. 需要拖拽时实现 `setAcceptDrops + dragEnterEvent + dropEvent`  
9. 注册到 `src/gui/main_window.py` 的 `TOOL_PAGE_REGISTRY`  
10. 如页面复杂度接近 `data_masking`，按“卡片 + 子卡片 + 固定表单宽度 + 步骤状态机”实现
11. 页面存在滚动区域时，按“1.4 滚动条样式规范”添加作用域化滚动条 QSS
12. 涉及弹窗/文件选择时，严格按“1.5 弹窗与文件对话框规范”走 `qt_common` 封装

## 8. 回归检查清单（弹窗/对话框）

每次修改弹窗或文件对话框样式后，至少手工验证以下场景：
1. 数据模糊化页点击“保存配置”，弹窗标题栏浅色、文字对齐正常、无卡死
2. 数据模糊化页点击“选择文件/选择文件夹/选择输出路径”，文件对话框为浅色
3. 文件对话框中选中一行时，高亮明显（`#DDEBFF`）且文字可读
4. 文件对话框顶部导航按钮图标可见，不出现“只有按钮轮廓无图标”
5. 文件对话框滚动条、分割条、角落区无深色块
6. Windows 深色系统主题下运行时，以上表现保持一致

## 9. 推荐模板（简版骨架）

```python
class NewToolPage(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self.setObjectName("new_tool")
        self.main_window = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(TitleLabel("新工具"))
        subtitle = BodyLabel("一句话描述")
        subtitle.setTextColor("#6B7280", "#6B7280")
        left.addWidget(subtitle)
        left.addStretch(1)
        back_btn = PushButton("返回主页")
        back_btn.clicked.connect(lambda: self.main_window.switch_to(self.main_window.home_interface))
        header.addLayout(left, stretch=1)
        header.addWidget(back_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addLayout(header)

        # 其余区域按“操作行 -> 文件列表 -> 输出 -> 进度 -> 主动作 -> 状态”扩展
```

---

如后续要做统一视觉重构，建议先把本规范里的颜色和尺寸提取到单独 `theme.py`（Qt 版本）再让页面按 token 引用，避免散落硬编码。
