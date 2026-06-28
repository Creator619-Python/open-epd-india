# open-epd-india × lca-carbon-calculator

Integrates open-epd-india as a native EPD data source in [lca-carbon-calculator](https://github.com/upasana-sen/lca-carbon-calculator) — an open-source whole-life carbon screening tool (EN 15978) by Upasana Sen.

Once wired in, the calculator gains a searchable Indian EPD panel in its Inventory tab — 388 verified EPDs across 21 material categories, no API key, CC0.

---

## Files

| File | Purpose |
|---|---|
| `openepdindia.py` | The adapter — drop into `lca/factors/` |
| `test_openepdindia.py` | 38 offline tests — drop into `tests/` |

The `app.py` changes are documented below.

---

## Setup

### 1. Clone lca-carbon-calculator

```bash
git clone https://github.com/upasana-sen/lca-carbon-calculator
cd lca-carbon-calculator
```

### 2. Drop in the adapter and tests

```bash
cp path/to/openepdindia.py lca/factors/openepdindia.py
cp path/to/test_openepdindia.py tests/test_openepdindia.py
```

### 3. Wire into app.py

Add the import at the top alongside the other adapters:

```python
from lca.factors.openepdindia import OpenEPDIndiaAdapter
```

Add a cached instance after `okobaudat_adapter()`:

```python
@st.cache_resource
def openepdindia_adapter() -> OpenEPDIndiaAdapter:
    return OpenEPDIndiaAdapter()
```

Add the expander inside `render_inventory()`, after the ÖKOBAUDAT block and before the `st.data_editor` call:

```python
with st.expander("Add from open-epd-india (Indian EPD database)", expanded=False):
    st.caption(
        "Searches open-epd-india — an open (CC0) database of 388 verified Indian EPDs "
        "across 21 material categories (cement, steel, glass, tiles, paints, and more). "
        "No API key required. Imports A1–A3 GWP; A4/A5/B6 remain engine-derived."
    )
    india = openepdindia_adapter()
    col_qi, col_ni = st.columns([3, 1])
    with col_qi:
        india_query = st.text_input("Search Indian EPD materials", "cement", key="india_query")
    with col_ni:
        india_n = st.number_input("Max results", min_value=1, max_value=50, value=15, step=5, key="india_n")
    if st.button("Search open-epd-india"):
        try:
            with st.spinner("Searching open-epd-india…"):
                st.session_state["india_candidates"] = [
                    c.__dict__ for c in india.search(india_query, limit=int(india_n))
                ]
        except Exception as exc:
            st.session_state["india_candidates"] = []
            st.error(f"open-epd-india request failed: {exc}. Generic and manual factors still work.")
    india_candidates = st.session_state.get("india_candidates", [])
    if india_candidates:
        st.caption(f"{len(india_candidates)} result(s). Data: open-epd-india (CC0 1.0).")
        india_labels = [
            f"{c['material_name'][:70]} | {c['preview_gwp_a1a3']:g} kgCO2e/{c['declared_unit']} | {c['citation']}"
            for c in india_candidates
        ]
        india_chosen = st.selectbox("EPD record", india_labels, key="india_choice")
        india_chosen_c = india_candidates[india_labels.index(india_chosen)]
        ci1, ci2, ci3 = st.columns(3)
        with ci1:
            india_element = st.text_input("Element name", "Frame", key="india_el")
        with ci2:
            india_category = st.selectbox("Category", ELEMENT_CATEGORIES, key="india_cat")
        with ci3:
            india_qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0, key="india_qty")
        if st.button("Add Indian EPD material"):
            try:
                with st.spinner("Loading EPD record…"):
                    india_factor = india.get(india_chosen_c["record_id"])
                project.line_items.append(
                    LineItem(
                        element_name=india_element,
                        category=india_category,
                        material_name=india_factor.material_name,
                        quantity=india_qty,
                        unit=india_factor.declared_unit,
                        transport_distance_km=project.default_transport_distance_km,
                        transport_mode="road",
                        wastage_rate=0.0,
                        factor=india_factor,
                        notes="open-epd-india EPD (CC0). Set wastage/density if needed.",
                    )
                )
                st.success(
                    f"Added {india_factor.material_name[:50]} "
                    f"({india_factor.declared_unit}, A1–A3 {india_factor.gwp_by_module['A1A3']:.3g} kgCO2e). "
                    "Source: open-epd-india (CC0 1.0)."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Could not load EPD record: {exc}")
```

### 4. Run the tests

```bash
# Copy india_epds.json to the repo root so offline tests can find it
cp path/to/india_epds.json .

pytest tests/test_openepdindia.py -v
# 38 passed
```

---

## How the adapter works

The adapter follows the `FactorAdapter` interface (`search()` + `get()`) so it
slots in alongside the existing `OkobaudatAdapter` and `GenericFactorAdapter`
with no changes to the engine.

**Data flow:**
- `search(query)` — fetches `india_epds.json` once, caches in memory, returns
  `FactorCandidate` list filtered by name / manufacturer / category
- `get(registration_number)` — returns a full `EmissionFactorSet` with A1-A3
  GWP populated and A4/A5/B6/C modules at 0.0 (engine-derived or not declared)

**Data quality mapping:**

| extraction_confidence | source_type (engine) |
|---|---|
| HIGH | `epd` |
| MEDIUM | `epd-estimated` |
| None | `screening` |

**Filters applied by default:**
- `is_expired=True` records excluded from search
- `is_industrial_equipment=True` records excluded from search
- Both are still retrievable by `registration_number` via `get()`

---

## Coverage

388 EPDs · 21 categories · 373 searchable (14 expired, ~5 industrial excluded)

Top categories by count: Steel & Metal · Concrete & Cement · Fibre Cement & Boards · Aluminium · Glass · Flooring & Surfaces

---

## Data source

**open-epd-india** — India's open EPD database  
[creator619-python.github.io/open-epd-india](https://creator619-python.github.io/open-epd-india)  
License: CC0 1.0 · Maintained by [Gokul Krishna T.B.](https://github.com/Creator619-Python)
