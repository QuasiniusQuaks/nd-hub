"""Shared-Package für gemeinsame Router, Services und Models.

Issue #65 — Code-Duplikation zwischen Desktop- und Web-Backend reduzieren.

Beide Backends (desktop-client/backend/ und ndhub-web/backend/) haben
identische Endpoint-Logik. Dieses Package stellt gemeinsame Router-Factorys
bereit, die von beiden Backends importiert werden.
"""
