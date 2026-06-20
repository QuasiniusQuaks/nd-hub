import os
import tempfile
import unittest

from security_manager import SecurityManager


class CrossInstitutionPermissionTests(unittest.TestCase):
    def test_admin_has_cross_institution_helpers(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.environ["ND_HUB_INITIAL_ADMIN_PASSWORD"] = "TestAdmin!12345"
        try:
            manager = SecurityManager(path)
            try:
                ok, _ = manager.authenticate("admin", "TestAdmin!12345")
                self.assertTrue(ok)
                self.assertTrue(manager.can_view_cross_institution_masterdata())
                self.assertTrue(manager.can_edit_cross_institution_masterdata())
            finally:
                manager.close()
        finally:
            os.unlink(path)
            os.environ.pop("ND_HUB_INITIAL_ADMIN_PASSWORD", None)


if __name__ == "__main__":
    unittest.main()
