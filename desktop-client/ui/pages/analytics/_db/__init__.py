"""Zentralisierte Analytics-Queries — Delegation an Database.

Diese Schicht kapselt alle Analytics-DB-Aufrufe und stellt eine saubere
Schnittstelle für die UI-Tabs bereit. Die eigentlichen SQL-Queries liegen
in db_manager.py (Database-Klasse), hier wird nur delegiert.
"""
