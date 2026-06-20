import unittest

from db_manager import Database


def _draft():
    return {
        "version": 3,
        "institution": {
            "name": "Test-Institution",
            "adresse": "Strasse 1",
            "latitude": None,
            "longitude": None,
        },
        "praeparate": [{"name": "P1"}],
        "depots": [
            {
                "name": "Depot A",
                "adresse": "Weg 2",
                "email": "depot@example.com",
                "telefon": "030123",
                "kontakt_name": "Zentrale",
                "praeparat_assignments": [{"name": "P1", "sollbestand": 5}],
            }
        ],
    }


class SetupWizardApplyTests(unittest.TestCase):
    def test_apply_inserts_rows(self):
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = Database(path)
            try:
                db.apply_setup_wizard_draft(_draft())
                inst = db.cur.execute("SELECT name FROM institutions ORDER BY id LIMIT 1").fetchone()
                self.assertEqual(inst[0], "Test-Institution")
                n_d = int(db.cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0])
                self.assertEqual(n_d, 1)
                dp = db.cur.execute(
                    """
                    SELECT dp.sollbestand FROM depot_praeparate dp
                    JOIN praeparate p ON p.id = dp.praeparat_id
                    WHERE p.name = ?
                    """,
                    ("P1",),
                ).fetchone()
                self.assertEqual(int(dp[0]), 5)
                k = db.cur.execute("SELECT name, email FROM kontakte LIMIT 1").fetchone()
                self.assertEqual(k[0], "Zentrale")
                self.assertEqual(k[1], "depot@example.com")
            finally:
                db.conn.close()
        finally:
            os.unlink(path)

    def test_second_apply_raises(self):
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = Database(path)
            try:
                db.apply_setup_wizard_draft(_draft())
                with self.assertRaises(RuntimeError):
                    db.apply_setup_wizard_draft(_draft())
                n_d = int(db.cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0])
                self.assertEqual(n_d, 1)
            finally:
                db.conn.close()
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
