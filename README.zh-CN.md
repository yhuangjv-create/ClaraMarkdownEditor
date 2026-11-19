# ClaraMarkdownEditor

**仿 Word Ribbon 界面的轻量级 Markdown 编辑器，支持所见即所得编辑、左右同步预览，以及 Markdown ⇄ Word ⇄ PDF 三向互转。**

[English README（主版本）](README.md)

版本：**1.5.6** · 平台：Windows 10/11（macOS/Linux 在 PySide6 下基本可用） · 许可证：[MIT](LICENSE)

最新：功能区「设置」选项卡移到「转换」之后。[完整更新记录 ↓](#8-版本更新记录)

---

## 1. 快速开始

```bat
pip install -r requirements.txt
python app.py
```

或直接双击 `run.bat`（用 `pythonw` 启动，不弹控制台）。

环境要求：Python 3.10+（已在 3.15 上验证），PySide6 6.6+。

---

## 2. 功能介绍与注意事项

### 2.1 编辑区

| 功能 | 说明 |
|---|---|
| 代码编辑模式 | Markdown 源码编辑，行号、当前行高亮、等宽字体，Tab 缩进 4 空格 |
| 分屏同步模式 | 左源码 + 右侧**可直接编辑**的渲染视图，修改会回写 Markdown，滚动按比例联动，`Ctrl`+单击打开链接。「开始」选项卡的格式按钮作用于最后聚焦的一侧 |
| 所见即所得模式 | 仿 Word 富文本，隐藏 Markdown 语法；加粗/斜体/删除线/行内代码、标题、列表、引用、代码块、表格可完整往返 |
| Ribbon 工具栏 | 文件 / 开始 / 插入 / 视图 / 转换 五个选项卡，可折叠，字母图标为 Fluent 风格 |
| 文档标签页 | 每个打开的文件在编辑区上方显示一个标签，点击切换、拖动排序、`×` 关闭；有未保存修改时显示 `*` |
| 快捷键 | `Ctrl+N/O/S`、`Ctrl+Shift+S`、`Ctrl+B`、`Ctrl+I`、`Ctrl+K`、`Ctrl+F`、`Ctrl+Shift+M`（源码）、`Ctrl+Shift+P`（分屏）、`Ctrl+Shift+W`（所见即所得）、`Esc` 关闭查找栏 |
| 自动保存 | 有未保存修改时按间隔（默认 120 秒，即 2 分钟，可在「设置」中自定义）写入 `.autosave/draft.md`，下次启动询问是否恢复 |
| 大纲 | 左侧标题树，点击跳转到对应行 |
| 主题与语言 | 右上角可切换浅色/深色、中文/English，设置由 QSettings 持久化 |
| 拖拽打开 | 把 `.md` / `.docx` / `.pdf` 拖入窗口即可打开或导入 |

**注意事项**

- 所见即所得模式下嵌套列表层级可能被压平；在该模式下插入的表格会以字面 Markdown 文本存在，切回源码模式编辑即可。
- 分屏预览使用 Qt 的 HTML/CSS 子集，极特殊的 Markdown 扩展显示效果会比 GitHub 简化。右侧直接输入时，内容会经过与所见即所得相同的「富文本 → Markdown」转换。
- 导出的是文字型 PDF，字体取决于系统已安装字体。
- 切换文档标签会重新载入文档内容，因此该标签的撤销历史会重置。

### 2.2 格式转换中心

| 方向 | 引擎 | 说明 |
|---|---|---|
| Markdown → Word | `python-docx` | 标题、行内样式、列表、引用、代码块（底纹）、表格（Table Grid）、真实超链接、本地图片 |
| Markdown → PDF | `QTextDocument` + `QPdfWriter` | 纸张 A4/A5/B5/Letter、毫米页边距、字体与字号可配置 |
| Word → Markdown | `python-docx` | 处理 run、超链接、表格和内嵌图片（保存到 `assets/`） |
| PDF → Markdown | `pypdf` | 仅文字提取，**不含 OCR**，扫描件几乎无法提取；分页以 `<!-- 第 N 页 -->` 标记 |

转换页还提供：

- **左源预览 / 右目标预览**，中间分割条可拖动调整比例；
- **差异色带**（基于 `difflib`），标记相同 / 新增 / 删除 / 修改内容；
- 纸张、页边距、字体、字号、深色预览开关；
- “使用当前文档”或选择外部源文件。

### 2.3 文件管理

新建、打开、保存、另存为、最近文件（1–50 条，可设置）、导出 Word/PDF、导入 Word/PDF、拖拽打开；导出 Word/PDF（以及转换中心执行转换）时若目标文件已存在，会弹窗提供「覆盖」「另存为」「取消」三种选择，选择「另存为」会打开保存对话框并预填 `文件名 (1).docx` 这类编号名，可确认、改名或取消，不再静默覆盖；主界面的「另存为」也采用同一套逻辑。多个文档以标签页同时保持打开，关闭未保存的标签会询问是否保存。最近文件下拉列表中，在条目上点右键选「移除该记录」即可删除该条；列表底部有「清空所有记录」，可一次清除全部记录；「设置」中可自定义显示条数（1–50），还可只显示最近 N 天内打开的文件（0 表示不限，天数没有上限），修改后立即生效；勾选「不显示最近文件」可隐藏整个列表，状态会被记住。

---

## 3. 目录树索引

```
ClaraMarkdownEditor/
├── app.py                     # 程序入口
├── run.bat                    # Windows 启动脚本（pythonw 无控制台）
├── requirements.txt           # Python 依赖
├── .gitignore                 # Git 忽略规则
├── .gitattributes             # 换行符规则（LF，.bat 用 CRLF）
├── README.md                  # 英文版 README（主版本）
├── README.zh-CN.md            # 中文版 README（本文件）
├── LICENSE                    # MIT 许可证
├── clara/                     # 应用包
│   ├── __init__.py            # 应用名、组织名、版本号
│   ├── backup.py              # 版本备份工具 + 命令行入口
│   ├── converter.py           # 转换门面与参数数据类
│   ├── convert_page.py        # 转换中心界面 + 差异色带
│   ├── docx_io.py             # Markdown ⇄ DOCX（python-docx）
│   ├── editor.py              # 源码编辑器、查找栏、分屏/所见即所得编辑器
│   ├── fileutils.py           # 导出冲突处理（覆盖 / 自动编号 / 取消）
│   ├── i18n.py                # 中英文字符串表与 I18n 辅助类
│   ├── icons.py               # 自绘字母图标
│   ├── main_window.py         # 主窗口、动作分发、自动保存、文件读写
│   ├── outline.py             # 标题大纲面板
│   ├── pdf_io.py              # Markdown → PDF、PDF → Markdown（pypdf）
│   ├── qt_document.py         # QTextDocument → Markdown 序列化
│   ├── render.py              # Markdown → HTML、HTML → Markdown、块解析
│   ├── ribbon.py              # Ribbon 选项卡/分组/按钮布局
│   ├── settings.py            # QSettings 偏好设置
│   └── theme.py               # 浅色/深色 QSS 样式表
├── .autosave/                 # （运行时）崩溃恢复草稿
└── _backups/                  # （运行时）完整版本备份
```

标注“运行时”的两个目录会自动创建，且不进入 git 与版本备份。

---

## 4. 文件互相调用逻辑

```
app.py
 └─ QApplication → clara.main_window.MainWindow
      ├─ clara.settings.Settings        （语言、主题、模式、自动保存、最近文件）
      ├─ clara.i18n.I18n                （全部界面文案）
      ├─ clara.theme.build_stylesheet   （全局 QSS）
      ├─ clara.ribbon.RibbonBar
      │    └─ clara.icons.text_icon
      ├─ clara.outline.OutlinePanel → clara.render.iter_headings
      ├─ clara.editor.MarkdownEditor
      │    ├─ SourceEditor（行号）+ FindBar
      │    ├─ clara.render.md_to_html        （分屏预览）
      │    └─ clara.qt_document.document_to_markdown（所见即所得 → MD）
      ├─ clara.convert_page.ConvertPage
      │    ├─ clara.converter.convert / source_preview / target_preview
      │    ├─ clara.docx_io.export_md_to_docx / import_docx_to_md
      │    ├─ clara.pdf_io.export_md_to_pdf / import_pdf_to_md
      │    └─ DiffStrip（difflib）
      └─ clara.backup.create_backup
```

一句话概括：**main_window 持有文档状态**（`current_file`、`dirty`、编辑器内容），其他模块要么是渲染/转换工具，要么是通过 Qt 信号回报的纯 UI 组件。

- 分屏预览：`MarkdownEditor._on_source_changed` → 160ms 防抖 → `render.md_to_html` → `PreviewEditor.setHtml`；在右侧输入时调用 `document_to_markdown` 静默回写源码。
- 模式切换：`set_mode` → `mark_quote_blocks` + `md_to_html` 生成富文本；切回源码时调用 `document_to_markdown`。
- 转换流程：`ConvertPage.refresh` 调用 `converter.source_preview` / `target_preview`；`run_conversion` 调用 `converter.convert`，再分发到 `docx_io` / `pdf_io`。

---

## 5. 所有文件代码解释

### `app.py`
先创建 `QApplication`（部分 Qt 组件依赖），设置 HiDPI 取整策略、应用名与版本，再延迟导入 `MainWindow`，避免过早导入 Qt 控件。`main()` 返回事件循环退出码。

### `clara/__init__.py`
导出三个全局常量：`APP_NAME`、`ORG_NAME`（QSettings 命名空间）、`__version__`。

### `clara/settings.py`
`Settings` 封装 `QSettings(ORG_NAME, APP_NAME)`。属性包括 `language`、`dark_mode`、`editor_mode`、`outline_visible`、`autosave_enabled`、`autosave_interval`、`last_dir`，以及最近文件相关配置（`recent_files()`、`visible_recent_files()`、`recent_limit` 1–50、`recent_days` 0 表示不限、`recent_hidden`，打开时间以 JSON 保存）和方法 `add_recent_file()`、`remove_recent_file()`、`clear_recent_files()`。布尔值以 `"true"/"false"` 字符串存储，兼容注册表。

### `clara/fileutils.py`
`unique_path(path)` 依次尝试 ` (1)`、` (2)` … 直到文件名可用。`resolve_overwrite(parent, i18n, path)` 在目标不存在时直接返回原路径；已存在时弹出警告框，提供「覆盖 / 另存为 / 取消」。选择「另存为」会打开预填编号路径的保存对话框，返回用户确认后的路径；取消则返回 `None`。Ribbon 导出与转换中心都会在保存对话框之后调用它（对话框使用 `DontConfirmOverwrite`，保证只询问一次）。

### `clara/i18n.py`
`STRINGS` 将每个键映射为 `(中文, English)`。`I18n` 保存当前语言（`lang`），提供 `t(key, **fmt)`（带安全 `str.format`）与 `toggle()`。`install_qt_translator(lang)` 负责加载或移除 Qt 自带的 `qtbase_zh_CN` 翻译，使标准右键菜单、对话框按钮跟随界面语言。各界面组件实现 `retranslate()`，切换语言无需重启。

### `clara/theme.py`
`build_stylesheet(dark)` 返回一整段 QSS，通过 `objectName`（`RibbonTab`、`RibbonButton`、`GroupTitle`、`MiniButton`、`Outline`、`StatusBar` 等）精确控制样式。强调色为 Word 蓝 `#2b579a`，深色主题使用中性炭灰配色。

### `clara/icons.py`
`text_icon(text, size=22, …)` 用 QPainter 绘制圆角方块与居中字母，字号按 1/2/3+ 字符自适应，避免 `PDF`、`W>M` 被裁切。`clear_cache()` 在主题切换时清空内存图标缓存。

### `clara/render.py`
- `md_to_body_html`：用 `markdown` 包（`extra`、`sane_lists`、`toc`、`nl2br`）把 Markdown 转为 HTML 正文；包缺失时使用 `_fallback_markdown`。
- `md_to_html`：拼接浅色/深色 CSS、页面宽度、字体、字号和留白。
- `html_to_md`：`HTMLParser` 构建 `_Node` 树，`_inline`、`_render_list`、`_render_table`、`_render_block` 再序列化回 Markdown。
- `html_to_plain_text`：去标签取纯文本，供 PDF 文本处理使用。
- `parse_blocks`：轻量块解析（标题/段落/代码/引用/列表/表格/分隔线/图片），供 DOCX 导出使用。
- `iter_headings`：产出 `(级别, 标题, 行号)` 给大纲面板。
- `count_words`：中文按字、英文按词计数。

### `clara/qt_document.py`
所见即所得文档的序列化器。自定义块属性 `QUOTE_PROP`、`CODE_PROP` 标记引用与代码块；`mark_quote_blocks` 还会根据背景色反推引用。`document_to_markdown` 按顺序遍历 block，用 `_table_to_md` 处理 `QTextTable`，用 `QTextList` 对象分组列表项（不同列表切换时及时 flush），标题 run 去掉加粗，列表之间不插入空行。

### `clara/docx_io.py`
- `export_md_to_docx`：页面尺寸/页边距、中日韩字体、Heading 1–6、行内 run（`_add_inline_runs` 处理 `**粗**`、`*斜*`、`` `代码` ``、`~~删除~~`、链接）、项目符号/编号列表、带底纹代码块、`Table Grid` 表格与图片。
- `_add_hyperlink`：写入真正的 OOXML 超链接关系。
- `import_docx_to_md`：`_iter_blocks` 按正文顺序遍历，`_runs_to_md` 处理 run 与超链接，`_save_paragraph_images` 把内嵌图片存到 `assets/`，`_table_to_md` 转表格，最后用正则合并相邻列表项，保证 Markdown 列表紧凑。

### `clara/pdf_io.py`
- `export_html_to_pdf`：`QPdfWriter` + `QTextDocument.print_`；用 writer 分辨率把页面绘制矩形换算为设备像素（96 dpi），保证毫米页边距准确。
- `export_md_to_pdf`：Markdown 渲染为打印 CSS（无论界面主题都保持白底）后导出。
- `import_pdf_to_md`：`pypdf` 逐页提取文本，`_merge_lines` 根据中英文标点重新合并硬换行，页间以 `<!-- 第 N 页 -->` 分隔。

### `clara/converter.py`
`ConversionOptions` 数据类（纸张、页边距、字体、字号、深色）。`DIRECTIONS`、`DIRECTION_SOURCE`、`DIRECTION_TARGET` 描述四个转换方向。`convert()` 校验方向、创建输出目录并分发；`source_preview` / `target_preview` 返回左右面板 HTML，Markdown 目标预览关闭页面装饰以避免横向滚动。

### `clara/editor.py`
- `LineNumberArea` + `SourceEditor`：行号栏、当前行高亮、等宽字体、自动缩进、Tab/Backtab 缩进。
- `FindBar`：页内查找，带匹配计数、下一个/上一个、Esc 关闭。
- `PreviewEditor`：分屏右侧使用的可编辑富文本视图；`Ctrl`+单击打开链接，普通输入会回写为 Markdown。
- `MarkdownEditor`：用 `QSplitter` 组合源码编辑器与可编辑的 `PreviewEditor`；三种模式（`source`、`split`、`wysiwyg`）、160ms 预览防抖、分屏下富文本与 Markdown 双向同步、双向按比例滚动联动；信号 `contentChanged` / `documentLoaded` / `cursorMoved` / `modeChanged`；格式化命令（加粗、斜体、删除线、行内代码、标题、列表、引用）与插入命令（链接、图片、表格、分隔线、代码块）。

### `clara/outline.py`
`OutlinePanel` 用 `iter_headings` 列出标题，按级别缩进，点击时发出 `headingActivated(line)`，主窗口据此滚动编辑器。

### `clara/ribbon.py`
`RIBBON_LAYOUT` 是声明式数据：选项卡键 → [(分组键, [(动作键, 图标文字), …]), …]。`RibbonButton` 在语言/主题变化时重绘图标；`RibbonGroup` 负责分组标题。`RibbonBar` 构建选项卡栏、折叠按钮、文档标题与语言/主题按钮，发出 `actionTriggered`、`languageToggled`、`themeToggled`、`collapseToggled`，并在 `set_language` / `set_dark` 时重建（先 hide、再 setParent(None)、最后 deleteLater，避免残影）。

### `clara/convert_page.py`
- `DiffStrip`：依据 `difflib.SequenceMatcher` 的 opcode（相同/插入/删除/替换）绘制比例色带，浅色/深色各一套配色。
- `ConvertPage`：标题、方向下拉、参数行（纸张、页边距、字体、字号、深色预览）、源文件选择 + “使用当前文档”、左右 `QSplitter`（Markdown 目标显示渲染预览，二进制源显示只读文本）、差异图例与执行按钮。`set_context_provider` 让主窗口提供实时文档；`refresh()` 200ms 防抖后重算预览；`run_conversion()` 选择输出路径并就地显示错误。

### `clara/main_window.py`
构建主窗口：`RibbonBar`、`QStackedWidget`（编辑页 / 转换页）、`OutlinePanel`、状态栏。关键部分：
- `_dispatch`：把每个 Ribbon 动作键映射到处理函数。
- 文件操作：`new_document`、`open_dialog`、`open_path`、`save_document`、`save_document_as`、`show_recent`、拖拽事件。
- Word/PDF 导入导出复用 `converter` 与 `docx_io` / `pdf_io`。
- 自动保存：QTimer 在有修改时写入 `.autosave/draft.md` + `draft.json`；`_check_draft` 启动时询问恢复。
- 语言/主题：`_toggle_language`、`_toggle_theme`、`_apply_theme`（QSS + 编辑器 + 转换页 + Ribbon）。
- `backup_version`：输入说明后调用 `create_backup(APP_DIR, __version__, note)`。
- `show_about`、`closeEvent`（保存提示、草稿落盘）与状态更新（模式、字数、光标位置）。

### `clara/backup.py`
`create_backup(root, version, note)` 把整个项目复制到 `_backups/{版本号}_{安全说明}/`，忽略 `__pycache__`、`.git`、`.autosave`、`_backups`、`*.pyc`、`*.tmp`，并写入 `BACKUP_INFO.txt`。命令行用法：

```bat
python -m clara.backup "1.0.0 初始版本"
```

Ribbon 上的“BKP”按钮调用同一函数。

### `run.bat`
`cd /d "%~dp0"` 后执行 `start "" pythonw app.py`，无控制台窗口启动。

---

## 6. 版本、备份与 README 流程

1. 修改 `clara/__init__.py` 中的 `__version__`。
2. 在下方“版本更新记录”追加一条（两个 README 都要写）。
3. 运行 `python -m clara.backup "<改动说明>"`（或点击 **BKP**）。完整副本出现在 `_backups/<版本号>_<改动说明>/`，内含 `BACKUP_INFO.txt`。
4. 备份文件夹名同时包含版本号与改动说明，因此每个版本都保留独立快照。

---

## 7. 已知限制

- 所见即所得模式切回 Markdown 时，嵌套列表层级可能被压平。
- 在所见即所得模式插入的表格/分隔线是字面文本，需切到源码模式编辑。
- PDF → Markdown 仅支持文字型 PDF（无 OCR）。
- 复杂 DOCX 结构（文本框、图表、脚注）不参与转换。
- PySide6 体积较大，打包后的安装包会超过 50MB 目标，尽管源码体积极小。

---

## 8. 版本更新记录

版本号规则：每一位只占一位数字，`1.0.9` 之后是 `1.1.0`，再到 `1.1.1` … `1.1.9`、`1.2.0`。

### 1.5.6 — 「设置」选项卡移到「转换」之后
- 功能区顺序调整为「文件 / 开始 / 插入 / 转换 / 设置」；转换中心的进出与模式切换改为按选项卡键定位，不再依赖固定下标，后续调整顺序也不会错位。

### 1.5.5 — 选择 MD 文件后不再误报无可转换内容
- 「MD → Word」「MD → PDF」下用「选择文件」指定 .md 后可直接转换，不再提示「当前没有可转换的内容」；仅当既未选文件、当前文档也为空时才提示，与「文件 → 导出 Word/PDF」的行为一致。

### 1.5.4 — MD 源文件选择生效
- 「MD → Word」「MD → PDF」方向下用「选择文件」打开 .md 后，左右预览与转换都使用该文件；未选择文件时才使用当前文档，底部状态显示实际使用的文件名。

### 1.5.3 — 反向转换隐藏「使用当前文档」
- 「Word → Markdown」「PDF → Markdown」方向下隐藏「使用当前文档」按钮（这两种方向必须选择 Word / PDF 源文件），切回正向时自动恢复；未选文件时提示文字改为「未选择文件」。

### 1.5.2 — 各转换方向记住源文件
- 「格式转换中心」按源类型（Markdown / Word / PDF）分别记住已选的文件，在四个方向按钮之间来回切换不再丢失选择，切回时自动恢复（文件已不存在则清空）。

### 1.5.1 — 反向转换的参数控件置灰
- 「Word → Markdown」「PDF → Markdown」方向下，「正文字号」与纸张、页边距一起禁用，避免出现调了无效的选项；被禁用的输入框显示为灰色底纹与灰色文字，状态一目了然。

### 1.5.0 — 新增 A3 纸张
- 「格式转换中心」的「纸张」下拉新增 A3（297 × 420 mm），导出 Word 与 PDF 时均按 A3 排版；默认仍为 A4。

### 1.4.9 — 导出后可一键打开
- 导出 Word / PDF 文件、或完成「格式转换中心」的转换后，提示对话框提供「直接打开」与「确定」两个按钮；点「直接打开」会用系统默认程序打开生成的文件。

### 1.4.8 — 转换中心添加关闭按钮
- 「格式转换中心」右上角新增「✕ 关闭」按钮，点击后返回编辑界面，并恢复进入前所在的功能区选项卡；拖入 docx / pdf 进入转换中心时同样可用。

### 1.4.7 — 设置开关按钮的下陷效果
- 「自动保存」与「恢复上次会话」按钮在功能开启时保持下陷外观：柔和的强调色填充、顶部内阴影与内描边，切换时带短暂过渡动画；切换主题或语言后按下状态保持不变。

### 1.4.6 — 行内代码支持二次取消
- 「行内代码」按钮同样支持二次取消：第一次点击把选区（或光标所在词）设为行内代码，第二次点击去掉反引号，同时清除等宽字体与代码配色。

### 1.4.5 — 段落与查找按钮支持二次取消
- 分屏右侧预览与所见即所得模式下，「开始」选项卡「段落」组内的标题（H1–H3）、无序列表、有序列表、引用，以及「编辑」组的查找：第一次点击应用，第二次点击取消。取消标题后字号与字重恢复常规；列表与引用可对选中的多个段落一次性切换。

### 1.4.4 — 大纲按钮移位
- 「大纲」按钮从「设置」移到「文件」选项卡的「显示」分组，位于「源码模式」左侧，功能不变。

### 1.4.3 — 恢复会话开关
- 「设置」新增「恢复上次会话」入口，点击后弹出可勾选项；取消勾选即停止保存与恢复会话并清除已存会话，重新勾选恢复功能。

### 1.4.2 — 恢复上次会话
- 关闭时记住所有打开的标签页（含顺序与当前标签），下次启动自动恢复，并还原未保存的修改与光标位置；已保存的文件以磁盘最新内容为准。关闭时选择「不保存」的内容不会被恢复。

### 1.4.1 — 新建表格内容行留空
- 插入表格时只填写表头（列 1、列 2…），其余单元格在预览与 Markdown 源码中均为空。

### 1.4.0 — 最近文件显示更完整
- 每个条目第一行为加粗文件名，第二行为完整路径与最后修改时间；路径过长时中间省略，鼠标悬停可看完整内容。点击打开与右键移除行为不变。

### 1.3.9 — 大表格不再卡死
- 表格改为一次性 HTML 插入并统一设置样式，不再逐格写入。30 × 30 表格由约 30 秒（程序未响应）降至约 0.1 秒；边框、表头与单元格内边距外观保持一致。

### 1.3.8 — 表格行列取消上限
- 「行数」「列数」数字框不再限制最大值，最小仍为 1，原来的 20 行/列上限已移除。

### 1.3.7 — 表格行列可自定义
- 「表格」按钮改为下拉菜单：可直接设置行数、列数（1–20，默认 3 行 3 列），再点「插入表格」，不再固定为 3×3。

### 1.3.6 — 「插入」选项卡在分屏右侧即时呈现
- 链接插入为真实超链接（蓝色下划线），图片插入后直接显示（超宽自动缩放），表格插入带边框的 3×3 表格，分割线绘制为横线，代码块为带底色的等宽块——右侧窗口不再出现原始 Markdown 标记。
- 这些富文本对象在左侧源码中会还原为标准 Markdown（`[](...)`、`![](...)`、管道表格、`---`、围栏代码块）。

### 1.3.5 — 已有 Markdown 格式的文字可取消样式
- 加粗、斜体、删除线改为检查整个选区（而非只看光标一点）：Markdown 原文中已有 `**文字**`、`*文字*`、`~~文字~~` 的，第一次点击取消样式，第二次恢复。
- 选区中部分有样式时按「无样式」处理，点击一次即对整段应用样式。

### 1.3.4 — 分屏右侧加粗/斜体/删除线可反复切换
- 在右侧窗口点击加粗、斜体、删除线：第一次应用样式，第二次取消样式。
- 修复右侧窗口已获得焦点时（不再产生焦点变化事件）格式目标丢失、命令落到左侧源码的问题。

### 1.3.3 — 斜体与删除线图标
- 「斜体」图标改为倾斜的 *I*，「删除线」图标改为被横线划过的 *S*，与 Office 习惯一致。
- 图标仍由代码绘制（无图片资源），深色/浅色主题均适配。

### 1.3.2 — 修复删除线
- `~~文字~~` 现在会在分屏预览、PDF 预览与 PDF 导出中渲染为真正的删除线，不再显示字面波浪号（新增轻量 Markdown 行内扩展，并保留兜底解析）。
- 修复富文本模式下「开始」选项卡删除线命令的报错（`fontStrikeOut` 取错对象），并支持再次点击取消。
- 源码模式下选中 `~~文字~~` 再点删除线会去掉标记。

### 1.3.1 — 「开始」选项卡可操作右侧预览
- 分屏模式下，若最后聚焦的是右侧窗口，加粗、斜体、删除线、行内代码、标题、列表、引用及插入命令会作用于右侧内容，而不是总改源码。
- 目标跟随焦点：先点击源码或右侧预览，再使用「开始」选项卡的按钮。

### 1.3.0 — 分屏右侧可直接编辑
- 分屏模式右侧的渲染视图不再是只读：可直接点击输入，Markdown 源码会静默同步更新。
- 任一侧编辑都会同步另一侧（源码 → 预览经 160ms 防抖，预览 → 源码立即生效）；滚动比例与主题切换不会丢失内容。
- 链接改为 `Ctrl`+单击打开，普通单击用于放置光标。

### 1.2.9 — 自动保存间隔改为菜单内直接输入
- 「每 N 分钟自动保存」改为在下拉菜单内嵌数字输入框，无需弹窗即可输入或微调。
- 数值改变后立即生效（1–120 分钟，默认 2 分钟）。

### 1.2.8 — 自动保存间隔可自定义
- 「自动保存」下拉新增「每 N 分钟自动保存…」项，默认 2 分钟。
- 点击后可在对话框中将间隔设为 1–120 分钟，保存后立即生效。

### 1.2.7 — 「自动保存」改为可勾选下拉
- 「设置」选项卡中的「自动保存」按钮点击后弹出下拉，内含可勾选的「自动保存」项。
- 勾选或取消勾选会立即启动/停止自动保存定时器，并记住该选择。

### 1.2.6 — 「视图」选项卡改名「设置」
- 第 4 个 Ribbon 选项卡由「视图」改为「设置」，其下「工具」组（大纲、自动保存、关于）保持不变。

### 1.2.5 — 移除「视图」下的主题按钮
- 「视图」选项卡只保留大纲、自动保存、关于；主题切换仍可在右上角完成。

### 1.2.4 — 编辑模式移到「文件」选项卡
- 源码模式、分屏预览、所见即所得三个按钮从「视图」移到「文件」选项卡的「显示」组；「视图」只保留大纲、主题、自动保存与关于。

### 1.2.3 — 移除「退出」按钮
- 「文件」选项卡去掉「退出」按钮及空置的「工具」组，退出程序改为直接关闭窗口。

### 1.2.2 — 「最近文件」移到「打开」右侧
- 「文件」选项卡的「文档」组顺序调整为：新建、打开、最近文件、保存、另存为；原「工具」组只保留「退出」。

### 1.2.1 — 修复「最近文件」按钮残留高亮
- 下拉菜单关闭后主动重置按钮状态（清除按下、焦点并发送 leave 事件），不再一直停留在悬停/按下的高亮外观。

### 1.2.0 — 「另存为」统一冲突处理
- 主界面「另存为」保存 Markdown 时，与导出 Word/PDF 一致：目标已存在则提示「覆盖 / 另存为…（预填编号）/ 取消」，不再静默覆盖。

### 1.1.9 — 冲突提示改为「另存为…」
- 冲突弹窗中间按钮改为「另存为…」：打开保存对话框并预填 `文件名 (1).ext`，用户可确认、改名或取消；「覆盖」「取消」保持不变。

### 1.1.8 — 导出冲突提示
- 导出 Word/PDF（以及转换中心执行转换）时，若目标文件已存在，不再静默覆盖：弹窗提供「覆盖」「自动编号」（`文件名 (1).ext`、`文件名 (2).ext` …）「取消」。

### 1.1.7 — 右键菜单跟随界面语言
- 加载 Qt 自带的 `qtbase_zh_CN` 翻译，编辑器右键菜单（撤消、剪切、复制、粘贴、全选）及标准对话框按钮会跟随界面语言；切换语言后立即生效。

### 1.1.6 — 可隐藏最近文件
- 最近文件下拉菜单新增可勾选项「不显示最近文件」；勾选后列表替换为提示文字，勾选状态会被保存。

### 1.1.5 — 最近文件可按天数筛选
- 最近文件设置对话框新增「仅显示最近多少天内打开的文件」，0 表示不限，天数没有上限；打开文件时会记录时间戳。

### 1.1.4 — 最近文件上限提升
- 最近文件条数上限由 20 提升到 50。

### 1.1.3 — 最近文件可设置显示条数
- 最近文件下拉菜单新增「设置」，可设定显示最近文件的条数（1–50），设置会保存，列表长度立即更新。

### 1.1.2 — 可清空最近文件
- 在最近文件下拉菜单底部新增「清空所有记录」，与文件条目之间用分隔线隔开，可一次清除全部记录。

### 1.1.1 — 最近文件可移除
- 最近文件下拉列表中，在条目上点右键可选择「移除该记录」，把该文件从最近列表中删除。

### 1.1.0 — 文档标签页
- 打开或新建文档时在编辑区上方生成标签，可点击切换、拖动排序、点 `×` 关闭；未保存的文档标签显示 `*`，关闭标签或退出程序时逐个询问是否保存。

### 1.0.9 — 开发备份移入关于对话框
- 从「文件」和「视图」两个 Ribbon 选项卡中移除开发用途的「备份版本」按钮，改为「关于」对话框内的「创建开发备份」按钮；`python -m clara.backup` 命令行仍然可用。

### 1.0.8 — 换行符配置
- 新增 `.gitattributes`（`* text=auto eol=lf`，`.bat` 用 CRLF），Git 统一以 LF 存储文本，首次 `git add` 不再出现“LF will be replaced by CRLF”警告。

### 1.0.7 — 最近文件下拉菜单
- “最近文件”改为在按钮下方展开的下拉菜单，不再弹出模态对话框；菜单显示文件名，悬停提示完整路径，无记录时显示置灰的“暂无最近文件”。

### 1.0.6 — MIT 许可证
- 将自定义版权条款替换为标准 MIT 许可证，允许商业使用、修改与再分发。

### 1.0.5 — 版权文件
- 新增 `LICENSE`，包含中英文版权声明及个人/教育用途的使用条款。

### 1.0.4 — 启动模式
- 启动时固定进入**分屏预览**模式，不再恢复上次使用的编辑模式。

### 1.0.3 — 主题按钮文案
- 修复：切换主题后右上角按钮仍显示“深色主题”的问题；现在始终显示“将切换到的主题”（浅色主题 / 深色主题），视图选项卡中的同名按钮同步更新。
- 切换中英文时，按钮文案也会跟随变化。

### 1.0.2 — 统一深浅主题行距
- 将预览/所见即所得样式拆分为“共用排版规则 + 仅颜色覆盖”两部分，深浅主题的段落、标题、列表、代码块间距完全一致。
- 修复：深色主题下所见即所得内容行距明显大于浅色主题的问题。

### 1.0.1 — 修复拖拽打开
- 修复：把文件拖到编辑器任意区域（源码 / 分屏预览 / 所见即所得）时，现在会直接打开文件，而不是插入一行 `file:///...` 文本。
- 拖拽事件由编辑器组件转发给主窗口处理；Markdown / Word / PDF 的打开逻辑保持不变。

### 1.0.0 — 初始版本
- 仿 Word Ribbon 界面（文件 / 开始 / 插入 / 视图 / 转换），支持折叠。
- 三种编辑模式，行号、当前行高亮、滚动联动的实时预览。
- 自动保存草稿与崩溃恢复。
- 转换中心：MD→DOCX、MD→PDF、DOCX→MD、PDF→MD，左右预览、可拖动分割条与差异高亮。
- 右上角中英文切换；浅色/深色主题。
- 最近文件、拖拽打开、版本备份工具与双语 README。
