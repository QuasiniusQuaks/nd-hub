"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import logging
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbInstitutionsMixin:
    def list_institutions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                    FROM institutions
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_onboarding_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM institutions")
                institutions = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM depots")
                depots = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM praeparate")
                praeparate = int((cur.fetchone() or {}).get("c") or 0)
        requires_onboarding = depots == 0 or praeparate == 0
        return {
            "requires_onboarding": bool(requires_onboarding),
            "counts": {
                "institutions": institutions,
                "depots": depots,
                "praeparate": praeparate,
            },
        }

    def create_institution(
        self,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        safe_name,
                        self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                        (strasse or "").strip() or None,
                        (hausnummer or "").strip() or None,
                        (postleitzahl or "").strip() or None,
                        (stadt or "").strip() or None,
                        float(latitude) if latitude is not None else None,
                        float(longitude) if longitude is not None else None,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_institution",
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            latitude=latitude,
            longitude=longitude,
        )
        return new_id

    def create_onboarding_setup(
        self,
        institution: dict[str, Any],
        praeparate: list[dict[str, Any]],
        depots: list[dict[str, Any]],
    ) -> dict[str, Any]:
        safe_name = str((institution or {}).get("name") or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        if not praeparate:
            raise ValueError("Mindestens ein Praeparat ist erforderlich.")
        if not depots:
            raise ValueError("Mindestens ein Notfalldepot ist erforderlich.")

        seen_praeparate: set[str] = set()
        normalized_praeparate: list[dict[str, Any]] = []
        for item in praeparate:
            item_name = str((item or {}).get("name") or "").strip()
            if not item_name:
                raise ValueError("Praeparat-Name darf nicht leer sein.")
            key = item_name.lower()
            if key in seen_praeparate:
                raise ValueError(f"Praeparat doppelt angegeben: {item_name}")
            seen_praeparate.add(key)
            normalized_praeparate.append(
                {
                    "name": item_name,
                    "wirkstoff": str((item or {}).get("wirkstoff") or "").strip() or None,
                    "darreichungsform": str((item or {}).get("darreichungsform") or "").strip() or None,
                    "staerke": str((item or {}).get("staerke") or "").strip() or None,
                    "einheit": str((item or {}).get("einheit") or "").strip() or None,
                    "pzn": str((item or {}).get("pzn") or "").strip() or None,
                    "hersteller": str((item or {}).get("hersteller") or "").strip() or None,
                }
            )

        with self._connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                    INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            safe_name,
                        self._compose_adresse(
                            str((institution or {}).get("adresse") or "").strip() or None,
                            str((institution or {}).get("strasse") or "").strip() or None,
                            str((institution or {}).get("hausnummer") or "").strip() or None,
                            str((institution or {}).get("postleitzahl") or "").strip() or None,
                            str((institution or {}).get("stadt") or "").strip() or None,
                        ),
                        str((institution or {}).get("strasse") or "").strip() or None,
                        str((institution or {}).get("hausnummer") or "").strip() or None,
                        str((institution or {}).get("postleitzahl") or "").strip() or None,
                        str((institution or {}).get("stadt") or "").strip() or None,
                            float(institution["latitude"]) if (institution or {}).get("latitude") is not None else None,
                            float(institution["longitude"]) if (institution or {}).get("longitude") is not None else None,
                        ),
                    )
                    institution_id = int(cur.lastrowid)

                    praeparat_ids_by_name: dict[str, int] = {}
                    for item in normalized_praeparate:
                        cur.execute(
                            """
                            INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                item["name"],
                                item["wirkstoff"],
                                item["darreichungsform"],
                                item["staerke"],
                                item["einheit"],
                                item["pzn"],
                                item["hersteller"],
                            ),
                        )
                        praeparat_ids_by_name[str(item["name"]).lower()] = int(cur.lastrowid)

                    created_depots: list[dict[str, Any]] = []
                    for depot in depots:
                        depot_name = str((depot or {}).get("name") or "").strip()
                        if not depot_name:
                            raise ValueError("Depot-Name darf nicht leer sein.")
                        cur.execute(
                            """
                            INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                depot_name,
                                self._compose_adresse(
                                    str((depot or {}).get("adresse") or "").strip() or None,
                                    str((depot or {}).get("strasse") or "").strip() or None,
                                    str((depot or {}).get("hausnummer") or "").strip() or None,
                                    str((depot or {}).get("postleitzahl") or "").strip() or None,
                                    str((depot or {}).get("stadt") or "").strip() or None,
                                ),
                                str((depot or {}).get("strasse") or "").strip() or None,
                                str((depot or {}).get("hausnummer") or "").strip() or None,
                                str((depot or {}).get("postleitzahl") or "").strip() or None,
                                str((depot or {}).get("stadt") or "").strip() or None,
                                str((depot or {}).get("telefon") or "").strip() or None,
                                str((depot or {}).get("email") or "").strip() or None,
                                institution_id,
                                float(depot["latitude"]) if (depot or {}).get("latitude") is not None else None,
                                float(depot["longitude"]) if (depot or {}).get("longitude") is not None else None,
                            ),
                        )
                        depot_id = int(cur.lastrowid)
                        assignments = list((depot or {}).get("assignments") or [])
                        if not assignments:
                            raise ValueError(f"Depot '{depot_name}' hat keine Praeparate-Zuordnung.")
                        seen_assignment: set[int] = set()
                        assignment_count = 0
                        for assignment in assignments:
                            praeparat_name = str((assignment or {}).get("praeparat_name") or "").strip()
                            praeparat_id = praeparat_ids_by_name.get(praeparat_name.lower())
                            if not praeparat_id:
                                raise ValueError(
                                    f"Unbekanntes Praeparat in Zuordnung fuer Depot '{depot_name}': {praeparat_name}"
                                )
                            if praeparat_id in seen_assignment:
                                continue
                            seen_assignment.add(praeparat_id)
                            sollbestand = int((assignment or {}).get("sollbestand", 0) or 0)
                            if sollbestand < 0:
                                raise ValueError("Sollbestand darf nicht negativ sein.")
                            cur.execute(
                                """
                                INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                                VALUES (%s, %s, %s)
                                """,
                                (depot_id, praeparat_id, sollbestand),
                            )
                            assignment_count += 1
                        if assignment_count == 0:
                            raise ValueError(f"Depot '{depot_name}' hat keine gueltige Praeparate-Zuordnung.")
                        created_depots.append({"id": depot_id, "name": depot_name, "assignments": assignment_count})
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        self._mirror_write(
            "create_onboarding_setup",
            institution=institution,
            praeparate=praeparate,
            depots=depots,
        )
        return {
            "institution_id": institution_id,
            "praeparate_count": len(normalized_praeparate),
            "depots": created_depots,
        }

    def update_institution(
        self,
        institution_id: int,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE institutions
                    SET name = %s, adresse = %s, strasse = %s, hausnummer = %s, postleitzahl = %s, stadt = %s, latitude = %s, longitude = %s
                    WHERE id = %s
                    """,
                    (
                        safe_name,
                        self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                        (strasse or "").strip() or None,
                        (hausnummer or "").strip() or None,
                        (postleitzahl or "").strip() or None,
                        (stadt or "").strip() or None,
                        float(latitude) if latitude is not None else None,
                        float(longitude) if longitude is not None else None,
                        int(institution_id),
                    ),
                )
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_institution",
            institution_id=institution_id,
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            latitude=latitude,
            longitude=longitude,
        )
        return changed

    def delete_institution(self, institution_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM depots WHERE institution_id = %s", (int(institution_id),))
                used = int((cur.fetchone() or {}).get("c") or 0)
                if used > 0:
                    raise ValueError("Institution ist noch Depots zugeordnet.")
                cur.execute("DELETE FROM institutions WHERE id = %s", (int(institution_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_institution", institution_id)
        return changed

    def set_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool) -> None:
        safe_username = (username or "").strip()
        if not safe_username:
            raise ValueError("Benutzername fehlt.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE can_read = VALUES(can_read), can_write = VALUES(can_write)
                    """,
                    (safe_username, int(depot_id), int(bool(can_read)), int(bool(can_write))),
                )
                conn.commit()
        self._mirror_write(
            "set_user_depot_permission",
            username=safe_username,
            depot_id=depot_id,
            can_read=can_read,
            can_write=can_write,
        )

    def list_user_depot_permissions(self, username: str) -> list[dict[str, Any]]:
        safe_username = (username or "").strip()
        if not safe_username:
            return []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT udp.depot_id, udp.can_read, udp.can_write, depots.name AS depot_name
                    FROM user_depot_permissions udp
                    JOIN depots ON depots.id = udp.depot_id
                    WHERE udp.username = %s
                    ORDER BY depots.name
                    """,
                    (safe_username,),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def list_map_institutions_with_depots(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        institutions.id AS institution_id,
                        institutions.name AS institution_name,
                        institutions.adresse AS institution_adresse,
                        institutions.strasse AS institution_strasse,
                        institutions.hausnummer AS institution_hausnummer,
                        institutions.postleitzahl AS institution_postleitzahl,
                        institutions.stadt AS institution_stadt,
                        institutions.latitude AS institution_latitude,
                        institutions.longitude AS institution_longitude,
                        depots.id AS depot_id,
                        depots.name AS depot_name,
                        depots.adresse AS depot_adresse,
                        depots.strasse AS depot_strasse,
                        depots.hausnummer AS depot_hausnummer,
                        depots.postleitzahl AS depot_postleitzahl,
                        depots.stadt AS depot_stadt,
                        depots.latitude AS depot_latitude,
                        depots.longitude AS depot_longitude
                    FROM institutions
                    LEFT JOIN depots ON depots.institution_id = institutions.id
                    ORDER BY institutions.name, depots.name
                    """
                )
                rows = cur.fetchall()
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            key = int(row["institution_id"])
            item = grouped.setdefault(
                key,
                {
                    "institution_id": key,
                    "institution_name": row["institution_name"],
                    "institution_adresse": row["institution_adresse"],
                    "institution_strasse": row["institution_strasse"],
                    "institution_hausnummer": row["institution_hausnummer"],
                    "institution_postleitzahl": row["institution_postleitzahl"],
                    "institution_stadt": row["institution_stadt"],
                    "latitude": row["institution_latitude"],
                    "longitude": row["institution_longitude"],
                    "depots": [],
                },
            )
            if row.get("depot_id") is not None:
                item["depots"].append(
                    {
                        "id": int(row["depot_id"]),
                        "name": row.get("depot_name"),
                        "adresse": row.get("depot_adresse"),
                        "strasse": row.get("depot_strasse"),
                        "hausnummer": row.get("depot_hausnummer"),
                        "postleitzahl": row.get("depot_postleitzahl"),
                        "stadt": row.get("depot_stadt"),
                        "latitude": row.get("depot_latitude"),
                        "longitude": row.get("depot_longitude"),
                    }
                )
        return list(grouped.values())
