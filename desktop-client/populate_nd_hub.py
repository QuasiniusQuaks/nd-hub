#!/usr/bin/env python3
"""
ND-Hub – Testdaten-Generator
=============================
Befüllt die Datenbank mit realistischen Testdaten basierend auf den
Gelben Tafeln / Notfalltafeln der Apothekerkammern.

Präparate orientieren sich an typischen Notfalldepot-Sortimenten:
- Analgetika & Antipyretika
- Antibiotika (parenteral)
- Antidote & Gegenmittel
- Kardiovaskuläre Notfallmedikamente
- Infusionslösungen
- Antikonvulsiva / Sedativa
- Atemwegs-Notfallmedikamente
- Gynäkologische Notfallpräparate
- Ophthalmika / HNO-Notfall
- Sonstige Notfallpräparate
"""

import sqlite3
import random
import os
import sys
from datetime import datetime, timedelta

# Dynamischer Pfad zur Datenbank
if os.name == 'nt': # Windows
    DB_PATH = os.path.join(os.environ['APPDATA'], 'ND-Hub', 'nd_hub.db')
else:
    DB_PATH = os.path.expanduser('~/ND-Hub/nd_hub.db')

# ============================================================
# STAMMDATEN: Notfalldepots (fiktive, realistische Standorte)
# ============================================================
DEPOTS = [
    {
        "name": "Notfalldepot Kreis Musterstadt",
        "adresse": "Hauptstraße 12, 12345 Musterstadt",
        "telefon": "0234 / 567890",
        "email": "depot-musterstadt@aponet.de",
        "kontakte": [
            ("Dr. Maria Schneider", "Depotleiterin", "0234 567891", "m.schneider@aponet.de"),
            ("Thomas Becker", "Stellvertreter", "0234 567892", "t.becker@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Landkreis Oberberg",
        "adresse": "Bahnhofstr. 5, 51643 Gummersbach",
        "telefon": "02261 / 34567",
        "email": "depot-oberberg@aponet.de",
        "kontakte": [
            ("Apothekerin Petra Müller", "Depotleiterin", "02261 34568", "p.mueller@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Rheingau",
        "adresse": "Marktplatz 8, 65366 Geisenheim",
        "telefon": "06722 / 12345",
        "email": "depot-rheingau@aponet.de",
        "kontakte": [
            ("Dr. Klaus Weber", "Depotleiter", "06722 12346", "k.weber@aponet.de"),
            ("Anna Hoffmann", "Pharmazeutin", "06722 12347", "a.hoffmann@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Bergisches Land",
        "adresse": "Kölner Str. 22, 42651 Solingen",
        "telefon": "0212 / 987654",
        "email": "depot-bergisch@aponet.de",
        "kontakte": [
            ("Dr. Sabine Fischer", "Depotleiterin", "0212 987655", "s.fischer@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Eifel-Mosel",
        "adresse": "Trierer Str. 15, 54290 Trier",
        "telefon": "0651 / 445566",
        "email": "depot-eifel@aponet.de",
        "kontakte": [
            ("Apotheker Jürgen Klein", "Depotleiter", "0651 445567", "j.klein@aponet.de"),
            ("Martina Lang", "Stellvertreterin", "0651 445568", "m.lang@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Sauerland",
        "adresse": "Arnsberger Str. 3, 59872 Meschede",
        "telefon": "0291 / 778899",
        "email": "depot-sauerland@aponet.de",
        "kontakte": [
            ("Dr. Helmut Braun", "Depotleiter", "0291 778900", "h.braun@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Niederrhein",
        "adresse": "Klever Str. 44, 47533 Kleve",
        "telefon": "02821 / 334455",
        "email": "depot-niederrhein@aponet.de",
        "kontakte": [
            ("Apothekerin Claudia Schröder", "Depotleiterin", "02821 334456", "c.schroeder@aponet.de"),
            ("Stefan Richter", "Pharmazeut", "02821 334457", "s.richter@aponet.de"),
        ]
    },
    {
        "name": "Notfalldepot Münsterland",
        "adresse": "Prinzipalmarkt 10, 48143 Münster",
        "telefon": "0251 / 667788",
        "email": "depot-muensterland@aponet.de",
        "kontakte": [
            ("Dr. Franziska Wolf", "Depotleiterin", "0251 667789", "f.wolf@aponet.de"),
        ]
    },
]

# ============================================================
# STAMMDATEN: Präparate (Gelbe Tafel / Notfalltafel)
# ============================================================
PRAEPARATE = [
    # --- Analgetika & Antipyretika ---
    "Morphin 10mg/1ml Amp.",
    "Morphin 20mg/1ml Amp.",
    "Metamizol 1g/2ml Amp. (Novalgin)",
    "Paracetamol 1g Infusionslsg.",
    "Ibuprofen 400mg Supp.",
    "Tramadol 100mg/2ml Amp.",
    "Piritramid 15mg/2ml Amp. (Dipidolor)",
    "Ketamin 50mg/ml 2ml Amp. (Ketanest S)",

    # --- Antibiotika (parenteral) ---
    "Ceftriaxon 2g i.v. (Rocephin)",
    "Ampicillin/Sulbactam 3g i.v. (Unacid)",
    "Piperacillin/Tazobactam 4,5g i.v.",
    "Gentamicin 80mg/2ml Amp.",
    "Meropenem 1g i.v.",
    "Metronidazol 500mg/100ml Inf.",

    # --- Antidote & Gegenmittel ---
    "Atropin 0,5mg/1ml Amp.",
    "Naloxon 0,4mg/1ml Amp. (Narcanti)",
    "Flumazenil 0,5mg/5ml Amp. (Anexate)",
    "Aktivkohle 50g Pulver (Kohle-Compretten)",
    "N-Acetylcystein 5g/25ml Amp. (Fluimucil Antidot)",
    "Dimeticon Emulsion 50ml (Sab simplex)",
    "4-DMAP 250mg Amp.",
    "Natriumthiosulfat 10% 10ml Amp.",
    "Hydroxocobalamin 5g (Cyanokit)",
    "Obidoxim 250mg Amp. (Toxogonin)",
    "Physostigmin 2mg/5ml Amp. (Anticholium)",
    "Calciumgluconat 10% 10ml Amp.",

    # --- Kardiovaskuläre Notfallmedikamente ---
    "Adrenalin 1mg/1ml Amp. (Epinephrin)",
    "Noradrenalin 1mg/1ml Amp. (Arterenol)",
    "Amiodaron 150mg/3ml Amp. (Cordarex)",
    "Glyceroltrinitrat 0,8mg Spray (Nitrolingual)",
    "Urapidil 50mg/10ml Amp. (Ebrantil)",
    "Metoprolol 5mg/5ml Amp. (Beloc)",
    "Furosemid 20mg/2ml Amp. (Lasix)",
    "Heparin 25.000 I.E./5ml",
    "Acetylsalicylsäure 500mg i.v. (Aspirin i.v.)",
    "Dobutamin 250mg/50ml Inf. (Dobutrex)",
    "Vasopressin 20 I.E./1ml Amp.",
    "Adenosin 6mg/2ml Amp. (Adrekar)",
    "Verapamil 5mg/2ml Amp. (Isoptin)",

    # --- Infusionslösungen ---
    "NaCl 0,9% 500ml",
    "NaCl 0,9% 100ml",
    "NaCl 0,9% 10ml Amp.",
    "Ringer-Lösung 500ml",
    "Glucose 5% 500ml",
    "Glucose 40% 10ml Amp.",
    "HES 6% 500ml (Voluven)",
    "Natriumbicarbonat 8,4% 100ml",

    # --- Antikonvulsiva / Sedativa ---
    "Diazepam 10mg/2ml Amp. (Valium)",
    "Midazolam 5mg/1ml Amp. (Dormicum)",
    "Midazolam 15mg/3ml Amp. (Dormicum)",
    "Thiopental 500mg Trockensubstanz (Trapanal)",
    "Propofol 1% 20ml (Disoprivan)",
    "Lorazepam 2mg/1ml Amp. (Tavor)",
    "Phenytoin 250mg/5ml Amp. (Phenhydan)",
    "Levetiracetam 500mg/5ml Konz. (Keppra)",
    "Clonazepam 1mg/1ml Amp. (Rivotril)",

    # --- Atemwegs-Notfallmedikamente ---
    "Salbutamol DA 100µg/Hub (Sultanol)",
    "Ipratropiumbromid 0,5mg/2ml Inh. (Atrovent)",
    "Reproterol 0,09mg/1ml Amp. (Bronchospasmin)",
    "Prednisolon 250mg i.v. (Solu-Decortin H)",
    "Dexamethason 4mg/1ml Amp. (Fortecortin)",
    "Dexamethason 8mg/2ml Amp. (Fortecortin)",
    "Theophyllin 200mg/10ml Amp. (Euphylong)",

    # --- Muskelrelaxantien ---
    "Succinylcholin 100mg/5ml Amp. (Lysthenon)",
    "Rocuronium 50mg/5ml (Esmeron)",
    "Sugammadex 200mg/2ml (Bridion)",

    # --- Gynäkologische Notfallpräparate ---
    "Oxytocin 10 I.E./1ml Amp. (Syntocinon)",
    "Methylergometrin 0,2mg/1ml Amp. (Methergin)",
    "Fenoterol 0,5mg/10ml Amp. (Partusisten)",

    # --- Sonstige Notfallpräparate ---
    "Dimetinden 4mg/4ml Amp. (Fenistil)",
    "Ranitidin 50mg/5ml Amp. (Zantic)",
    "Ondansetron 4mg/2ml Amp. (Zofran)",
    "Tranexamsäure 1g/10ml Amp. (Cyklokapron)",
    "MgSO4 50% 10ml Amp.",
    "KCl 7,45% 20ml Amp.",
    "Insulin Actrapid 100 I.E./ml 10ml",
    "Clonidin 0,15mg/1ml Amp. (Catapresan)",
    "Haloperidol 5mg/1ml Amp. (Haldol)",
    "Promethazin 50mg/2ml Amp. (Atosil)",
    "Lidocain 2% 5ml Amp.",
    "Bupivacain 0,5% 4ml Amp. (Carbostesin)",
    "Alteplase 50mg (Actilyse)",
    "Norepinephrin-Perfusor 5mg/50ml",
]

# Chargen-Prefix basierend auf Hersteller
HERSTELLER_PREFIXE = [
    "CH-B", "FR", "RP", "SN", "BX", "HX", "KL", "MK",
    "PH", "AB", "GX", "TX", "NK", "WL", "ZR"
]


def random_charge():
    """Erzeugt eine realistische Chargennummer."""
    prefix = random.choice(HERSTELLER_PREFIXE)
    nummer = random.randint(10000, 99999)
    suffix = chr(random.randint(65, 90))
    return f"{prefix}{nummer}{suffix}"


def random_verfall(min_months=-3, max_months=36):
    """Erzeugt ein realistisches Verfallsdatum."""
    today = datetime.now()
    months = random.randint(min_months, max_months)
    target = today + timedelta(days=months * 30)
    # Verfallsdatum ist immer Ende des Monats
    if target.month == 12:
        target = target.replace(year=target.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        target = target.replace(month=target.month + 1, day=1) - timedelta(days=1)
    return target.strftime("%Y-%m-%d")


def random_eingang(months_ago_min=1, months_ago_max=18):
    """Erzeugt ein realistisches Eingangsdatum in der Vergangenheit."""
    today = datetime.now()
    days_ago = random.randint(months_ago_min * 30, months_ago_max * 30)
    return (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def populate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Prüfen ob bereits Daten vorhanden
    count = cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0]
    if count > 0:
        print(f"Datenbank enthält bereits {count} Depots. Bereinige Tabellen für Neubefüllung...")
        cur.execute("DELETE FROM bewegungen")
        cur.execute("DELETE FROM depot_praeparate")
        cur.execute("DELETE FROM kontakte")
        cur.execute("DELETE FROM depots")
        cur.execute("DELETE FROM praeparate")
        cur.execute("DELETE FROM warnung_einstellungen")
        conn.commit()

    print("=" * 60)
    print("ND-Hub Testdaten-Generator")
    print("Basierend auf Gelber Tafel / Notfalltafel")
    print("=" * 60)

    # ---- 1. Depots anlegen ----
    print(f"\n[1/5] Lege {len(DEPOTS)} Notfalldepots an...")
    depot_ids = {}
    for depot in DEPOTS:
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            (depot["name"], depot["adresse"], depot["telefon"], depot["email"])
        )
        depot_id = cur.lastrowid
        depot_ids[depot["name"]] = depot_id

        # Kontakte anlegen
        for kontakt in depot["kontakte"]:
            cur.execute(
                "INSERT INTO kontakte (depot_id, name, rolle, telefon, email) VALUES (?, ?, ?, ?, ?)",
                (depot_id, kontakt[0], kontakt[1], kontakt[2], kontakt[3])
            )
        print(f"  [OK] {depot['name']} (ID: {depot_id})")

    # ---- 2. Präparate anlegen ----
    print(f"\n[2/5] Lege {len(PRAEPARATE)} Präparate an...")
    praep_ids = {}
    for name in PRAEPARATE:
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", (name,))
        praep_ids[name] = cur.lastrowid
    print(f"  [OK] {len(PRAEPARATE)} Präparate angelegt")

    # ---- 3. Sollbestände je Depot ----
    print(f"\n[3/5] Definiere Sollbestände...")
    soll_count = 0
    for depot_name, depot_id in depot_ids.items():
        # Jedes Depot hat 50-80% der Präparate
        anzahl_praep = random.randint(
            int(len(PRAEPARATE) * 0.5),
            int(len(PRAEPARATE) * 0.8)
        )
        auswahl = random.sample(list(praep_ids.items()), anzahl_praep)

        for praep_name, praep_id in auswahl:
            # Sollbestand je nach Medikament
            if "Amp." in praep_name or "Spray" in praep_name:
                soll = random.choice([3, 5, 5, 10, 10, 10, 20])
            elif "500ml" in praep_name or "100ml" in praep_name:
                soll = random.choice([5, 10, 10, 20])
            elif "Pulver" in praep_name or "Trockensubstanz" in praep_name:
                soll = random.choice([2, 3, 5])
            else:
                soll = random.choice([3, 5, 10])

            cur.execute(
                "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
                (depot_id, praep_id, soll)
            )
            soll_count += 1
    print(f"  [OK] {soll_count} Sollbestand-Einträge")

    # ---- 4. Bewegungen (Eingang) – Aktueller Bestand ----
    print(f"\n[4/5] Erzeuge Bestandsbewegungen...")
    bew_count = 0

    for depot_name, depot_id in depot_ids.items():
        # Alle Soll-Einträge dieses Depots holen
        soll_entries = cur.execute(
            "SELECT praeparat_id, sollbestand FROM depot_praeparate WHERE depot_id = ?",
            (depot_id,)
        ).fetchall()

        for praep_id, sollbestand in soll_entries:
            # Für jedes Präparat 1-3 Chargen anlegen
            anz_chargen = random.choices([1, 2, 3], weights=[40, 40, 20])[0]
            restmenge = sollbestand

            for i in range(anz_chargen):
                if i == anz_chargen - 1:
                    menge = restmenge
                else:
                    menge = random.randint(1, max(1, restmenge - 1))
                    restmenge -= menge

                if menge <= 0:
                    continue

                charge = random_charge()
                verfall = random_verfall(min_months=-2, max_months=30)
                eingang = random_eingang(1, 12)

                cur.execute("""
                    INSERT INTO bewegungen 
                    (depot_id, praeparat_id, charge, verfall, eingang_datum, 
                     ausgang_datum, empfaenger, anzahl, typ, datei_pfad)
                    VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 'Zugang', NULL)
                """, (depot_id, praep_id, charge, verfall, eingang, menge))
                bew_count += 1

    # ---- 4b. Einige Ausgänge erzeugen ----
    print(f"  [OK] {bew_count} Zugangsbewegungen")

    ausgang_count = 0
    empfaenger_namen = [
        "Rettungsdienst Kreis Nord", "Notarzt Dr. Meier",
        "Feuerwehr Musterstadt", "DRK Kreisverband",
        "Intensivstation KH Süd", "Rettungswache Ost",
        "Notarzt Dr. Schmidt", "ASB Rettungsdienst",
        "Berufsfeuerwehr West", "Kindernotarzt",
    ]

    # Für ca. 15% der Depots einige Ausgänge erzeugen
    for depot_name, depot_id in depot_ids.items():
        # 5-15 Ausgänge pro Depot
        n_ausgaenge = random.randint(5, 15)
        eingaenge = cur.execute(
            """SELECT id, praeparat_id, charge, verfall, anzahl 
               FROM bewegungen 
               WHERE depot_id = ? AND typ = 'Zugang' AND ausgang_datum IS NULL
               ORDER BY RANDOM() LIMIT ?""",
            (depot_id, n_ausgaenge)
        ).fetchall()

        for eing in eingaenge:
            bew_id, praep_id, charge, verfall, anz = eing
            ausgang_menge = random.randint(1, max(1, anz))
            ausgang_datum = random_eingang(0, 6)
            empfaenger = random.choice(empfaenger_namen)

            # Neuen Ausgangs-Eintrag erzeugen
            cur.execute("""
                INSERT INTO bewegungen 
                (depot_id, praeparat_id, charge, verfall, eingang_datum,
                 ausgang_datum, empfaenger, anzahl, typ, datei_pfad)
                VALUES (?, ?, ?, ?, NULL, ?, ?, ?, 'Abgang', NULL)
            """, (depot_id, praep_id, charge, verfall,
                  ausgang_datum, empfaenger, ausgang_menge))
            ausgang_count += 1

    print(f"  [OK] {ausgang_count} Abgangsbewegungen")

    # ---- 5. Warnung-Einstellungen ----
    print(f"\n[5/5] Setze Warneinstellungen...")
    cur.execute("""
        UPDATE warnung_einstellungen 
        SET kritisch_tage = 30, warnung_tage = 90, achtung_tage = 180
        WHERE id = 1
    """)
    if cur.rowcount == 0:
        cur.execute("""
            INSERT INTO warnung_einstellungen 
            (kritisch_tage, warnung_tage, achtung_tage, email_benachrichtigung)
            VALUES (30, 90, 180, 0)
        """)
    print("  [OK] Kritisch: 30 Tage, Warnung: 90 Tage, Achtung: 180 Tage")

    conn.commit()

    # ---- Zusammenfassung ----
    total_bew = cur.execute("SELECT COUNT(*) FROM bewegungen").fetchone()[0]
    total_depots = cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0]
    total_praep = cur.execute("SELECT COUNT(*) FROM praeparate").fetchone()[0]
    total_soll = cur.execute("SELECT COUNT(*) FROM depot_praeparate").fetchone()[0]
    total_kontakte = cur.execute("SELECT COUNT(*) FROM kontakte").fetchone()[0]

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Depots:              {total_depots}")
    print(f"  Kontakte:            {total_kontakte}")
    print(f"  Präparate:           {total_praep}")
    print(f"  Soll-Einträge:       {total_soll}")
    print(f"  Bewegungen gesamt:   {total_bew}")
    print(f"  davon Zugänge:       {bew_count}")
    print(f"  davon Abgänge:       {ausgang_count}")
    print(f"\n  Datenbank: {DB_PATH}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    populate()