"""ClaraMarkdownEditor 启动入口。

运行方式：
    python app.py
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from clara import APP_NAME, ORG_NAME, __version__


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)

    from clara.i18n import install_qt_translator
    from clara.settings import Settings

    install_qt_translator(Settings().language)

    # 延迟导入，确保 QApplication 先创建（部分 Qt 组件依赖它）
    from clara.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
