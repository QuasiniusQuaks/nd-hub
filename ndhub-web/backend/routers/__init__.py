"""FastAPI-Router für das ND-Hub Web-Backend.

Issue #60 — Modularisierung des 4758-LOC Monolithen.

Jeder Router kapselt eine thematische Gruppe von Endpoints.
Router werden in app.py via app.include_router() gemountet.
"""
