# open-epd-india

**India's first open, community-contributed Environmental Product Declaration (EPD) database.**

🔗 **[creator619-python.github.io/open-epd-india](https://creator619-python.github.io/open-epd-india)**

---

## What this is

A searchable, downloadable index of all Indian EPDs registered on [Environdec.com](https://www.environdec.com) — the world's largest EPD programme operator. Every record includes:

- Product name, manufacturer, and material category
- GWP A1-A3 value (kg CO₂eq) extracted from the EPD PDF
- Declared unit, life cycle stages, validity dates
- Direct link to the source EPD on Environdec

**No paywall. No registration. No request form. Just data.**

---

## Coverage

| Field | Value |
|---|---|
| Total EPDs | 388 |
| GWP A1-A3 values | 384 |
| Material categories | 21 |
| Manufacturers | 139 |
| Years covered | 2020 – 2026 |
| License | CC0 1.0 (public domain) |

**Categories:** Acoustic & Insulation · Aggregate & Stone · Aluminium · Brick & Masonry · Chemicals & Waterproofing · Concrete & Cement · Electrical & Electronics · Fibre Cement & Boards · Flooring & Surfaces · Furniture & Fittings · Glass · Gypsum & Plasterboard · Insulation · Paint & Coating · Plastic & Polymer · Refractories · Rubber & Tyres · Solar & Energy · Steel & Metal · Timber & Wood · Building (Whole)

---

## Using the data

### Download
Download `india_epds.csv` directly from this repo — no account needed.

### Python (pandas)
```python
import pandas as pd

df = pd.read_csv('https://raw.githubusercontent.com/Creator619-Python/open-epd-india/main/india_epds.csv')

# Filter to concrete EPDs with GWP data
concrete = df[
    (df['material_category'] == 'Concrete & Cement') &
    (df['gwp_a1a3'].notna())
].sort_values('gwp_a1a3')

print(concrete[['material_name', 'manufacturer_name', 'gwp_a1a3', 'gwp_unit']].to_string())
```

### Filter valid EPDs only
```python
import datetime
current_year = datetime.date.today().year
valid = df[df['valid_until'] >= current_year]
```

### Compare by unit (important — don't mix units)
```python
# GWP values are in different units per declared unit
# Always filter to the same unit before comparing
steel_per_tonne = df[
    (df['material_category'] == 'Steel & Metal') &
    (df['gwp_unit'] == 'kg CO2eq/tonne')
]
print(steel_per_tonne['gwp_a1a3'].describe())
```

---

## CSV schema

| Column | Description |
|---|---|
| `registration_number` | Environdec registration ID (e.g. EPD-IES-0031470:004) |
| `material_name` | Product name as declared in the EPD |
| `material_category` | Material category (21 categories, classified by this project) |
| `manufacturer_name` | EPD owner/manufacturer |
| `product_category` | Environdec product category |
| `geographical_scope` | India / Global / Asia |
| `country_of_origin` | Country of manufacture |
| `gwp_a1a3` | GWP total for life cycle stages A1-A3 (kg CO₂eq) |
| `gwp_unit` | Declared unit for GWP value (normalized canonical form) |
| `declared_unit` | Original declared unit from the EPD |
| `life_cycle_stages` | Stages covered (A1-A3, A1-C4, etc.) |
| `epd_programme_operator` | Programme operator (EPD International AB, etc.) |
| `year_published` | Year the EPD was registered |
| `valid_until` | Year the EPD expires (EPDs are valid for 5 years) |
| `epd_url` | Direct URL to the EPD on Environdec |
| `extraction_confidence` | HIGH / MEDIUM — confidence of AI GWP extraction |
| `notes` | Extraction notes and edge cases |
| `carbon_negative` | True if GWP A1-A3 is negative (e.g. timber biogenic carbon) |
| `is_expired` | True if valid_until < current year |
| `is_industrial_equipment` | True if GWP > 1,000,000 kg CO₂eq (whole-equipment EPDs) |

---

## Methodology

GWP A1-A3 values were extracted from EPD PDFs using a combination of:
- **Gemini** (primary extraction from PDF tables)
- **Groq / LLaMA-3.3-70b** (validation and fallback)

Extraction confidence is marked HIGH for unambiguous table reads and MEDIUM for values requiring interpretation. 4 EPDs had no machine-readable GWP value and remain blank.

All unit values have been normalized from 31 raw variants to 10 canonical forms (e.g. `kg CO2 eq/1000 kg` → `kg CO2eq/tonne`).

---

## Citing this database

```
Gokul Krishna T.B. (2026). open-epd-india: India's open EPD database (v1.3.0) [Dataset].
GitHub. https://github.com/Creator619-Python/open-epd-india
```

Or use the **⧉ Cite** button on the website to copy a formatted citation for any individual EPD.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add EPDs, report errors, or improve category classifications.

---

## Integrations

open-epd-india plugs into existing LCA and carbon tools as a data source. Ready-to-use adapters are in the [`integrations/`](integrations/) folder.

| Tool | What it does | Folder |
|---|---|---|
| [lca-carbon-calculator](https://github.com/upasana-sen/lca-carbon-calculator) | EN 15978 whole-life carbon screening (Streamlit) | [`integrations/lca-carbon-calculator/`](integrations/lca-carbon-calculator/) |

Each integration folder contains the adapter file, tests, and a README with drop-in instructions.

---

## Related projects

- [EPD SETU](https://www.epdsetu.com/) — IIT Madras EPD support initiative for Indian manufacturers
- [Environdec](https://www.environdec.com/) — Source database for all EPDs indexed here
- [EC3 / openEPD](https://buildingtransparency.org/) — Global embodied carbon database (US-focused)

---

## License

**CC0 1.0 Universal** — This database is dedicated to the public domain. You can copy, modify, distribute, and use the data for any purpose without asking permission or providing attribution (though attribution is appreciated).

*Built by [Gokul Krishna T.B.](https://www.linkedin.com/in/gokul-k-148624117/)*
