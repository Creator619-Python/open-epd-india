"""open-epd-india adapter for the LCA Carbon Calculator (EN 15978).

Fetches from the open-epd-india JSON dataset:
  https://creator619-python.github.io/open-epd-india/india_epds.json

open-epd-india is an open (CC0), India-specific EPD database covering 388
verified EPDs across 21 material categories. GWP values (A1-A3) are extracted
from EPD PDFs with HIGH/MEDIUM/LOW extraction confidence.

JSON structure (v1.4+):
  {
    "version": "1.4.0",
    "last_updated": "2026-06-14",
    "total": 388,
    "epds": [
      {
        "registration_number": "EPD-IES-0031470:004",
        "material_name": "TMT Bars",
        "material_category": "Steel & Metal",
        "manufacturer_name": "Steel Authority of India Limited (SAIL)",
        "product_category": "Construction products",
        "geographical_scope": "Global",
        "country_of_origin": "India",
        "gwp_a1a3": 2363.0,
        "gwp_unit": "kg CO2eq/tonne",
        "declared_unit": "1000 kg",
        "life_cycle_stages": "A1-A3",
        "epd_programme_operator": "EPD International AB",
        "year_published": 2026,
        "valid_until": 2031,
        "epd_url": "https://www.environdec.com/library/epd31470",
        "extraction_confidence": "HIGH",   # HIGH / MEDIUM / None
        "notes": "...",
        "carbon_negative": false,
        "is_expired": false,
        "is_industrial_equipment": false
      },
      ...
    ]
  }

Design notes:
- Only gwp_a1a3 is surfaced. A4/A5/B6 are engine-derived; C1-C4 are not
  declared in the dataset (even A1-C4 records only carry the A1-A3 value
  in gwp_a1a3 — the field name reflects the extraction source, not that
  C modules are absent).
- Declared units are normalised: "1 tonne", "1000 kg", "1 metric tonne", "1 MT"
  → "tonne"; "1 m2" / "1 m²" → "m2"; "1 m3" → "m3"; "1 kg" → "kg"; etc.
  The engine handles mass conversion (kg ↔ tonne ↔ m3 via density).
- Expired EPDs (is_expired=True) and industrial equipment (is_industrial_equipment=True)
  are excluded from search results by default; the get() method still
  retrieves them if requested by registration_number.
- extraction_confidence "HIGH" → data_quality "epd";
  "MEDIUM" → "epd-estimated"; None → "screening".

Author: open-epd-india / Creator619-Python
License (data): CC0 1.0  |  Attribution requested: open-epd-india
Source: https://creator619-python.github.io/open-epd-india
"""

from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base import FactorAdapter, FactorCandidate
from ..models import EmissionFactorSet

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_URL = "https://creator619-python.github.io/open-epd-india/india_epds.json"
SOURCE_LABEL = "open-epd-india (CC0)"

_CONFIDENCE_TO_DQ: Dict[Optional[str], str] = {
    "HIGH": "epd",
    "MEDIUM": "epd-estimated",
    None: "screening",
}

# ---------------------------------------------------------------------------
# Declared-unit normalisation
# ---------------------------------------------------------------------------
# open-epd-india declared_unit strings are free-text from EPD PDFs.
# We strip the leading quantity ("1 ") and map to the engine's canonical units.
# Anything we can't map is kept as-is — the UI will show it and the user can
# override density/quantity as needed.

_UNIT_ALIASES: List[Tuple[re.Pattern, str]] = [
    # mass — tonne family  (must come before "t" alone)
    (re.compile(r"^(1\s*)?(metric\s*tonne|metric\s*ton|1000\s*kg|mt|tonne|ton)\b", re.I), "tonne"),
    (re.compile(r"^(1\s*)?t$", re.I), "tonne"),  # "1 t" (aluminium profiles, hot rolled coils)
    # mass — kilogram
    (re.compile(r"^(1\s*)?kg\b", re.I), "kg"),
    # mass — gram
    (re.compile(r"^(1\s*)?g\b", re.I), "g"),
    # area
    (re.compile(r"^(1\s*)?m\s*[²2]\b", re.I), "m2"),
    # volume
    (re.compile(r"^(1\s*)?m\s*[³3]\b", re.I), "m3"),
    # linear metre
    (re.compile(r"^(1\s*)?m\b", re.I), "m"),
    # watt-peak (solar panels)
    (re.compile(r"^(1\s*)?wp\b", re.I), "Wp"),
    # litre
    (re.compile(r"^(1\s*)?litre\b|^(1\s*)?l\b", re.I), "l"),
    # piece / unit / each
    (re.compile(r"^(1\s*)?(piece|pcs|unit|product|each|nos|no\.)\b", re.I), "each"),
]


