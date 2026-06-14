# Contributing to open-epd-india

Thanks for wanting to contribute. This database grows through community effort — better data helps everyone doing embodied carbon work in India.

---

## Ways to contribute

### 1. Report a data error
If a GWP value, unit, or category is wrong, open a GitHub Issue with:
- Registration number (e.g. `EPD-IES-0031470:004`)
- What's wrong
- Correct value with source (link to EPD PDF or Environdec page)

### 2. Add a missing EPD
If an Indian EPD is on Environdec but not in this database, open an Issue or submit a PR with the new row added to `india_epds.csv`.

**Required fields:**
```
registration_number, material_name, material_category, manufacturer_name,
gwp_a1a3, gwp_unit, declared_unit, life_cycle_stages, year_published,
valid_until, epd_url
```

**How to find missing EPDs:**
1. Go to [environdec.com/library](https://www.environdec.com/library)
2. Filter by Country: India
3. Check against `india_epds.csv` — if the registration number isn't in the file, it's missing

### 3. Improve a category classification
Some EPDs may be in the wrong `material_category`. Open an Issue with:
- Registration number
- Current category
- Suggested category
- Reasoning

### 4. Add a state/plant location column
If you know the manufacturing location (state, city) for an EPD, this is valuable data. Submit a PR adding a `plant_state` column for any EPDs you have verified data for.

---

## CSV schema (for new rows)

Copy an existing row from `india_epds.csv` as a template. Key rules:

**`material_category`** — must be one of these exact values:
```
Acoustic & Insulation
Aggregate & Stone
Aluminium
Brick & Masonry
Building (Whole)
Chemicals & Waterproofing
Concrete & Cement
Electrical & Electronics
Fibre Cement & Boards
Flooring & Surfaces
Furniture & Fittings
Glass
Gypsum & Plasterboard
Insulation
Paint & Coating
Plastic & Polymer
Refractories
Rubber & Tyres
Solar & Energy
Steel & Metal
Timber & Wood
```

**`gwp_unit`** — must be one of these canonical forms:
```
kg CO2eq/kg
kg CO2eq/tonne
kg CO2eq/m²
kg CO2eq/m³
kg CO2eq/m
kg CO2eq/Wp
kg CO2eq/g
kg CO2eq/piece
kg CO2eq/unit
```

**`extraction_confidence`** — use `HIGH` if you read the value directly from a table, `MEDIUM` if there was ambiguity.

**`carbon_negative`** — `True` if `gwp_a1a3` < 0, else `False`

**`is_expired`** — `True` if `valid_until` < 2026, else `False`

**`is_industrial_equipment`** — `True` if `gwp_a1a3` > 1,000,000, else `False`

---

## Submitting a PR

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/open-epd-india.git
cd open-epd-india

# Make your changes to india_epds.csv
# Then commit and push:
git add india_epds.csv
git commit -m "Add EPD-IES-XXXXXXX: [product name]"
git push origin main

# Open a Pull Request on GitHub
```

---

## What we don't accept

- EPDs from non-Indian manufacturers (out of scope)
- GWP values without a source EPD link
- Changes to `index.html` or `fetch_india_epds.py` without discussion in an Issue first

---

## Contact

Raise an Issue on GitHub or reach out via [LinkedIn](https://www.linkedin.com/in/gokulkrishnatb/).

*Maintained by [Gokul Krishna T.B.](https://tbgokulkrishna.wordpress.com)*
