"""
Apple-Style Theme für die Notfalldepots Verwaltung
Version 2.0 - Optimiert ohne unnötige Borders
"""
from PySide6 import QtGui
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect


class AppleTheme:
    """Apple Human Interface Guidelines für Qt - Clean Edition"""

    is_dark_mode = False

    # FARBEN LIGHT
    COLORS_LIGHT = {
        'bg_primary': '#f8f9fa',
        'bg_secondary': '#ffffff',
        'bg_tertiary': '#f9fafb',

        'blue': '#3498db',
        'green': '#27ae60',
        'red': '#e74c3c',
        'orange': '#ff9500',
        'yellow': '#ffcc00',
        'purple': '#af52de',
        'pink': '#ff2d55',

        'label': '#2c3e50',
        'secondary_label': '#7f8c8d',
        'tertiary_label': '#aeaeb2',
        'separator': '#e1e8ed',

        'hover': '#ebf5fb',
        'selected': 'rgba(52, 152, 219, 0.15)',

        'sidebar_bg_start': '#2c3e50',
        'sidebar_bg_end': '#34495e',
        'sidebar_text': '#bdc3c7',
        'sidebar_text_active': '#ecf0f1',

        # STATUS COLORS
        'status_green': '#34c759',
        'status_green_bg': 'rgba(52, 199, 89, 0.15)',
        'status_blue': '#007aff',
        'status_blue_bg': 'rgba(0, 122, 255, 0.12)',
        'status_orange': '#ff9500',
        'status_orange_bg': 'rgba(255, 149, 0, 0.15)',
        'status_red': '#ff3b30',
        'status_red_bg': 'rgba(255, 59, 48, 0.12)',
        'status_gray': '#8e8e93',
        'status_gray_bg': 'rgba(142, 142, 147, 0.12)',
    }

    # FARBEN DARK
    COLORS_DARK = {
        'bg_primary': '#1c1c1e',
        'bg_secondary': '#2c2c2e',
        'bg_tertiary': '#3a3a3c',

        'blue': '#0a84ff',
        'green': '#32d74b',
        'red': '#ff453a',
        'orange': '#ff9f0a',
        'yellow': '#ffd60a',
        'purple': '#bf5af2',
        'pink': '#ff375f',

        'label': '#ffffff',
        'secondary_label': '#ebebf5',
        'tertiary_label': '#aeaeb2',
        'separator': '#38383a',

        'hover': '#3a3a3c',
        'selected': 'rgba(10, 132, 255, 0.25)',

        'sidebar_bg_start': '#121212',
        'sidebar_bg_end': '#1c1c1e',
        'sidebar_text': '#8e8e93',
        'sidebar_text_active': '#ffffff',

        # STATUS COLORS DARK
        'status_green': '#30d158',
        'status_green_bg': 'rgba(48, 209, 88, 0.25)',
        'status_blue': '#0a84ff',
        'status_blue_bg': 'rgba(10, 132, 255, 0.2)',
        'status_orange': '#ff9f0a',
        'status_orange_bg': 'rgba(255, 159, 10, 0.25)',
        'status_red': '#ff453a',
        'status_red_bg': 'rgba(255, 69, 58, 0.2)',
        'status_gray': '#8e8e93',
        'status_gray_bg': 'rgba(142, 142, 147, 0.2)',
    }

    @classmethod
    def current_colors(cls):
        return cls.COLORS_DARK if cls.is_dark_mode else cls.COLORS_LIGHT

    @classmethod
    def toggle_dark_mode(cls):
        cls.is_dark_mode = not cls.is_dark_mode

    # TYPOGRAFIE
    TYPOGRAPHY = {
        'largetitle': {'size': 34, 'weight': 700, 'tracking': -0.5},
        'title1': {'size': 28, 'weight': 700, 'tracking': -0.5},
        'title2': {'size': 22, 'weight': 600, 'tracking': -0.4},
        'title3': {'size': 20, 'weight': 600, 'tracking': -0.2},
        'headline': {'size': 17, 'weight': 600, 'tracking': -0.4},
        'body': {'size': 17, 'weight': 400, 'tracking': -0.4},
        'callout': {'size': 16, 'weight': 400, 'tracking': -0.3},
        'subheadline': {'size': 15, 'weight': 400, 'tracking': -0.2},
        'footnote': {'size': 13, 'weight': 400, 'tracking': -0.1},
        'caption1': {'size': 12, 'weight': 400, 'tracking': 0},
        'caption2': {'size': 11, 'weight': 400, 'tracking': 0.1},
    }

    # SPACING
    SPACING = {
        'xs': 4,
        'sm': 8,
        'md': 16,
        'lg': 24,
        'xl': 32,
        'xxl': 48,
    }

    # RADIUS
    RADIUS = {
        'sm': 8,
        'md': 12,
        'lg': 16,
        'xl': 20,
        'circle': 9999,
    }

    @staticmethod
    def get_font(style_name):
        """Gibt QFont für den angegebenen Style zurück"""
        style = AppleTheme.TYPOGRAPHY.get(style_name, AppleTheme.TYPOGRAPHY['body'])
        font = QtGui.QFont("SF Pro Display", style['size'])
        if not font.exactMatch():
            font = QtGui.QFont("Segoe UI", style['size'])
        font.setWeight(QtGui.QFont.Weight(style['weight'] // 100))
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, style['tracking'])
        return font

    @staticmethod
    def apply_shadow(widget, blur_radius=20, opacity=0.08, x_offset=0, y_offset=6):
        """Aktiviert einen modernen, tiefen Apple-Style Glass-Schatten auf Widgets"""
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur_radius)
        # Im Dark Mode ein heller, weicher Drop-Shadow bzw. sehr dunkel
        shadow_color = QColor(0, 0, 0) if not AppleTheme.is_dark_mode else QColor(0, 0, 0)
        opacity = opacity if not AppleTheme.is_dark_mode else opacity * 3.0 # Im Dark Mode muss der Schatten dicker sein um sichtbar zu sein
        shadow_color.setAlphaF(opacity)
        shadow.setColor(shadow_color)
        shadow.setOffset(x_offset, y_offset)
        widget.setGraphicsEffect(shadow)

    # CHART COLORS
    CHART_PALETTE = ['#007aff', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#5856d6', '#ff2d55']
    CHART_PALETTE_DARK = ['#0a84ff', '#30d158', '#ff9f0a', '#ff453a', '#bf5af2', '#5e5ce6', '#ff375f']

    @classmethod
    def get_chart_palette(cls):
        return cls.CHART_PALETTE_DARK if cls.is_dark_mode else cls.CHART_PALETTE

    @classmethod
    def setup_matplotlib(cls, plt=None):
        """Konfiguriert Matplotlib für das Apple-Theme.

        ``plt`` darf weggelassen oder ``None`` sein — dann wird
        ``matplotlib.pyplot`` lazy importiert (Analytics-Charts rufen
        historisch ``setup_matplotlib(None)`` auf).
        """
        if plt is None:
            import matplotlib.pyplot as plt  # noqa: PLC0415
        c = cls.current_colors()
        _is_dark = cls.is_dark_mode

        # Basis-Konfiguration
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Segoe UI', 'DejaVu Sans']
        plt.rcParams['text.color'] = c['label']
        plt.rcParams['axes.labelcolor'] = c['secondary_label']
        plt.rcParams['axes.edgecolor'] = c['separator']
        plt.rcParams['xtick.color'] = c['secondary_label']
        plt.rcParams['ytick.color'] = c['secondary_label']
        plt.rcParams['grid.color'] = c['separator']
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['figure.facecolor'] = 'none' # Transparent für Padding
        plt.rcParams['axes.facecolor'] = 'none'

        # Achsen-Stil
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.right'] = False
        plt.rcParams['axes.linewidth'] = 1.0

        # Legende
        plt.rcParams['legend.frameon'] = False
        plt.rcParams['legend.fontsize'] = 10

    @staticmethod
    def get_stylesheet():
        """Komplettes Apple-Style Stylesheet - Border-optimiert & Dark/Light support"""
        c = AppleTheme.current_colors()
        r = AppleTheme.RADIUS

        return f"""
        /* APPLE-STYLE THEME - CLEAN EDITION NO BORDERS */

        /* GLOBAL */
        QWidget {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
            font-size: 13px;
            color: {c['label']};
            background-color: transparent;
            border: none;
        }}

        /* MAIN WINDOW */
        QMainWindow {{
            background: {c['bg_primary']};
        }}

        /* SIDEBAR DARK */
        QFrame#sidebar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 {c['sidebar_bg_start']}, stop:1 {c['sidebar_bg_end']});
            border: none;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }}

        #sidebar QLabel {{
            color: #ecf0f1;
            font-size: 16px;
            font-weight: 600;
            padding: 10px;
            background: transparent;
            border: none;
        }}

        #sidebar QPushButton {{
            background-color: transparent;
            color: {c['sidebar_text']};
            border: none;
            border-radius: {r['sm']}px;
            padding: 12px 16px;
            text-align: left;
            margin: 4px 8px;
            font-size: 14px;
            font-weight: 500;
        }}

        #sidebar QPushButton:hover {{
            background-color: rgba(52, 152, 219, 0.2);
            color: {c['sidebar_text_active']};
        }}

        #sidebar QPushButton:pressed {{
            background-color: rgba(52, 152, 219, 0.3);
        }}

        #sidebar QPushButton[active="true"] {{
            background-color: {c['blue']};
            color: white;
            font-weight: 600;
        }}

        /* CARDS / FRAMES - NO BORDER! */
        QFrame {{
            background: transparent;
            border: none;
        }}

        QFrame[frameShape="0"] {{
            background: {c['bg_secondary']};
            border: none;
            border-radius: {r['md']}px;
        }}

        /* Dashboard Cards mit objectName */
        QFrame[objectName="card"],
        QFrame[objectName="dashboard_card"],
        QFrame[objectName="tracking_card"],
        .card {{
            background: {c['bg_secondary']};
            border: 1px solid {c['separator']};
            border-radius: {r['lg']}px;
        }}

        /* Dashboard spezifische Styles */
        QWidget[objectName="dashboard_container"] {{
            background: {c['bg_primary']};
        }}

        QWidget[objectName="dashboard_header"] {{
            background: transparent;
            border: none;
        }}

        QLabel[objectName="dashboard_title"] {{
            color: {c['label']};
            font-weight: 700;
            background: transparent;
            border: none;
        }}

        QLabel[objectName="dashboard_date"] {{
            color: {c['secondary_label']};
            background: transparent;
            border: none;
            padding: 0;
        }}

        QFrame[objectName="kpi_card"] {{
            background: {c['bg_secondary']};
            border: none;
            border-radius: {r['xl']}px;
        }}

        QFrame[objectName="activity_item"] {{
            background: {c['bg_tertiary']};
            border-radius: 6px;
            padding: 8px;
        }}

        QFrame[objectName="activity_item"]:hover {{
            background: {c['hover']};
        }}

        /* BUTTONS WITH BORDER */
        QPushButton {{
            background: {c['blue']};
            color: white;
            border: none;
            border-radius: {r['sm']}px;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: -0.2px;
        }}

        QPushButton:hover {{
            background: {"#409cff" if AppleTheme.is_dark_mode else "#2980b9"};
            border: none;
        }}

        QPushButton:pressed {{
            background: {"#0060df" if AppleTheme.is_dark_mode else "#21618c"};
        }}

        QPushButton:disabled {{
            background: {c['tertiary_label']};
            color: {c['secondary_label']};
            border: none;
        }}

        /* Secondary Button */
        QPushButton[objectName="btn_secondary"] {{
            background: #95a5a6;
            color: white;
            border: none;
        }}

        QPushButton[objectName="btn_secondary"]:hover {{
            background: #7f8c8d;
        }}

        /* Delete Button */
        QPushButton[objectName="btn_delete"] {{
            background: {c['red']};
            color: white;
            font-weight: 600;
            border: none;
        }}

        QPushButton[objectName="btn_delete"]:hover {{
            background: #c0392b;
            color: white;
        }}

        /* Add/Save Button */
        QPushButton[objectName="btn_add"],
        QPushButton[objectName="btn_save"] {{
            background: {c['green']};
            color: white;
            border: none;
        }}

        QPushButton[objectName="btn_add"]:hover,
        QPushButton[objectName="btn_save"]:hover {{
            background: #229954;
        }}

        /* INPUT FIELDS WITH BORDER */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {{
            background: {c['bg_secondary']};
            border: 2px solid {c['separator']};
            border-radius: {r['sm']}px;
            padding: 8px 12px;
            font-size: 13px;
            color: {c['label']};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
            border: 2px solid {c['blue']};
            background: {c['bg_tertiary']};
        }}

        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
        QSpinBox:disabled, QDateEdit:disabled, QComboBox:disabled {{
            background: {c['bg_tertiary']};
            color: {c['tertiary_label']};
            border: 2px solid {c['separator']};
        }}

        /* TABLES */
        QTableWidget {{
            background: {c['bg_secondary']};
            alternate-background-color: {"#f2f2f7" if not AppleTheme.is_dark_mode else "#3a3a3c"};
            border: 1px solid {c['separator']};
            border-radius: {r['sm']}px;
            gridline-color: {c['separator']};
            selection-background-color: {c['blue']};
            selection-color: white;
            color: {c['label']};
        }}

        QTableWidget::item {{
            padding: 8px;
            border: none;
            border-bottom: 1px solid {c['separator']};
            color: {c['label']};
        }}

        QTableWidget::item:selected {{
            background: {c['blue']};
            color: white;
        }}

        QTableWidget::item:hover {{
            background: {c['hover']};
        }}

        /* DARK TABLE HEADER */
        QHeaderView::section {{
            background-color: {c['sidebar_bg_end']};
            color: white;
            padding: 12px 8px;
            border: none;
            font-weight: 600;
            font-size: 13px;
        }}

        QHeaderView::section:first {{
            border-top-left-radius: {r['sm']}px;
        }}

        QHeaderView::section:last {{
            border-top-right-radius: {r['sm']}px;
        }}

        QHeaderView::section:vertical {{
            background-color: {c['sidebar_bg_end']};
            color: white;
            padding: 8px 4px;
            border: none;
            font-weight: 500;
        }}

        /* SCROLLBAR MINIMAL */
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 0;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background: {("#7a7a7a" if AppleTheme.is_dark_mode else "#bdc3c7")};
            border-radius: 6px;
            min-height: 30px;
            border: none;
        }}

        QScrollBar::handle:vertical:hover {{
            background: #95a5a6;
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            height: 0px;
            border: none;
            background: transparent;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 12px;
            margin: 0;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background: {("#7a7a7a" if AppleTheme.is_dark_mode else "#bdc3c7")};
            border-radius: 6px;
            min-width: 30px;
            border: none;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: #95a5a6;
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            width: 0px;
            border: none;
            background: transparent;
        }}

        /* SCROLL AREA NO BORDER */
        QScrollArea {{
            border: none;
            background: transparent;
        }}

        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}

        /* TAB WIDGET */
        QTabWidget::pane {{
            border: 1px solid {c['separator']};
            border-radius: {r['sm']}px;
            background: {c['bg_secondary']};
            top: -1px;
        }}

        QTabBar::tab {{
            background: {c['bg_tertiary']};
            color: {c['label']};
            padding: 10px 20px;
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background: {c['bg_secondary']};
            color: {c['blue']};
            font-weight: 600;
        }}

        QTabBar::tab:hover {{
            background: {c['hover']};
        }}

        /* LABELS NO BORDER */
        QLabel {{
            background: transparent;
            border: none;
        }}

        QLabel[class="page-title"] {{
            font-size: 24px;
            font-weight: 700;
            color: {c['label']};
            letter-spacing: -0.5px;
            border: none;
        }}

        /* CHECKBOXES */
        QCheckBox {{
            spacing: 8px;
            color: {c['label']};
            background: transparent;
            border: none;
        }}

        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {c['separator']};
            border-radius: 4px;
            background: {c['bg_secondary']};
        }}

        QCheckBox::indicator:hover {{
            border-color: {c['blue']};
        }}

        QCheckBox::indicator:checked {{
            background: {c['blue']};
            border-color: {c['blue']};
        }}

        /* RADIO BUTTONS */
        QRadioButton {{
            spacing: 8px;
            color: {c['label']};
            background: transparent;
            border: none;
        }}

        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {c['separator']};
            border-radius: 10px;
            background: {c['bg_secondary']};
        }}

        QRadioButton::indicator:hover {{
            border-color: {c['blue']};
        }}

        QRadioButton::indicator:checked {{
            background: {c['bg_secondary']};
            border-color: {c['blue']};
            border-width: 6px;
        }}

        /* COMBOBOX */
        QComboBox::drop-down {{
            border: none;
            width: 30px;
            background: transparent;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c['secondary_label']};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background: {c['bg_secondary']};
            border: 1px solid {c['separator']};
            border-radius: {r['sm']}px;
            selection-background-color: {c['hover']};
            selection-color: {c['label']};
            padding: 4px;
            outline: none;
            color: {c['label']};
        }}

        /* SPINBOX */
        QSpinBox {{
            min-width: 100px;
        }}

        QSpinBox::up-button, QSpinBox::down-button {{
            background: {c['bg_tertiary']};
            border: none;
            width: 20px;
        }}

        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {c['separator']};
        }}

        QSpinBox::up-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {c['secondary_label']};
        }}

        QSpinBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c['secondary_label']};
        }}

        /* DATEEDIT CALENDAR */
        QDateEdit::drop-down {{
            background: {c['bg_secondary']};
            border: none;
            width: 30px;
        }}

        QDateEdit::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c['secondary_label']};
            margin-right: 8px;
        }}

        QCalendarWidget {{
            background: {c['bg_secondary']};
            border: 1px solid {c['separator']};
            border-radius: {r['sm']}px;
        }}

        QCalendarWidget QAbstractItemView {{
            background: {c['bg_secondary']};
            selection-background-color: {c['blue']};
            selection-color: white;
            color: {c['label']};
            border: none;
        }}

        QCalendarWidget QWidget {{
            background: {c['bg_secondary']};
            color: {c['label']};
        }}

        QCalendarWidget QToolButton {{
            background: {c['bg_secondary']};
            color: {c['label']};
            border: none;
            border-radius: 4px;
            padding: 4px;
        }}

        QCalendarWidget QToolButton:hover {{
            background: {c['hover']};
        }}

        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background: {c['sidebar_bg_end']};
            color: white;
        }}

        QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton {{
            color: white;
            background: transparent;
        }}

        QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton:hover {{
            background: rgba(52, 152, 219, 0.3);
        }}

        /* MESSAGE BOX */
        QMessageBox {{
            background: {c['bg_secondary']};
        }}

        QMessageBox QLabel {{
            color: {c['label']};
            border: none;
        }}

        /* PROGRESS BAR */
        QProgressBar {{
            border: 2px solid {c['separator']};
            border-radius: {r['sm']}px;
            text-align: center;
            background: {c['bg_tertiary']};
            height: 24px;
        }}

        QProgressBar::chunk {{
            background: {c['blue']};
            border-radius: {r['sm']}px;
        }}

        /* DIALOG */
        QDialog {{
            background: {c['bg_secondary']};
        }}

        /* LIST WIDGET */
        QListWidget {{
            background: {c['bg_secondary']};
            border: 1px solid {c['separator']};
            border-radius: 6px;
            padding: 4px;
            color: {c['label']};
        }}

        QListWidget::item {{
            padding: 6px;
            border: none;
            border-radius: 4px;
            color: {c['label']};
        }}

        QListWidget::item:hover {{
            background: {c['bg_tertiary']};
        }}

        QListWidget::item:selected {{
            background: {c['hover']};
            color: {c['label']};
        }}

        /* GROUP BOX */
        QGroupBox {{
            font-weight: 600;
            border: 1px solid {c['separator']};
            border-radius: {r['sm']}px;
            margin-top: 8px;
            padding-top: 8px;
            background: transparent;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {c['label']};
        }}

        /* FORM LABELS */
        QFormLayout QLabel {{
            color: {c['label']};
            font-weight: 500;
            background: transparent;
            border: none;
        }}

        /* STATUS BAR */
        QStatusBar {{
            background: {c['bg_secondary']};
            border-top: 1px solid {c['separator']};
            color: {c['secondary_label']};
        }}

        QStatusBar::item {{
            border: none;
        }}

        /* TOOL TIP (Kontrast in Light und Dark) */
        QToolTip {{
            background: {c['bg_tertiary']};
            color: {c['label']};
            border: 1px solid {c['separator']};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}

        # Collapsible Sections
        QFrame#collapsible_header {{
            background: {c['bg_secondary']};
            border: none;
            border-radius: 12px;
        }}

        QFrame#collapsible_header:hover {{
            background: {c['bg_tertiary']};
        }}

        QFrame#collapsible_content {{
            background: {c['bg_secondary']};
            border: none;
            border-radius: 0px 0px 12px 12px;
        }}

        """
