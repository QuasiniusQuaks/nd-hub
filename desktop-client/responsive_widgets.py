"""
Responsive Widgets für die Notfalldepots Verwaltung
"""

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

from apple_theme import AppleTheme


class ResponsiveWidget(QtWidgets.QWidget):
    """Base class für responsive Widgets mit Breakpoints"""
    
    # Apple-Style Breakpoints
    BREAKPOINT_MOBILE = 640
    BREAKPOINT_TABLET = 1024
    BREAKPOINT_DESKTOP = 1440
    BREAKPOINT_WIDE = 1920
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_layout_mode = None
        self._update_layout_mode()
    
    def resizeEvent(self, event):
        """Reagiert auf Größenänderungen"""
        super().resizeEvent(event)
        self._update_layout_mode()
    
    def _update_layout_mode(self):
        """Bestimmt Layout-Modus basierend auf Breite"""
        width = self.width()
        
        if width < self.BREAKPOINT_MOBILE:
            new_mode = 'mobile'
        elif width < self.BREAKPOINT_TABLET:
            new_mode = 'compact'
        elif width < self.BREAKPOINT_DESKTOP:
            new_mode = 'normal'
        elif width < self.BREAKPOINT_WIDE:
            new_mode = 'wide'
        else:
            new_mode = 'ultra_wide'
        
        if new_mode != self._current_layout_mode:
            self._current_layout_mode = new_mode
            self._apply_layout_mode(new_mode)
    
    def _apply_layout_mode(self, mode):
        """Überschreiben in Subklassen - wird bei Modus-Wechsel aufgerufen"""
        pass


class FlowLayout(QtWidgets.QLayout):
    """
    Flow Layout - passt Widgets automatisch an verfügbaren Platz an
    (wie CSS flexbox)
    """
    
    def __init__(self, parent=None, margin=-1, h_spacing=-1, v_spacing=-1):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)
    
    def addItem(self, item):
        self._items.append(item)
    
    def horizontalSpacing(self):
        if self._h_spacing >= 0:
            return self._h_spacing
        return self._smart_spacing()
    
    def verticalSpacing(self):
        if self._v_spacing >= 0:
            return self._v_spacing
        return self._smart_spacing()
    
    def count(self):
        return len(self._items)
    
    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientations(0)
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        return self._do_layout(QtCore.QRect(0, 0, width, 0), True)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        
        margin = self.contentsMargins()
        size += QtCore.QSize(
            margin.left() + margin.right(),
            margin.top() + margin.bottom()
        )
        return size
    
    def _do_layout(self, rect, test_only):
        """Layout-Algorithmus - verteilt Widgets"""
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing_x = self.horizontalSpacing()
        spacing_y = self.verticalSpacing()
        
        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue
                
            space_x = spacing_x + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton,
                QtWidgets.QSizePolicy.PushButton,
                Qt.Horizontal
            )
            space_y = spacing_y + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton,
                QtWidgets.QSizePolicy.PushButton,
                Qt.Vertical
            )
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y()
    
    def _smart_spacing(self):
        parent = self.parent()
        if parent is None:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(
                QtWidgets.QStyle.PM_LayoutHorizontalSpacing, None, parent
            )
        return parent.spacing()


class AnalyticsKpiCard(QtWidgets.QFrame):
    """Kompakte KPI-Karte für den modernen Analytics-Look"""
    def __init__(self, title, value, unit="", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self.setMinimumWidth(180)
        self.setMinimumHeight(80)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title (Caption style)
        self.lbl_title = QtWidgets.QLabel(title.upper())
        c = AppleTheme.current_colors()
        self.lbl_title.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {c['tertiary_label']}; letter-spacing: 0.8px;"
        )
        layout.addWidget(self.lbl_title)
        
        # Value + Unit
        val_layout = QtWidgets.QHBoxLayout()
        val_layout.setSpacing(4)
        val_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        display_color = color if color else c["blue"]
        self.lbl_value = QtWidgets.QLabel(str(value))
        self.lbl_value.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {display_color};")
        val_layout.addWidget(self.lbl_value)
        
        if unit:
            self.lbl_unit = QtWidgets.QLabel(unit)
            self.lbl_unit.setStyleSheet(
                f"font-size: 14px; font-weight: 500; color: {c['tertiary_label']}; margin-top: 6px;"
            )
            val_layout.addWidget(self.lbl_unit)
            
        layout.addLayout(val_layout)
        layout.addStretch()


class ModernChartContainer(QtWidgets.QFrame):
    """Ein schicker Container für Diagramme mit abgerundeten Ecken und Schatten"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        if title:
            self.lbl_title = QtWidgets.QLabel(title)
            c = AppleTheme.current_colors()
            self.lbl_title.setStyleSheet(
                f"font-size: 15px; font-weight: 600; color: {c['label']};"
            )
            layout.addWidget(self.lbl_title)
            
        self.content_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.content_layout)
        
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
