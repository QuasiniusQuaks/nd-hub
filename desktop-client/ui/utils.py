from PySide6 import QtWidgets
from PySide6.QtWidgets import QFrame, QHeaderView
from apple_theme import AppleTheme

def create_card_widget():
    card = QtWidgets.QWidget()
    card.setProperty("class", "card")
    return card

class NumericTableWidgetItem(QtWidgets.QTableWidgetItem):
    """Spezielles TableWidgetItem für korrekte numerische Sortierung"""
    def __lt__(self, other):
        try:
            return float(self.text().replace(',', '.')) < float(other.text().replace(',', '.'))
        except (ValueError, AttributeError):
            return super().__lt__(other)


def configure_responsive_table(
    table: QtWidgets.QTableWidget,
    stretch_columns=None,
    content_columns=None,
    no_wrap: bool = True,
    pixel_scroll: bool = True,
):
    """Wendet konsistente Responsive-Defaults für Tabellen an."""
    if pixel_scroll:
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
    if no_wrap:
        table.setWordWrap(False)

    header = table.horizontalHeader()
    if header is None:
        return

    for col in range(table.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.Interactive)

    for col in (content_columns or []):
        if 0 <= col < table.columnCount():
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

    for col in (stretch_columns or []):
        if 0 <= col < table.columnCount():
            header.setSectionResizeMode(col, QHeaderView.Stretch)


