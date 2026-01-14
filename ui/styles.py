"""
UI 样式表

"""


class StyleSheet:
    """样式表"""
    
    # 颜色定义
    PRIMARY = "#1a73e8"          
    PRIMARY_DARK = "#1557b0"
    PRIMARY_LIGHT = "#4285f4"
    SECONDARY = "#34a853"        
    ERROR = "#ea4335"            
    WARNING = "#fbbc04"          
    
    BACKGROUND = "#ffffff"
    SURFACE = "#f8f9fa"
    SURFACE_DARK = "#e8eaed"
    
    TEXT_PRIMARY = "#202124"
    TEXT_SECONDARY = "#5f6368"
    TEXT_DISABLED = "#9aa0a6"
    
    BORDER = "#dadce0"
    HOVER = "#f1f3f4"
    
    # 侧边栏颜色
    SIDEBAR_BACKGROUND = "#6191D3"

    # 主样式表
    MAIN = f"""
    QMainWindow {{
        background-color: #ffffff;
    }}
    
    /* 侧边栏 - 纯色背景 */
    #sidebar {{
        background-color: {SIDEBAR_BACKGROUND};
        border-right: 1px solid #dadce0;
        min-width: 256px;
        max-width: 256px;
    }}
    
    /* 侧边栏按钮样式 */
    #sidebar QPushButton {{
        text-align: left;
        padding: 12px 24px;
        border: none;
        border-radius: 0 24px 24px 0;
        background: transparent;
        color: #ffffff;
        font-size: 14px;
        font-weight: 500;
    }}
    
    #sidebar QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.1);
    }}
    
    #sidebar QPushButton:checked {{
        background-color: rgba(255, 255, 255, 0.2);
        color: #ffffff;
        font-weight: 600;
        border-left: 3px solid #ffffff;
    }}
    
    /* 面包屑导航容器 - 自下往上渐变浅蓝色 */
    #breadcrumb {{
        background: qlineargradient(
            x1: 0, y1: 1,
            x2: 0, y2: 0,
            stop: 0 #D6DEEB,
            stop: 1 #ffffff
        );
        border-bottom: 1px solid #dadce0;
        padding: 8px 16px;
    }}
    
    /* 我的云盘按钮选中状态特殊样式 */
    #sidebar QPushButton#navMyDrive:checked {{
        background-color: #3966A2;
        color: #ffffff;
        font-weight: 600;
        border-left: 3px solid #ffffff;
    }}
    
    /* 群组按钮选中状态 */
    #sidebar QPushButton#navGroups:checked {{
        background-color: rgba(255, 255, 255, 0.25);
        color: #ffffff;
        font-weight: 600;
        border-left: 3px solid #ffffff;
    }}
    
    /* 侧边栏标签样式 */
    #sidebar QLabel {{
        color: #ffffff;
        font-size: 14px;
        padding: 12px 24px;
    }}
    
    /* 内容区 */
    #content {{
        background-color: #ffffff;
    }}
    
    /* 工具栏 - 渐变浅蓝色背景 */
    #toolbar {{
        background: qlineargradient(
            x1: 0, y1: 0,
            x2: 0, y2: 1,
            stop: 0 #D6DEEB,
            stop: 1 #ffffff
        );
        border-bottom: 1px solid #dadce0;
        padding: 8px 16px;
    }}
    
    /* 主按钮 */
    QPushButton#primaryButton {{
        background-color: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 500;
    }}
    
    QPushButton#primaryButton:hover {{
        background-color: #1557b0;
    }}
    
    QPushButton#primaryButton:pressed {{
        background-color: #174ea6;
    }}
    
    QPushButton#primaryButton:disabled {{
        background-color: #dadce0;
        color: #9aa0a6;
    }}
    
    /* 新建按钮 (FAB 风格) */
    QPushButton#fabButton {{
        background-color: #ffffff;
        color: #202124;
        border: 1px solid #dadce0;
        border-radius: 24px;
        padding: 12px 24px 12px 16px;
        font-size: 14px;
        font-weight: 500;
        margin: 0 16px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    QPushButton#fabButton:hover {{
        background-color: #f1f3f4;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }}
    
    /* 输入框 */
    QLineEdit {{
        border: 1px solid #dadce0;
        border-radius: 4px;
        padding: 12px 16px;
        font-size: 14px;
        background-color: #ffffff;
        color: #202124;
    }}
    
    QLineEdit:focus {{
        border: 2px solid #1a73e8;
        padding: 13px 15px;
    }}
    
    QLineEdit:disabled {{
        background-color: #f8f9fa;
        color: #9aa0a6;
    }}
    
    /* 标签 */
    QLabel {{
        color: #202124;
        font-size: 14px;
    }}
    
    QLabel#title {{
        font-size: 22px;
        font-weight: 400;
        color: #202124;
    }}
    
    QLabel#subtitle {{
        font-size: 14px;
        color: #5f6368;
    }}
    
    QLabel#errorLabel {{
        color: #ea4335;
        font-size: 12px;
    }}
    
    /* 列表视图 */
    QListWidget {{
        border: none;
        background-color: transparent;
        outline: none;
    }}
    
    QListWidget::item {{
        padding: 8px 16px;
        border-radius: 8px;
        margin: 2px 8px;
    }}
    
    QListWidget::item:hover {{
        background-color: #f1f3f4;
    }}
    
    QListWidget::item:selected {{
        background-color: #e8f0fe;
        color: #1a73e8;
    }}
    
    /* 表格视图 */
    QTableWidget {{
        border: none;
        gridline-color: #e8eaed;
        background-color: #ffffff;
        selection-background-color: #e8f0fe;
        outline: 0;
    }}
    
    QTableWidget::item {{
        padding: 12px 16px;
        border-bottom: 1px solid #e8eaed;
    }}
    
    QTableWidget::item:selected {{
        background-color: #e8f0fe;
        color: #1a73e8;
    }}
    
    QHeaderView::section {{
        background-color: #f8f9fa;
        padding: 12px 16px;
        border: none;
        border-bottom: 1px solid #dadce0;
        font-weight: 500;
        color: #5f6368;
    }}
    
    /* 滚动条 */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background: #dadce0;
        border-radius: 4px;
        min-height: 40px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: #bdc1c6;
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    
    QScrollBar::handle:horizontal {{
        background: #dadce0;
        border-radius: 4px;
    }}
    
    /* 菜单 */
    QMenu {{
        background-color: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 8px 0;
    }}
    
    QMenu::item {{
        padding: 8px 24px;
        color: #202124;
    }}
    
    QMenu::item:selected {{
        background-color: #f1f3f4;
    }}
    
    QMenu::separator {{
        height: 1px;
        background-color: #e8eaed;
        margin: 4px 0;
    }}
    
    /* 进度条 */
    QProgressBar {{
        border: none;
        border-radius: 2px;
        background-color: #e8eaed;
        height: 4px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: #1a73e8;
        border-radius: 2px;
    }}
    
    /* 对话框 */
    QDialog {{
        background-color: #ffffff;
    }}
    
    /* 分组框 */
    QGroupBox {{
        font-weight: 500;
        border: 1px solid #dadce0;
        border-radius: 8px;
        margin-top: 16px;
        padding-top: 16px;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 8px;
        color: #5f6368;
    }}
    
    /* 复选框 */
    QCheckBox {{
        spacing: 8px;
        color: #202124;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid #5f6368;
        border-radius: 2px;
    }}
    
    QCheckBox::indicator:checked {{
        background-color: #1a73e8;
        border-color: #1a73e8;
    }}
    
    /* 下拉框 */
    QComboBox {{
        border: 1px solid #dadce0;
        border-radius: 4px;
        padding: 8px 12px;
        background-color: #ffffff;
        min-width: 120px;
    }}
    
    QComboBox:hover {{
        border-color: #bdc1c6;
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    
    /* 标签页 */
    QTabWidget::pane {{
        border: none;
        background-color: #ffffff;
    }}
    
    QTabBar::tab {{
        padding: 12px 24px;
        border: none;
        background: transparent;
        color: #5f6368;
        font-weight: 500;
    }}
    
    QTabBar::tab:selected {{
        color: #1a73e8;
        border-bottom: 2px solid #1a73e8;
    }}
    
    QTabBar::tab:hover:!selected {{
        color: #202124;
    }}
    
    /* Toast 提示 */
    #toast {{
        background-color: #323232;
        color: #ffffff;
        border-radius: 4px;
        padding: 12px 24px;
    }}
    """

    # 登录对话框样式
    LOGIN = """
    QDialog {
        background-color: #ffffff;
    }
    
    QLabel#logoLabel {
        font-size: 24px;
        font-weight: 500;
        color: #202124;
    }
    
    QLabel#welcomeLabel {
        font-size: 24px;
        font-weight: 400;
        color: #202124;
        margin-bottom: 8px;
    }
    
    QLabel#descLabel {
        font-size: 16px;
        color: #5f6368;
        margin-bottom: 24px;
    }
    
    QLineEdit {
        border: 1px solid #dadce0;
        border-radius: 4px;
        padding: 14px 16px;
        font-size: 16px;
        margin-bottom: 16px;
    }
    
    QLineEdit:focus {
        border: 2px solid #1a73e8;
        padding: 13px 15px;
    }
    
    QPushButton#loginButton {
        background-color: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 500;
        min-width: 88px;
    }
    
    QPushButton#loginButton:hover {
        background-color: #1557b0;
    }
    
    QPushButton#linkButton {
        background: transparent;
        border: none;
        color: #1a73e8;
        font-size: 14px;
        font-weight: 500;
        padding: 8px 16px;
    }
    
    QPushButton#linkButton:hover {
        background-color: #f1f3f4;
        border-radius: 4px;
    }
    
    QTabBar::tab {
        padding: 12px 24px;
        border: none;
        background: transparent;
        color: #5f6368;
        font-size: 14px;
        font-weight: 500;
    }
    
    QTabBar::tab:selected {
        color: #1a73e8;
        border-bottom: 2px solid #1a73e8;
    }
    """



    # 文件项样式
    FILE_ITEM = """
    QFrame#fileItem {
        background-color: #ffffff;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 12px;
    }
    
    QFrame#fileItem:hover {
        background-color: #f1f3f4;
        border-color: #dadce0;
    }
    
    QLabel#fileName {
        font-size: 14px;
        color: #202124;
        font-weight: 500;
    }
    
    QLabel#fileInfo {
        font-size: 12px;
        color: #5f6368;
    }
    """