def _normalise_unit(raw: Optional[str]) -> str:
    """Map a free-text declared_unit string to the engine's canonical unit."""
    if not raw:
        return "kg"
    text = raw.strip()
    for pattern, canonical in _UNIT_ALIASES:
        if pattern.match(text):
            return canonical
    # Couldn't map — return cleaned original so the UI can display it.
    # Strip a leading "1 " if present.
    return re.sub(r"^1\s+", "", text).strip() or text


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class OpenEPDIndiaAdapter(FactorAdapter):
    """Adapter serving GWP factors from the open-epd-india database.

    The full dataset (~388 records, ~150 KB) is fetched once on first use and
    cached in memory for the session. A threading lock prevents duplicate
    fetches on concurrent Streamlit reruns.

    Parameters
    ----------
    api_url:
        Override the JSON endpoint (useful for offline testing with a local
        fixture — pass a ``file://`` path or a local HTTP URL).
    timeout:
        HTTP timeout in seconds (default 15).
    exclude_expired:
        If True (default), EPDs with is_expired=True are hidden from search
        results (but still retrievable by registration_number via get()).
    exclude_industrial:
        If True (default), records with is_industrial_equipment=True are
        hidden from search. Industrial equipment EPDs have very large declared
        units (e.g. "1 Cold Rolling Mill") and are not meaningful for
        building-element carbon assessment.
    """

    name = "open-epd-india"

    def __init__(
        self,
        api_url: str = API_URL,
        timeout: int = 15,
        exclude_expired: bool = True,
        exclude_industrial: bool = True,
    ) -> None:
        self.api_url = api_url
        self.timeout = timeout
        self.exclude_expired = exclude_expired
        self.exclude_industrial = exclude_industrial
        self._records: Optional[List[Dict[str, Any]]] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch and cache all EPD records (called once per session)."""
        with self._lock:
            if self._records is not None:
                return self._records
            resp = requests.get(self.api_url, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                records = payload
            elif isinstance(payload, dict):
                records = payload.get("epds", [])
            else:
                raise ValueError(
                    f"open-epd-india: unexpected JSON root type {type(payload).__name__}"
                )
            self._records = records
        return self._records

    def _searchable(self) -> List[Dict[str, Any]]:
        """Return records eligible for search (filters applied)."""
        records = self._fetch_all()
        if self.exclude_expired:
            records = [r for r in records if not r.get("is_expired", False)]
        if self.exclude_industrial:
            records = [r for r in records if not r.get("is_industrial_equipment", False)]
        return records

    @staticmethod
    def _confidence(record: Dict[str, Any]) -> Optional[str]:
        raw = record.get("extraction_confidence")
        return raw.upper() if raw else None

    @staticmethod
    def _dq(record: Dict[str, Any]) -> str:
        conf = OpenEPDIndiaAdapter._confidence(record)
        return _CONFIDENCE_TO_DQ.get(conf, "screening")

    @staticmethod
    def _geography(record: Dict[str, Any]) -> str:
        scope = record.get("geographical_scope") or ""
        origin = record.get("country_of_origin") or ""
        if scope and scope.lower() not in ("global", ""):
            return scope
        return origin or "IN"

    @staticmethod
    def _citation(record: Dict[str, Any], full: bool = False) -> str:
        reg = record.get("registration_number", "")
        name = record.get("material_name", reg)
        mfr = record.get("manufacturer_name", "")
        year = record.get("valid_until", "")
        url = record.get("epd_url", "")
        unit = _normalise_unit(record.get("declared_unit"))
        gwp = record.get("gwp_a1a3", "")

        if full:
            return (
                f"open-epd-india EPD: {name}"
                + (f", {mfr}" if mfr else "")
                + f" (Reg: {reg}, valid until: {year}). "
                f"GWP A1-A3 = {gwp} kg CO₂e per {unit}. "
                + (f"EPD source: {url}. " if url else "")
                + "Data: open-epd-india (CC0 1.0), "
                "creator619-python.github.io/open-epd-india. "
                "Verify against source EPD PDF and declared unit before "
                "external reporting."
            )
        # Short form for search result list
        parts = [f"open-epd-india · {mfr}" if mfr else "open-epd-india"]
        if year:
            parts.append(f"valid until {year}")
        return " · ".join(parts)

    def _to_candidate(self, record: Dict[str, Any]) -> FactorCandidate:
        return FactorCandidate(
            record_id=record["registration_number"],
            material_name=record.get("material_name", record["registration_number"]),
            declared_unit=_normalise_unit(record.get("declared_unit")),
            source=SOURCE_LABEL,
            source_type=self._dq(record),
            geography=self._geography(record),
            citation=self._citation(record, full=False),
            preview_gwp_a1a3=float(record.get("gwp_a1a3") or 0.0),
        )

    def _to_factor_set(self, record: Dict[str, Any]) -> EmissionFactorSet:
        dq = self._dq(record)
        unit = _normalise_unit(record.get("declared_unit"))
        gwp_a1a3 = float(record.get("gwp_a1a3") or 0.0)

        # Build notes
        notes_parts = [
            f"GWP A1-A3 from open-epd-india (extraction confidence: "
            f"{self._confidence(record) or 'unknown'})."
        ]
        life_cycle = record.get("life_cycle_stages", "")
        if life_cycle and life_cycle != "A1-A3":
            notes_parts.append(
                f"Source EPD covers {life_cycle}; only A1-A3 is stored here — "
                "C-stage data requires the full EPD PDF."
            )
        if record.get("carbon_negative"):
            notes_parts.append("Declared carbon-negative product.")
        if record.get("is_expired"):
            notes_parts.append("⚠ This EPD is expired — verify before use.")
        notes_parts.append(
            "C1-C4 not populated; use generic C-stage factors or a manual "
            "override with a citation."
        )

        return EmissionFactorSet(
            record_id=record["registration_number"],
            source=SOURCE_LABEL,
            source_type=dq,
            declared_unit=unit,
            gwp_by_module={
                "A1A3": gwp_a1a3,
                "A4": 0.0,   # engine derives from transport distance + mode
                "A5": 0.0,   # engine derives from wastage rate
                "B6": 0.0,   # engine derives from energy intensity + grid factor
                "C1": 0.0,   # not declared in open-epd-india v1.x
                "C2": 0.0,
                "C3": 0.0,
                "C4": 0.0,
            },
            material_name=record.get("material_name", record["registration_number"]),
            geography=self._geography(record),
            valid_until=str(record.get("valid_until", "")),
            citation=self._citation(record, full=True),
            data_quality=dq,
            notes=" ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # FactorAdapter interface
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 20) -> List[FactorCandidate]:
        """Search open-epd-india records by material name, manufacturer, or category.

        Matching is case-insensitive substring search across three fields.
        Results are ordered: HIGH confidence first, then by material name.
        Expired EPDs and industrial equipment are excluded by default.
        """
        records = self._searchable()
        needle = (query or "").strip().lower()

        if needle:
            records = [
                r for r in records
                if (
                    needle in (r.get("material_name") or "").lower()
                    or needle in (r.get("manufacturer_name") or "").lower()
                    or needle in (r.get("material_category") or "").lower()
                )
            ]

        # Sort: HIGH confidence first, then alphabetically
        _order = {"HIGH": 0, "MEDIUM": 1, None: 2}
        records = sorted(
            records,
            key=lambda r: (
                _order.get(r.get("extraction_confidence"), 2),
                (r.get("material_name") or "").lower(),
            ),
        )

        return [self._to_candidate(r) for r in records[:limit]]

    def get(self, record_id: str) -> EmissionFactorSet:
        """Retrieve an EPD by registration_number and return a full EmissionFactorSet."""
        for record in self._fetch_all():
            if record.get("registration_number") == record_id:
                return self._to_factor_set(record)
        raise KeyError(
            f"open-epd-india: registration number '{record_id}' not found. "
            "The database may have been updated — try searching again."
        )

    # ------------------------------------------------------------------
    # Convenience / metadata helpers (used by app.py status panel)
    # ------------------------------------------------------------------

    def available(self) -> bool:
        """Return True if the remote API is reachable."""
        try:
            self._fetch_all()
            return True
        except Exception:
            return False

    def total_count(self) -> int:
        """Total EPDs in the database (including expired/industrial)."""
        try:
            return len(self._fetch_all())
        except Exception:
            return 0

    def searchable_count(self) -> int:
        """EPDs visible in search (after applying exclude filters)."""
        try:
            return len(self._searchable())
        except Exception:
            return 0

    def categories(self) -> List[str]:
        """Unique material categories, sorted alphabetically."""
        try:
            cats = {r.get("material_category") for r in self._searchable()}
            return sorted(c for c in cats if c)
        except Exception:
            return []
