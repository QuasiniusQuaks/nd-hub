"""Issue #67: package split of setup_wizard_dialog into step modules."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


class SetupWizardPackageTests(unittest.TestCase):
    def test_helpers_without_qt(self):
        from ui.dialogs.setup_wizard.helpers import (
            _default_depot_row,
            _depot_assignments_from_dict,
            _empty_draft,
            _require_http_scheme,
        )

        draft = _empty_draft()
        self.assertEqual(draft["version"], 3)
        self.assertIn("institution", draft)
        row = _default_depot_row()
        self.assertEqual(row["praeparat_assignments"], [])
        assigns = _depot_assignments_from_dict(
            {"praeparat_assignments": [{"name": "P1", "sollbestand": 2}]}
        )
        self.assertEqual(assigns, [{"name": "P1", "sollbestand": 2}])
        self.assertEqual(_require_http_scheme("https://example.com/x"), "https://example.com/x")
        with self.assertRaises(ValueError):
            _require_http_scheme("file:///etc/passwd")

    def test_legacy_import_path_matches_package(self):
        from ui.dialogs.setup_wizard import SetupWizardDialog as FromPkg
        from ui.dialogs.setup_wizard_dialog import SetupWizardDialog as FromLegacy

        self.assertIs(FromPkg, FromLegacy)

    def test_step_methods_attached_on_dialog_class(self):
        import inspect

        from ui.dialogs.setup_wizard import SetupWizardDialog
        from ui.dialogs.setup_wizard import navigation, step_backend

        for name in (
            "_build_backend_page",
            "_build_institution_page",
            "_build_praeparate_page",
            "_build_depots_page",
            "_build_review_page",
            "_save_depot_form_to_row",
            "_collect_draft",
            "_on_next",
            "_on_finalize",
            "_geocode_address_if_possible",
        ):
            fn = getattr(SetupWizardDialog, name, None)
            self.assertTrue(callable(fn), f"missing attached method: {name}")
            # Prefer class dict / unwrap to avoid MagicMock auto-attrs under Qt stub.
            raw = SetupWizardDialog.__dict__.get(name, fn)
            if hasattr(raw, "__func__"):
                raw = raw.__func__
            self.assertTrue(inspect.isfunction(raw) or inspect.ismethod(fn), name)

        self.assertTrue(inspect.isfunction(navigation.NavigationMixin._on_next))
        self.assertTrue(inspect.isfunction(step_backend.BackendStepMixin._build_backend_page))

    def test_module_files_parse_and_size_gates(self):
        root = Path(__file__).resolve().parents[2] / "ui" / "dialogs" / "setup_wizard"
        expected = {
            "wizard_main.py": 220,
            "step_backend.py": 300,
            "step_institution.py": 300,
            "step_praeparate.py": 300,
            "step_depots.py": 300,
            "step_depots_form.py": 300,
            "step_review.py": 300,
            "navigation.py": 300,
            "chrome.py": 300,
            "helpers.py": 200,
        }
        for name, max_loc in expected.items():
            path = root / name
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding="utf-8")
            ast.parse(text)
            loc = len(text.splitlines())
            self.assertLessEqual(loc, max_loc, f"{name} is {loc} LOC (max {max_loc})")

        shim = root.parent / "setup_wizard_dialog.py"
        shim_text = shim.read_text(encoding="utf-8")
        self.assertIn("from ui.dialogs.setup_wizard import SetupWizardDialog", shim_text)
        self.assertLessEqual(len(shim_text.splitlines()), 20)


if __name__ == "__main__":
    unittest.main()