class Icons:
    """图标 (使用 Unicode/Emoji 作为简化方案)"""

    # 文件类型
    FOLDER = "📁"
    FILE = "📄"
    IMAGE = "🖼️"
    VIDEO = "🎬"
    AUDIO = "🎵"
    DOCUMENT = "📝"
    ARCHIVE = "📦"
    CODE = "💻"

    # 操作
    UPLOAD = "⬆️"
    DOWNLOAD = "⬇️"
    DELETE = "🗑️"
    RENAME = "✏️"
    SHARE = "🔗"
    NEW_FOLDER = "📁+"

    # 导航
    HOME = "🏠"
    GROUP = "👥"
    INVITE = "📬"
    TRASH = "🗑️"
    SETTINGS = "⚙️"

    # 状态
    LOCK = "🔒"
    UNLOCK = "🔓"
    SYNC = "🔄"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"

    @staticmethod
    def get_file_icon(filename: str) -> str:
        """根据文件名获取图标"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        image_exts = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
        video_exts = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'}
        audio_exts = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'}
        doc_exts = {'doc', 'docx', 'pdf', 'txt', 'rtf', 'odt'}
        archive_exts = {'zip', 'rar', '7z', 'tar', 'gz'}
        code_exts = {'py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'h'}

        if ext in image_exts:
            return Icons.IMAGE
        elif ext in video_exts:
            return Icons.VIDEO
        elif ext in audio_exts:
            return Icons.AUDIO
        elif ext in doc_exts:
            return Icons.DOCUMENT
        elif ext in archive_exts:
            return Icons.ARCHIVE
        elif ext in code_exts:
            return Icons.CODE
        else:
            return Icons.FILE