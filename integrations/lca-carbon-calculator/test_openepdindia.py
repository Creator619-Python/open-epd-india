"""Tests for the open-epd-india adapter.

Runs fully offline — uses a local fixture loaded from india_epds.json.
No network calls are made.

Run with:
    pytest tests/test_openepdindia.py -v
or:
    python -m unittest tests/test_openepdindia.py -v
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Adapter import — works when run from the repo root
# ---------------------------------------------------------------------------
from lca.factors.openepdindia import OpenEPDIndiaAdapter, _normalise_unit


# ---------------------------------------------------------------------------
# Fixture: load the real india_epds.json so tests reflect production data
# ---------------------------------------------------------------------------
_FIXTURE_PATH = Path(__file__).parent.parent / "india_epds.json"


def _load_fixture() -> dict:
    with _fixture_path().open(encoding="utf-8") as f:
        return json.load(f)


def _fixture_path() -> Path:
    # Support running from repo root or from tests/ subdirectory
    candidates = [
        Path(__file__).parent.parent / "india_epds.json",
        Path("india_epds.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "india_epds.json not found. Run tests from the repo root."
    )


def _make_adapter() -> OpenEPDIndiaAdapter:
    """Return an adapter pre-loaded with the local fixture (no HTTP)."""
    fixture = _load_fixture()
    adapter = OpenEPDIndiaAdapter()
    # Bypass HTTP by injecting the records directly
    adapter._records = fixture["epds"]
    return adapter


# ---------------------------------------------------------------------------
# Unit normaliser tests
# ---------------------------------------------------------------------------

class UnitNormaliserTests(unittest.TestCase):

    def test_kg(self):
        self.assertEqual(_normalise_unit("1 kg"), "kg")
        self.assertEqual(_normalise_unit("kg"), "kg")

    def test_tonne_variants(self):
        for raw in ["1 tonne", "1 ton", "1 metric tonne", "1 metric ton",
                    "1000 kg", "1 MT", "1 t"]:
            with self.subTest(raw=raw):
                self.assertEqual(_normalise_unit(raw), "tonne", f"failed for {raw!r}")

    def test_area(self):
        self.assertEqual(_normalise_unit("1 m2"), "m2")
        self.assertEqual(_normalise_unit("1 m²"), "m2")
        self.assertEqual(_normalise_unit("1 m 2"), "m2")

    def test_volume(self):
        self.assertEqual(_normalise_unit("1 m3"), "m3")
        self.assertEqual(_normalise_unit("1 m³"), "m3")

    def test_linear(self):
        self.assertEqual(_normalise_unit("1 m"), "m")
        self.assertEqual(_normalise_unit("1m"), "m")

    def test_each_variants(self):
        for raw in ["1 piece", "1 unit", "1 product", "1 each", "1 nos"]:
            with self.subTest(raw=raw):
                self.assertEqual(_normalise_unit(raw), "each")

    def test_watt_peak(self):
        self.assertEqual(_normalise_unit("1 Wp"), "Wp")

    def test_litre(self):
        self.assertEqual(_normalise_unit("1 litre"), "l")

    def test_none_returns_kg(self):
        self.assertEqual(_normalise_unit(None), "kg")

    def test_unknown_strips_leading_quantity(self):
        # Exotic declared units pass through with leading "1 " stripped
        result = _normalise_unit("1 Tyre driven 1,000km")
        self.assertNotIn("1 ", result[:2])


# ---------------------------------------------------------------------------
# Adapter search tests
# ---------------------------------------------------------------------------

class SearchTests(unittest.TestCase):

    def setUp(self):
        self.adapter = _make_adapter()

    def test_search_cement_returns_results(self):
        results = self.adapter.search("cement")
        self.assertGreater(len(results), 0)
        # Search matches on material_name, manufacturer_name, OR material_category.
        # "Fibre Cement & Boards" and "Concrete & Cement" categories legitimately
        # return products whose names don't contain "cement" directly.
        for c in results:
            record = next(
                r for r in self.adapter._records
                if r["registration_number"] == c.record_id
            )
            matched_fields = (
                record.get("material_name", "").lower()
                + record.get("manufacturer_name", "").lower()
                + record.get("material_category", "").lower()
            )
            self.assertIn(
                "cement", matched_fields,
                msg=f"'cement' not in any search field for: {c.material_name}"
            )

    def test_search_steel_returns_results(self):
        results = self.adapter.search("steel")
        self.assertGreater(len(results), 0)

    def test_search_respects_limit(self):
        results = self.adapter.search("steel", limit=3)
        self.assertLessEqual(len(results), 3)

    def test_search_empty_query_returns_records(self):
        results = self.adapter.search("", limit=10)
        self.assertGreater(len(results), 0)

    def test_search_excludes_expired_by_default(self):
        results = self.adapter.search("", limit=500)
        for c in results:
            # All returned record_ids must not be expired
            record = next(
                r for r in self.adapter._records
                if r["registration_number"] == c.record_id
            )
            self.assertFalse(
                record.get("is_expired", False),
                f"Expired EPD returned: {c.record_id}"
            )

    def test_search_excludes_industrial_by_default(self):
        results = self.adapter.search("", limit=500)
        for c in results:
            record = next(
                r for r in self.adapter._records
                if r["registration_number"] == c.record_id
            )
            self.assertFalse(
                record.get("is_industrial_equipment", False),
                f"Industrial EPD returned: {c.record_id}"
            )

    def test_search_high_confidence_first(self):
        results = self.adapter.search("cement", limit=20)
        dqs = [c.source_type for c in results]
        # epd (HIGH) should appear before epd-estimated or screening
        if "epd-estimated" in dqs or "screening" in dqs:
            first_non_epd = next(
                i for i, d in enumerate(dqs) if d != "epd"
            )
            self.assertTrue(
                all(d == "epd" for d in dqs[:first_non_epd]),
                "HIGH confidence records should sort before MEDIUM/None"
            )

    def test_candidate_fields_populated(self):
        results = self.adapter.search("cement", limit=5)
        for c in results:
            self.assertTrue(c.record_id, "record_id should not be empty")
            self.assertTrue(c.material_name, "material_name should not be empty")
            self.assertIn(c.declared_unit, [
                "kg", "tonne", "m2", "m3", "m", "each", "g", "Wp", "l",
            ], f"Unexpected declared_unit: {c.declared_unit} for {c.material_name}")
            self.assertEqual(c.source, "open-epd-india (CC0)")
            self.assertGreaterEqual(c.preview_gwp_a1a3, 0.0)


# ---------------------------------------------------------------------------
# Adapter get() tests
# ---------------------------------------------------------------------------

class GetTests(unittest.TestCase):

    def setUp(self):
        self.adapter = _make_adapter()
        # Use first non-expired, non-industrial record as our test subject
        self.test_record = next(
            r for r in self.adapter._records
            if not r.get("is_expired") and not r.get("is_industrial_equipment")
        )
        self.reg = self.test_record["registration_number"]

    def test_get_returns_factor_set(self):
        from lca.models import EmissionFactorSet
        fs = self.adapter.get(self.reg)
        self.assertIsInstance(fs, EmissionFactorSet)

    def test_get_record_id_matches(self):
        fs = self.adapter.get(self.reg)
        self.assertEqual(fs.record_id, self.reg)

    def test_get_gwp_a1a3_matches_source(self):
        fs = self.adapter.get(self.reg)
        expected = float(self.test_record["gwp_a1a3"] or 0.0)
        self.assertAlmostEqual(fs.gwp_by_module["A1A3"], expected)

    def test_get_engine_derived_modules_are_zero(self):
        fs = self.adapter.get(self.reg)
        for module in ("A4", "A5", "B6"):
            self.assertEqual(
                fs.gwp_by_module[module], 0.0,
                f"{module} should be 0.0 (engine-derived, not from EPD)"
            )

    def test_get_c_modules_are_zero(self):
        # C1-C4 not declared in open-epd-india v1.x
        fs = self.adapter.get(self.reg)
        for module in ("C1", "C2", "C3", "C4"):
            self.assertEqual(fs.gwp_by_module[module], 0.0)

    def test_get_source_label(self):
        fs = self.adapter.get(self.reg)
        self.assertEqual(fs.source, "open-epd-india (CC0)")

    def test_get_source_type_high_confidence(self):
        # Find a HIGH confidence record
        high_rec = next(
            r for r in self.adapter._records
            if r.get("extraction_confidence") == "HIGH"
            and not r.get("is_expired")
            and not r.get("is_industrial_equipment")
        )
        fs = self.adapter.get(high_rec["registration_number"])
        self.assertEqual(fs.source_type, "epd")

    def test_get_declared_unit_normalised(self):
        fs = self.adapter.get(self.reg)
        self.assertIn(fs.declared_unit, [
            "kg", "tonne", "m2", "m3", "m", "each", "g", "Wp", "l",
        ], f"Raw declared_unit not normalised: {fs.declared_unit}")

    def test_get_citation_contains_reg_number(self):
        fs = self.adapter.get(self.reg)
        self.assertIn(self.reg, fs.citation)

    def test_get_citation_contains_cc0(self):
        fs = self.adapter.get(self.reg)
        self.assertIn("CC0", fs.citation)

    def test_get_valid_until_is_string(self):
        fs = self.adapter.get(self.reg)
        self.assertIsInstance(fs.valid_until, str)

    def test_get_unknown_id_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.adapter.get("EPD-DOES-NOT-EXIST:999")

    def test_get_tmt_bars_known_value(self):
        """Regression test against a known EPD — TMT Bars, SAIL, 2363 kgCO2e/tonne."""
        reg = "EPD-IES-0031470:004"
        if not any(r["registration_number"] == reg for r in self.adapter._records):
            self.skipTest("Known EPD not in fixture")
        fs = self.adapter.get(reg)
        self.assertAlmostEqual(fs.gwp_by_module["A1A3"], 2363.0)
        self.assertEqual(fs.declared_unit, "tonne")
        self.assertEqual(fs.source_type, "epd")


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

class MetaTests(unittest.TestCase):

    def setUp(self):
        self.adapter = _make_adapter()

    def test_total_count(self):
        self.assertEqual(self.adapter.total_count(), 388)

    def test_searchable_count_less_than_total(self):
        # 14 expired + 1+ industrial excluded
        self.assertLess(self.adapter.searchable_count(), self.adapter.total_count())

    def test_categories_returns_sorted_list(self):
        cats = self.adapter.categories()
        self.assertGreater(len(cats), 0)
        self.assertEqual(cats, sorted(cats))
        self.assertIn("Concrete & Cement", cats)  # actual category name in v1.x dataset
        self.assertIn("Steel & Metal", cats)


if __name__ == "__main__":
    unittest.main()
