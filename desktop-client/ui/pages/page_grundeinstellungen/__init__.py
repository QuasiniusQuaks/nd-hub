"""Sub-Module für die Grundeinstellungen-Seite.

Re-Exporte für externe Konsumenten (z.B. `from ...page_grundeinstellungen
import DepotsPage`). Die Imports werden hier absichtlich vorgenommen,
damit das Paket als einheitliche Public-API fungiert.
"""
from ._hauptseite import GrundeinstellungenPage
from .backup_tab import BackupManager
from .depots_tab import DepotsPage
from .kontakte_tab import KontaktePage
from .praeparate_tab import PraeparatePage
from .zuordnungen_tab import AssignmentPage

__all__ = [
    "DepotsPage",
    "PraeparatePage",
    "KontaktePage",
    "AssignmentPage",
    "BackupManager",
    "GrundeinstellungenPage",
]
