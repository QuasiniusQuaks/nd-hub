import unittest

from core.setup_wizard_contract import (
    validate_depot_kontakt_and_assignments,
    validate_depot_stamm_rows,
    validate_institution_dict,
    validate_postleitzahl_optional,
    validate_praeparate_names,
)


class SetupWizardContractTests(unittest.TestCase):
    def test_validate_institution_dict_requires_name(self):
        self.assertFalse(validate_institution_dict({})[0])
        self.assertFalse(validate_institution_dict({"name": "  "})[0])
        self.assertTrue(validate_institution_dict({"name": "Klinik"})[0])

    def test_validate_praeparate_names(self):
        self.assertTrue(validate_praeparate_names(["A", "B"])[0])
        self.assertFalse(validate_praeparate_names(["A", "a"])[0])

    def test_validate_postleitzahl_optional(self):
        self.assertTrue(validate_postleitzahl_optional("")[0])
        self.assertTrue(validate_postleitzahl_optional("12345")[0])
        self.assertFalse(validate_postleitzahl_optional("1234")[0])

    def test_validate_depot_stamm_rows(self):
        self.assertFalse(validate_depot_stamm_rows([])[0])
        self.assertFalse(validate_depot_stamm_rows([{"name": ""}])[0])
        self.assertTrue(validate_depot_stamm_rows([{"name": "D1"}])[0])

    def test_validate_depot_kontakt_and_assignments(self):
        rows = [
            {
                "name": "D1",
                "email": "a@b.example.com",
                "praeparat_assignments": [{"name": "P1", "sollbestand": 2}],
            }
        ]
        pr = {"p1"}
        self.assertTrue(validate_depot_kontakt_and_assignments(rows, pr)[0])
        ok, _ = validate_depot_kontakt_and_assignments(
            [
                {
                    "name": "D1",
                    "email": "bad",
                    "praeparat_assignments": [{"name": "P1", "sollbestand": 0}],
                }
            ],
            pr,
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
