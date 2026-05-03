#!/bin/bash
# ND-Hub Environment Setup Script

echo "[*] Initialisiere ND-Hub Umgebung..."

# Prüfen auf Python 3
if ! command -v python3 &> /dev/null
then
    echo "[!] Fehler: python3 wurde nicht gefunden."
    exit 1
fi

# Erstelle .venv falls nicht vorhanden
if [ ! -d ".venv" ]; then
    echo "[*] Erstelle neue virtuelle Umgebung (.venv)..."
    python3 -m venv .venv
fi

# Aktiviere venv und installiere/aktualisiere Anforderungen
echo "[*] Installiere/Aktualisiere Abhängigkeiten aus requirements.txt..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Spezieller Check für python-pptx
if ./.venv/bin/pip list | grep -q python-pptx; then
    echo "[+] python-pptx erfolgreich verifiziert."
else
    echo "[!] Warnung: python-pptx konnte nicht installiert werden."
fi

echo "[+] Setup abgeschlossen. Du kannst die Anwendung nun mit ./run_notfalldepots.py starten."
