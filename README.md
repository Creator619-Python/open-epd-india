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

**No paywall. No registration. No request form.**

> **Source: EPD International AB.**
>
> **AI-extracted data from the original published EPD.** Values may not be identical to the original EPD record. Every entry links to the original EPD on the International EPD System, which is the authoritative source.
>
> **Data notice.** All EPD data comes from [The International EPD System®](https://www.environdec.com) (EPD International AB). The EPDs are owned by their original owners and are subject to the [General Terms of Use](https://www.environdec.com/general-terms). GWP values here were extracted by AI and are **not verified**. Always check the linked original EPD before use. See [Data notice](#data-notice).

---

## Coverage

| Field | Value |
|---|---|
| Total EPDs | 388 |
| GWP A1-A3 values shown | 379 |
| Material categories | 21 |
| Manufacturers | 139 |
| Years covered | 2020 – 2026 |
| License | Index structure and classifications CC0 1.0; EPD data and values are subject to the source terms (see [Data notice](#data-notice)) |

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
| `material_category` | **Derived by this project** (not EPD data): material category, 21 groups |
| `manufacturer_name` | EPD owner/manufacturer |
| `product_category` | Environdec product category |
| `geographical_scope` | India / Global / Asia |
| `country_of_origin` | Country of manufacture |
| `gwp_a1a3` | GWP total for life cycle stages A1-A3 (kg CO₂eq) |
| `gwp_unit` | **Derived by this project** (not EPD data): a grouped unit label used only for filtering. The unit as published is `declared_unit` |
| `declared_unit` | Declared unit exactly as published in the EPD |
| `life_cycle_stages` | Stages covered (A1-A3, A1-C4, etc.) |
| `epd_programme_operator` | Programme operator (EPD International AB, etc.) |
| `year_published` | Year the EPD was registered |
| `valid_until` | Year the EPD expires (EPDs are valid for 5 years) |
| `epd_url` | Direct URL to the EPD on Environdec |
| `extraction_confidence` | HIGH / MEDIUM — confidence of AI GWP extraction |
| `notes` | Extraction notes and edge cases |
| `carbon_negative` | Derived by this project: True if GWP A1-A3 is negative (e.g. timber biogenic carbon) |
| `source` | Source: EPD International AB |
| `disclaimer` | AI-extracted data from the original published EPD. |
| `is_expired` | True if valid_until < current year |
| `is_industrial_equipment` | True if GWP > 1,000,000 kg CO₂eq (whole-equipment EPDs) |

---

## Methodology

GWP A1-A3 values were extracted from EPD PDFs using a combination of:
- **Gemini** (primary extraction from PDF tables)
- **Groq / LLaMA-3.3-70b** (validation and fallback)

Extraction confidence is the model's own rating (HIGH for unambiguous table reads, MEDIUM for values requiring interpretation). It is **not** human verification. No value has been independently checked unless noted in `notes`. 4 EPDs had no machine-readable GWP value and remain blank.

The site shows each value with the unit as declared in the original EPD. A derived `gwp_unit` group (e.g. `1000 kg` and `1 tonne` grouped as `kg CO2eq/tonne`) is used only for filtering, and is not EPD data.

Five entries (EPD-IES-0009817:001, EPD-IES-0009807:001, EPD-IES-0006086:001, EPD-IES-0001419:001, EPD-IES-0002108:001) have their GWP value withdrawn because the unit did not match the declared unit. They will return once checked against the original EPD.

---

## Citing this database
Gokul Krishna T.B. (2026). open-epd-india: India's open EPD database (v1.5.1) [Dataset].
GitHub. https://github.com/Creator619-Python/open-epd-india
Or use the **⧉ Cite** button on the website to copy a formatted citation for any individual EPD.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add EPDs, report errors, or improve category classifications.

---

## Related projects

- [The International EPD System®](https://www.environdec.com/) — Source of all EPDs indexed here; data subject to its [General Terms of Use](https://www.environdec.com/general-terms)
- [EC3 / openEPD](https://buildingtransparency.org/) — Global embodied carbon database (US-focused)

---

## Data notice

- **Source and ownership.** All EPDs originate from The International EPD System® (EPD International AB), published at environdec.com. Data in an EPD is owned by the original EPD owner. Use of the data is subject to the [International EPD System General Terms of Use](https://www.environdec.com/general-terms), including crediting the International EPD System as the source.
- **What is CC0.** The project's own contributions, namely the index structure, material categories, canonical unit scheme and flags (`carbon_negative`, `is_expired`, `is_industrial_equipment`), are dedicated to the public domain under CC0 1.0.
- **What is not CC0.** The EPD data and GWP values themselves are not ours to relicense. Where you use them, follow the source terms and link to the original EPD (`epd_url`).
- **Status.** The licensing of the extracted values is being clarified with EPD International AB. This notice will be updated with their answer.
- **No warranty.** Values are AI-extracted and unverified. Do not use them for LCA, certification or procurement without checking the original EPD.

## License

Index structure and project classifications: **CC0 1.0 Universal**. Code: MIT. EPD data and GWP values: see the [Data notice](#data-notice).

*Built by [Gokul Krishna T.B.](https://www.linkedin.com/in/gokul-k-148624117/)*
