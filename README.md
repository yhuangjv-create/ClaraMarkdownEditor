# ClaraMarkdownEditor

**A lightweight Markdown editor with a Word-style Ribbon UI, WYSIWYG editing, synchronized split preview, and Markdown ⇄ Word ⇄ PDF conversion.**

[中文说明 / Chinese README](README.zh-CN.md)

Version: **1.3.8** · Platform: Windows 10/11 (macOS/Linux largely work with PySide6) · License: [MIT](LICENSE)

Latest: Table rows/columns no longer have an upper limit (minimum is 1). [Full version history ↓](#8-version-history)

---

## 1. Quick start

```bat
pip install -r requirements.txt
python app.py
```

or double-click `run.bat` (starts with `pythonw`, no console window).

Requirements: Python 3.10+ (tested on 3.15), PySide6 6.6+.

---

## 2. Features and caveats

### 2.1 Editor

| Feature | Details |
|---|---|
| Source mode | Markdown source with line numbers, current-line highlight, monospace font, Tab = 4 spaces |
| Split mode | Source on the left and a **directly editable** rendered view on the right; edits sync back to Markdown, proportional scroll sync, `Ctrl`+click opens links. Home-tab formatting applies to whichever pane was focused last |
| WYSIWYG mode | Word-like rich text; Markdown syntax is hidden. Bold/italic/strikethrough/inline code, headings, lists, quotes, code blocks and tables survive the round-trip back to Markdown |
| Ribbon toolbar | File / Home / Insert / View / Convert tabs, collapsible, Fluent-inspired letter icons |
| Document tabs | Every opened file gets a tab above the editor; click to switch, drag to reorder, `×` to close. Dirty documents show `*` |
| Shortcuts | `Ctrl+N/O/S`, `Ctrl+Shift+S`, `Ctrl+B`, `Ctrl+I`, `Ctrl+K`, `Ctrl+F`, `Ctrl+Shift+M` (source), `Ctrl+Shift+P` (split), `Ctrl+Shift+W` (WYSIWYG), `Esc` closes search |
| Auto-save | Draft written to `.autosave/draft.md` every N seconds (default 120, i.e. 2 minutes; configurable in Settings) while dirty; recovery prompt on next start |
| Outline | Heading tree on the left; click to jump to the line |
| Theme & language | Light/dark toggle and 中文/English toggle, both in the top-right Ribbon area, persisted via QSettings |
| Drag & drop | Drop `.md`, `.docx`, `.pdf` onto the window to open or import |

**Caveats**

- WYSIWYG nested list levels may flatten; tables inserted while in WYSIWYG remain literal Markdown text until you switch to source mode.
- Rendering in split preview uses Qt's HTML/CSS subset, so very exotic Markdown extensions may look simpler than on GitHub. Typing in the right pane round-trips through the same rich-text → Markdown converter as WYSIWYG mode.
- PDF export produces a text-based PDF; fonts depend on what is installed on the system.
- Switching between document tabs reloads the document text, so the undo history restarts for that tab.

### 2.2 Conversion center

| Direction | Engine | Notes |
|---|---|---|
| Markdown → Word | `python-docx` | Headings, inline styles, lists, quotes, code blocks (shaded), tables (`Table Grid`), real hyperlinks, local images |
| Markdown → PDF | `QTextDocument` + `QPdfWriter` | Paper size (A4/A5/B5/Letter), margins in mm, font family/size configurable |
| Word → Markdown | `python-docx` | Handles runs, hyperlinks, tables and embedded images (saved to `assets/`) |
| PDF → Markdown | `pypdf` | Text extraction only — **no OCR**; scanned PDFs produce little or no text. Page breaks are marked with `<!-- Page N -->` |

The conversion page also provides:

- **Left source preview / right target preview** in a draggable splitter.
- **Difference strip** under the previews (`difflib` based) highlighting equal / added / removed / changed content.
- Paper size, margin, font family, font size and dark preview switch.
- “Use current document” or choose an external source file.

### 2.3 File management

New, open, save, save-as, recent files (1–50, configurable), export Word/PDF, import Word/PDF, and drag-and-drop opening. If the export target already exists, a prompt offers **Overwrite**, **Save as…** (a `name (1).docx` path is pre-filled in the save dialog) or **Cancel** instead of silently replacing the file; Save As on the main window behaves the same way. Multiple documents stay open as tabs; closing a dirty tab asks whether to save it. In the Recent list, right-click an entry and choose “Remove from recent” to drop it, or use “Clear all recent” at the bottom to empty the list. “Settings” in the same menu sets how many entries are shown (1–50) and an optional time window in days (0 = no limit). Tick “Don't show recent files” to hide the whole list; the choice is remembered.

---

## 3. Folder and file tree (index)

```
ClaraMarkdownEditor/
├── app.py                     # Application entry point
├── run.bat                    # Windows launcher (pythonw, no console)
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
├── .gitattributes             # Line-ending rules (LF, CRLF for .bat)
├── README.md                  # English README (primary)
├── README.zh-CN.md            # Chinese README
├── LICENSE                    # MIT License
├── clara/                     # Application package
│   ├── __init__.py            # App name, organization, version
│   ├── backup.py              # Versioned full-project backup + CLI
│   ├── converter.py           # Conversion facade and option dataclass
│   ├── convert_page.py        # Conversion center UI + diff strip
│   ├── docx_io.py             # Markdown ⇄ DOCX (python-docx)
│   ├── editor.py              # Source editor, find bar, split/WYSIWYG editor
│   ├── fileutils.py           # Export conflict prompt (overwrite/auto-number/cancel)
│   ├── i18n.py                # Chinese/English string table and I18n helper
│   ├── icons.py               # Painted letter icons (Fluent-ish)
│   ├── main_window.py         # Main window, actions, autosave, file I/O
│   ├── outline.py             # Heading outline panel
│   ├── pdf_io.py              # Markdown → PDF, PDF → Markdown (pypdf)
│   ├── qt_document.py         # QTextDocument → Markdown serializer
│   ├── render.py              # Markdown → HTML, HTML → Markdown, block parser
│   ├── ribbon.py              # Ribbon tab/group/button layout
│   ├── settings.py            # QSettings-backed preferences
│   └── theme.py               # Light/dark QSS stylesheet
├── .autosave/                 # (runtime) crash-recovery draft
└── _backups/                  # (runtime) full version backups
```

The two folders marked *(runtime)* are created automatically and are excluded from git and from version backups.

---

## 4. How the files call each other

```
app.py
 └─ QApplication → clara.main_window.MainWindow
      ├─ clara.settings.Settings        (language, theme, mode, autosave, recent files)
      ├─ clara.i18n.I18n                (all UI strings)
      ├─ clara.theme.build_stylesheet   (global QSS)
      ├─ clara.ribbon.RibbonBar
      │    └─ clara.icons.text_icon
      ├─ clara.outline.OutlinePanel → clara.render.iter_headings
      ├─ clara.editor.MarkdownEditor
      │    ├─ SourceEditor (line numbers) + FindBar
      │    ├─ clara.render.md_to_html        (split preview)
      │    └─ clara.qt_document.document_to_markdown (WYSIWYG → MD)
      ├─ clara.convert_page.ConvertPage
      │    ├─ clara.converter.convert / source_preview / target_preview
      │    ├─ clara.docx_io.export_md_to_docx / import_docx_to_md
      │    ├─ clara.pdf_io.export_md_to_pdf / import_pdf_to_md
      │    └─ DiffStrip (difflib)
      └─ clara.backup.create_backup
```

Data flow in one sentence: **main_window owns the document state** (`current_file`, `dirty`, editor content), and every other module is either a rendering helper, a converter, or a pure UI component that reports back through Qt signals.

- Split preview: `MarkdownEditor._on_source_changed` → 160 ms debounce → `render.md_to_html` → `PreviewEditor.setHtml`; typing in the right pane calls `document_to_markdown` and rewrites the source silently.
- WYSIWYG switch: `MarkdownEditor.set_mode` → `mark_quote_blocks` + `md_to_html` → rich text; switching back calls `document_to_markdown`.
- Conversion: `ConvertPage.refresh` asks `converter.source_preview` / `target_preview`; `run_conversion` calls `converter.convert`, which dispatches to `docx_io` / `pdf_io`.

---

## 5. Code walkthrough (file by file)

### `app.py`
Creates `QApplication` first (required by several Qt components), sets HiDPI rounding policy, application name/version, then lazily imports `MainWindow` to avoid importing Qt widgets too early. `main()` returns the Qt event-loop exit code.

### `clara/__init__.py`
Three constants used across the app: `APP_NAME`, `ORG_NAME` (QSettings namespace) and `__version__`.

### `clara/settings.py`
`Settings` wraps `QSettings(ORG_NAME, APP_NAME)`. Properties: `language`, `dark_mode`, `editor_mode`, `outline_visible`, `autosave_enabled`, `autosave_interval`, `last_dir`, plus recent-file settings (`recent_files()`, `visible_recent_files()`, `recent_limit` 1–50, `recent_days` 0 = no limit, `recent_hidden`, open timestamps stored as JSON) and helpers `add_recent_file()`, `remove_recent_file()`, `clear_recent_files()`. Booleans are stored as `"true"/"false"` strings to stay registry-friendly.

### `clara/fileutils.py`
`unique_path(path)` appends ` (1)`, ` (2)` … until the name is free. `resolve_overwrite(parent, i18n, path)` returns the original path when free; otherwise shows a warning box with **Overwrite / Save as… / Cancel**. “Save as…” opens a save dialog prefilled with the numbered path, and returns the chosen path or `None` if cancelled. Both the Ribbon exports and the conversion page call it after their save dialog (which runs with `DontConfirmOverwrite` so the user is asked only once).

### `clara/i18n.py`
`STRINGS` maps every key to `(Chinese, English)`. `I18n` holds the active language (`lang`), provides `t(key, **fmt)` with safe `str.format` and `toggle()`. `install_qt_translator(lang)` loads or removes Qt's own `qtbase_zh_CN` translation so standard context menus and dialog buttons follow the UI language. UI widgets call `retranslate()` so switching language rebuilds labels without restarting.

### `clara/theme.py`
`build_stylesheet(dark)` returns one large QSS string targeting `objectName`s (`RibbonTab`, `RibbonButton`, `GroupTitle`, `MiniButton`, `Outline`, `StatusBar`, …). Accent color is Word blue `#2b579a`; dark mode uses a neutral charcoal palette.

### `clara/icons.py`
`text_icon(text, size=22, …)` paints a rounded square with the accent color and centered initials. Font size adapts to 1/2/3+ characters so labels like `PDF` and `W>M` are not clipped. `clear_cache()` drops the in-memory icon cache when theme changes.

### `clara/render.py`
- `md_to_body_html`: Markdown → HTML body using the `markdown` package (`extra`, `sane_lists`, `toc`, `nl2br`), with `_fallback_markdown` if the package is unavailable.
- `md_to_html`: wraps the body with light/dark CSS, page width, font family/size and padding.
- `html_to_md`: `HTMLParser` builds a `_Node` tree, then `_inline`, `_render_list`, `_render_table`, `_render_block` serialize it back to Markdown (used for previews and fallbacks).
- `html_to_plain_text`: strips tags, used by PDF text extraction helpers.
- `parse_blocks`: lightweight block parser (heading/paragraph/code/quote/list/table/hr/image) used by DOCX export.
- `iter_headings`: yields `(level, text, line)` for the outline.
- `count_words`: counts CJK characters individually plus whitespace-separated Latin words.

### `clara/qt_document.py`
Serializer for the WYSIWYG document. Custom block properties `QUOTE_PROP` and `CODE_PROP` tag quote/code paragraphs; `mark_quote_blocks` also infers quotes from their background color when loading HTML. `document_to_markdown` walks blocks in order, handles `QTextTable` via `_table_to_md`, groups `QTextList` items by list object (so switching between bullet and numbered lists flushes correctly), strips bold from heading runs, and joins lists without blank lines.

### `clara/docx_io.py`
- `export_md_to_docx`: page size/margins, East-Asian font, headings (Heading 1–6), paragraphs with inline runs (`_add_inline_runs` handles `**b**`, `*i*`, `` `code` ``, `~~s~~`, links), bullet/numbered lists, shaded code blocks, `Table Grid` tables, and images.
- `_add_hyperlink`: real OOXML hyperlink relationship.
- `import_docx_to_md`: iterates body blocks in document order (`_iter_blocks`), converts runs and hyperlinks with `_runs_to_md`, saves embedded images into `assets/` (`_save_paragraph_images`), converts tables (`_table_to_md`), and merges adjacent list items with a regex so Markdown lists stay compact.

### `clara/pdf_io.py`
- `export_html_to_pdf`: `QPdfWriter` + `QTextDocument.print_`; the page paint rect is converted from device pixels using the writer resolution (96 dpi) so mm margins are accurate.
- `export_md_to_pdf`: renders Markdown to print CSS (white background regardless of UI theme) and exports.
- `import_pdf_to_md`: `pypdf` text extraction per page, `_merge_lines` re-joins hard-wrapped lines based on CJK/latin punctuation, pages separated by `<!-- Page N -->`.

### `clara/converter.py`
`ConversionOptions` dataclass (paper, margin, font family, font size, dark). `DIRECTIONS`, `DIRECTION_SOURCE`, `DIRECTION_TARGET` describe the four conversions. `convert()` validates direction, creates the output directory and dispatches. `source_preview` / `target_preview` return HTML for the left/right panes; MD targets render without page chrome to avoid horizontal scrolling.

### `clara/editor.py`
- `LineNumberArea` + `SourceEditor`: line-number gutter, current-line highlight, monospace font, auto-indent, Tab/Backtab indent support.
- `FindBar`: inline search with match counter, next/previous, Esc to close.
- `PreviewEditor`: editable rich-text pane used by split mode; `Ctrl`+click follows links, plain typing is converted back to Markdown.
- `MarkdownEditor`: owns a `QSplitter` with a source editor and an editable `PreviewEditor`; three modes (`source`, `split`, `wysiwyg`), 160 ms preview debounce, bidirectional rich-text ↔ Markdown sync in split mode, proportional scroll sync in both directions, `contentChanged` / `documentLoaded` / `cursorMoved` / `modeChanged` signals, formatting commands (`toggle_bold`, `toggle_italic`, `toggle_strike`, `toggle_inline_code`, `set_heading`, `toggle_list`, `toggle_quote`) and insert helpers (link, image, table, horizontal rule, code block).

### `clara/outline.py`
`OutlinePanel` lists headings using `iter_headings`, indents by level and emits `headingActivated(line)` on click; the main window scrolls the editor to that line.

### `clara/ribbon.py`
`RIBBON_LAYOUT` is declarative data: tab key → list of (group key, [(action key, icon text), …]). `RibbonButton` repaints its icon when language/theme changes; `RibbonGroup` adds the group caption. `RibbonBar` builds the tab strip, collapse button, document title and language/theme buttons, emits `actionTriggered`, `languageToggled`, `themeToggled`, `collapseToggled`, and rebuilds itself on `set_language` / `set_dark` (widgets are hidden, unparented and `deleteLater()`d to avoid ghost buttons).

### `clara/convert_page.py`
- `DiffStrip`: paints proportional color bands from `difflib.SequenceMatcher` opcodes (equal, insert, delete, replace) with separate light/dark palettes.
- `ConvertPage`: header, direction combo, parameter row (paper, margin, font, size, dark preview), source picker + “use current”, a `QSplitter` holding left/right `QStackedWidget`s (rendered preview for MD targets, read-only text for binary sources), diff legend, and the run button. `set_context_provider` lets the main window supply the live document; `refresh()` recomputes previews after a 200 ms debounce; `run_conversion()` chooses the output path and reports errors inline.

### `clara/main_window.py`
Builds the window: `RibbonBar`, a `QStackedWidget` (editor page / conversion page), `OutlinePanel`, status bar. Key parts:
- `_dispatch`: maps every Ribbon action key to a handler.
- File operations: `new_document`, `open_dialog`, `open_path`, `save_document`, `save_document_as`, `show_recent`, drag & drop handlers.
- Export/import shortcuts for Word/PDF reusing `converter` and `docx_io` / `pdf_io`.
- Autosave: QTimer writes `.autosave/draft.md` + `draft.json` when dirty; `_check_draft` offers recovery at startup.
- Language/theme: `_toggle_language`, `_toggle_theme`, `_apply_theme` (QSS + editor + convert page + ribbon).
- `backup_version`: asks for a note and calls `create_backup(APP_DIR, __version__, note)`.
- `show_about`, `closeEvent` (save prompt, draft flush) and status updates (mode, word count, cursor position).

### `clara/backup.py`
`create_backup(root, version, note)` copies the whole project into `_backups/{version}_{safe note}/`, ignoring `__pycache__`, `.git`, `.autosave`, `_backups`, `*.pyc`, `*.tmp`, and writes `BACKUP_INFO.txt`. Run from a terminal with:

```bat
python -m clara.backup "1.0.0 初始版本"
```

This is the same routine used by the “BKP” Ribbon button.

### `run.bat`
`cd /d "%~dp0"` then `start "" pythonw app.py` — launches without a console window.

---

## 6. Versioning, backup and README workflow

1. Bump `__version__` in `clara/__init__.py`.
2. Add a new entry to the **Version history** section below (both README files).
3. Run `python -m clara.backup "<change summary>"` (or click **BKP**). A full copy appears as `_backups/<version>_<change summary>/` containing `BACKUP_INFO.txt`.
4. Because the backup folder name includes both the version and the change note, every release keeps a self-contained snapshot.

---

## 7. Known limitations

- WYSIWYG nested list depth may be flattened when converting back to Markdown.
- Tables/lines inserted while in WYSIWYG are literal text until edited in source mode.
- PDF → Markdown works only for text-based PDFs (no OCR).
- Complex DOCX constructs (text boxes, charts, footnotes) are not converted.
- PySide6 is large; the frozen installer will exceed the 50 MB target even though the source tree is tiny.

---

## 8. Version history

Versioning rule: each number stays single-digit — after `1.0.9` comes `1.1.0`, then `1.1.1` … `1.1.9`, `1.2.0`.

### 1.3.8 — No upper limit on table size
- The Rows and Columns spin boxes now accept any positive number (minimum 1); the previous 20-row/column cap is removed.

### 1.3.7 — Table size picker
- The Table button now opens a dropdown with Rows and Columns spin boxes (1–20, default 3 × 3) plus an Insert Table command, instead of always inserting a 3 × 3 table.

### 1.3.6 — Insert tab is WYSIWYG in the split preview
- Link now inserts a real hyperlink (blue, underlined), image inserts the actual picture (scaled to fit), table inserts a formatted 3×3 table, horizontal rule draws a real line, and code block gets a shaded monospace block — no more raw Markdown markers in the right pane.
- These rich objects convert back to standard Markdown (`[](...)`, `![](...)`, pipe tables, `---`, fenced code) when the source pane is refreshed.

### 1.3.5 — Styled text from Markdown can now be toggled off
- Bold, Italic and Strikethrough now inspect the whole selection instead of a single cursor position. Text that already carries the style from Markdown (`**text**`, `*text*`, `~~text~~`) is un-styled on the first click and re-styled on the second.
- Mixed selections (partly styled) are treated as unstyled, so one click applies the style to the entire selection.

### 1.3.4 — Reliable bold/italic/strikethrough toggling in split preview
- Clicking Bold, Italic or Strikethrough in the right pane now toggles: the first click applies the style, the second click removes it.
- Fixed the formatting target being lost when the preview already had focus (no new focus event), which previously sent commands to the source pane instead.

### 1.3.3 — Ribbon icons for italic and strikethrough
- The Italic icon is now a slanted *I* and the Strikethrough icon an *S* crossed by a line, matching Office conventions.
- Icons are still drawn in code (no image assets), and both light and dark themes are supported.

### 1.3.2 — Strikethrough fixed
- `~~text~~` is now rendered as real strikethrough in split preview, PDF and PDF-preview HTML instead of showing literal tildes (a small Markdown inline extension, with fallback support).
- Fixed a crash in the Home-tab strikethrough command in rich-text modes (`fontStrikeOut` was read from the wrong object), and toggling it off now works.
- Selecting `~~text~~` in source mode and pressing the button unwraps it.

### 1.3.1 — Home-tab formatting works on the preview pane
- Bold, italic, strikethrough, inline code, headings, lists, quotes and inserts now apply to the right pane in split mode when it was the last focused pane, instead of always modifying the source.
- The target follows focus: click the source or the preview, then use the Home tab.

### 1.3.0 — Split-preview right pane is editable
- The rendered pane in split mode is no longer read-only: click and type directly, and the Markdown source updates silently.
- Editing in either pane keeps the other in sync (source → preview after a 160 ms debounce, preview → source immediately); scroll ratio and theme changes preserve content.
- Links open with `Ctrl`+click so a plain click can place the caret.

### 1.2.9 — Inline editable autosave interval
- The “Every N minutes” entry now embeds a spin box directly in the drop-down; type or step the number without opening a dialog.
- The interval is applied as soon as the value changes (1–120 minutes, default 2).

### 1.2.8 — Custom autosave interval
- The Auto Save drop-down now shows a “Every N minutes” item (default 2 minutes).
- Clicking it opens a dialog where the interval can be set from 1 to 120 minutes; the new value takes effect immediately.

### 1.2.7 — Autosave becomes a checkable drop-down
- In **Settings**, the **Auto Save** button now opens a drop-down with a checkable “Auto Save” item.
- Ticking or unticking it starts or stops the autosave timer immediately, and the choice is remembered.

### 1.2.6 — “View” tab renamed to “Settings”
- The fourth Ribbon tab is now “Settings” / “设置”; its Tools group (outline, autosave, about) is unchanged.

### 1.2.5 — Theme button removed from the View tab
- The View tab now only holds outline, autosave and about; theme switching stays available from the top-right control.

### 1.2.4 — Editing modes moved to the File tab
- Source, Split and WYSIWYG buttons moved from the View tab into a “Display” group on the File tab; the View tab keeps outline, theme, autosave and about.

### 1.2.3 — Exit button removed from the Ribbon
- The “Exit” button and its now-empty Tools group were removed from the File tab; close the window to quit.

### 1.2.2 — Recent moved next to Open
- The “Recent files” button now sits directly to the right of “Open” in the File tab, and the separate Tools slot only keeps “Exit”.

### 1.2.1 — Recent button no longer stays highlighted
- After the Recent dropdown closes, the Ribbon button is reset (`setDown(False)`, focus cleared, synthetic leave event), so its hover/pressed background no longer sticks.

### 1.2.0 — Consistent Save As behaviour
- “Save As” for Markdown files now uses the same conflict prompt as Word/PDF export: Overwrite, Save as… (numbered name pre-filled) or Cancel, instead of silently replacing an existing file.

### 1.1.9 — “Save as…” conflict option
- The conflict prompt’s middle button is now “Save as…”: it opens a save dialog prefilled with `name (1).ext`, so the user can confirm the suggested name, edit it, or cancel. Overwrite and Cancel are unchanged.

### 1.1.8 — Export conflict prompt
- Exporting Word/PDF (and running a conversion) onto an existing file no longer overwrites silently: a dialog offers Overwrite, Auto-number (`name (1).ext`, `name (2).ext`, …) or Cancel.

### 1.1.7 — Localized context menus
- Loading Qt's `qtbase_zh_CN` translation makes the built-in right-click menus (undo, cut, copy, paste, select all) and standard dialog buttons follow the UI language; switching language updates them immediately.

### 1.1.6 — Hide recent files
- Added a checkable “Don't show recent files” item to the Recent dropdown. When ticked, the list is replaced by a hint and the state is saved.

### 1.1.5 — Recent time window
- The Recent settings dialog now also lets you show only files opened within the last N days (0 = no limit, no upper bound). Entry timestamps are stored when a file is opened.

### 1.1.4 — Recent list limit raised
- The maximum number of recent entries is now 50 (previously 20).

### 1.1.3 — Recent list settings
- Added “Settings” to the Recent dropdown; it asks for the number of entries to show (1–50) and stores the choice. The list length updates immediately.

### 1.1.2 — Clear all recent
- Added a “Clear all recent” item at the bottom of the Recent dropdown, separated from the file entries.

### 1.1.1 — Remove recent entries
- The Recent dropdown now supports right-clicking a file and choosing “Remove from recent” to delete that entry from the list.

### 1.1.0 — Document tabs
- Opening or creating documents now adds a tab above the editor; tabs can be clicked to switch, dragged to reorder and closed with `×`. Unsaved documents show `*`, and closing a dirty tab or the app asks to save each one.

### 1.0.9 — Developer backup moved
- Removed the developer-only “Backup Version” button from both the File and View ribbon tabs; it is now a “Create developer backup” button inside the About dialog. The `python -m clara.backup` CLI still works.

### 1.0.8 — Line-ending configuration
- Added `.gitattributes` (`* text=auto eol=lf`, `.bat` CRLF) so Git stores text as LF and no longer prints “LF will be replaced by CRLF” warnings on the first `git add`.

### 1.0.7 — Recent files dropdown
- “Recent” now opens a dropdown menu anchored under the ribbon button instead of a modal dialog; each entry shows the file name with the full path as tooltip, and an empty list shows a disabled “No recent files” item.

### 1.0.6 — MIT License
- Replaced the custom copyright terms with the standard MIT License, allowing commercial use, modification and redistribution.

### 1.0.5 — Copyright file
- Added `LICENSE` with English and Chinese copyright notices and the personal/educational use terms.

### 1.0.4 — Startup mode
- The app now always starts in **Split Preview** mode instead of restoring the last-used mode.

### 1.0.3 — Theme button label
- Fixed: the theme toggle button kept showing “Dark Theme” after switching; it now always shows the theme you will switch to (“Light Theme” / “Dark Theme”, 浅色主题 / 深色主题), in both the top-right and the View tab.
- The label follows language changes as well.

### 1.0.2 — Consistent line spacing
- Split the preview/WYSIWYG stylesheet into a shared layout part plus color-only overrides, so light and dark themes now use identical paragraph, heading, list and code-block spacing.
- Fixed: dark-theme WYSIWYG content had visibly larger line spacing than the light theme.

### 1.0.1 — Drag-and-drop fix
- Fixed: dropping a file anywhere inside the editor (source, split preview or WYSIWYG) now opens it instead of inserting a `file:///...` text line.
- File drops are forwarded from the editor widgets to the main window; source/Word/PDF handling is unchanged.

### 1.0.0 — Initial release
- Word-style Ribbon UI (File / Home / Insert / View / Convert), collapsible.
- Three editing modes with line numbers, current-line highlight and scroll-synced preview.
- Auto-save draft and crash recovery.
- Conversion center with MD→DOCX, MD→PDF, DOCX→MD, PDF→MD, split previews, draggable divider and difference highlighting.
- Full Chinese/English UI switch in the top-right corner; light/dark themes.
- Recent files, drag-and-drop, version backup tool and bilingual README.
