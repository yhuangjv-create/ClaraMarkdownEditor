# ClaraMarkdownEditor

**仿 Word Ribbon 界面的轻量级 Markdown 编辑器，支持所见即所得编辑、左右同步预览，以及 Markdown ⇄ Word ⇄ PDF 三向互转。**

[English README（主版本）](README.md)

版本：**1.0.1** · 平台：Windows 10/11（macOS/Linux 在 PySide6 下基本可用）

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
| 分屏同步模式 | 左源码 + 右实时预览，滚动位置按比例联动 |
| 所见即所得模式 | 仿 Word 富文本，隐藏 Markdown 语法；加粗/斜体/删除线/行内代码、标题、列表、引用、代码块、表格可完整往返 |
| Ribbon 工具栏 | 文件 / 开始 / 插入 / 视图 / 转换 五个选项卡，可折叠，字母图标为 Fluent 风格 |
| 快捷键 | `Ctrl+N/O/S`、`Ctrl+Shift+S`、`Ctrl+B`、`Ctrl+I`、`Ctrl+K`、`Ctrl+F`、`Ctrl+Shift+M`（源码）、`Ctrl+Shift+P`（分屏）、`Ctrl+Shift+W`（所见即所得）、`Esc` 关闭查找栏 |
| 自动保存 | 有未保存修改时按间隔（默认 60 秒）写入 `.autosave/draft.md`，下次启动询问是否恢复 |
| 大纲 | 左侧标题树，点击跳转到对应行 |
| 主题与语言 | 右上角可切换浅色/深色、中文/English，设置由 QSettings 持久化 |
| 拖拽打开 | 把 `.md` / `.docx` / `.pdf` 拖入窗口即可打开或导入 |

**注意事项**

- 所见即所得模式下嵌套列表层级可能被压平；在该模式下插入的表格会以字面 Markdown 文本存在，切回源码模式编辑即可。
- 分屏预览使用 Qt 的 HTML/CSS 子集，极特殊的 Markdown 扩展显示效果会比 GitHub 简化。
- 导出的是文字型 PDF，字体取决于系统已安装字体。

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

新建、打开、保存、另存为、最近文件（最多 10 个）、导出 Word/PDF、导入 Word/PDF、拖拽打开。

---

## 3. 目录树索引

```
ClaraMarkdownEditor/
├── app.py                     # 程序入口
├── run.bat                    # Windows 启动脚本（pythonw 无控制台）
├── requirements.txt           # Python 依赖
├── .gitignore                 # Git 忽略规则
├── README.md                  # 英文版 README（主版本）
├── README.zh-CN.md            # 中文版 README（本文件）
├── clara/                     # 应用包
│   ├── __init__.py            # 应用名、组织名、版本号
│   ├── backup.py              # 版本备份工具 + 命令行入口
│   ├── converter.py           # 转换门面与参数数据类
│   ├── convert_page.py        # 转换中心界面 + 差异色带
│   ├── docx_io.py             # Markdown ⇄ DOCX（python-docx）
│   ├── editor.py              # 源码编辑器、查找栏、分屏/所见即所得编辑器
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

- 分屏预览：`MarkdownEditor._on_source_changed` → 160ms 防抖 → `render.md_to_html` → `QTextBrowser.setHtml`。
- 模式切换：`set_mode` → `mark_quote_blocks` + `md_to_html` 生成富文本；切回源码时调用 `document_to_markdown`。
- 转换流程：`ConvertPage.refresh` 调用 `converter.source_preview` / `target_preview`；`run_conversion` 调用 `converter.convert`，再分发到 `docx_io` / `pdf_io`。

---

## 5. 所有文件代码解释

### `app.py`
先创建 `QApplication`（部分 Qt 组件依赖），设置 HiDPI 取整策略、应用名与版本，再延迟导入 `MainWindow`，避免过早导入 Qt 控件。`main()` 返回事件循环退出码。

### `clara/__init__.py`
导出三个全局常量：`APP_NAME`、`ORG_NAME`（QSettings 命名空间）、`__version__ = "1.0.0"`。

### `clara/settings.py`
`Settings` 封装 `QSettings(ORG_NAME, APP_NAME)`。属性包括 `language`、`dark_mode`、`editor_mode`、`outline_visible`、`autosave_enabled`、`autosave_interval`，以及 `recent_files()`、`add_recent_file(limit=10)`、`last_dir`。布尔值以 `"true"/"false"` 字符串存储，兼容注册表。

### `clara/i18n.py`
`STRINGS` 将每个键映射为 `(中文, English)`。`I18n` 保存当前语言，提供 `t(key, **fmt)`（带安全 `str.format`）、`toggle()`、`set_language()`。各界面组件实现 `retranslate()`，切换语言无需重启。

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
- `MarkdownEditor`：用 `QSplitter` 组合源码编辑器与 `QTextBrowser`；三种模式（`source`、`split`、`wysiwyg`）、160ms 预览防抖、双向按比例滚动联动；信号 `contentChanged` / `documentLoaded` / `cursorMoved` / `modeChanged`；格式化命令（加粗、斜体、删除线、行内代码、标题、列表、引用）与插入命令（链接、图片、表格、分隔线、代码块）。

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
