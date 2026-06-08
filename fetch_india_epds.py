"""
Open India EPD Database — API Fetcher
======================================
Pulls all Indian EPDs from the Environdec External Downstream API
and saves them to india_epds.csv

Setup:
    1. Replace YOUR_API_KEY_HERE with your actual API key
    2. Run: python fetch_india_epds.py

Output: india_epds.csv
"""

import requests
import csv
import json
import time

# ── Configuration ──────────────────────────────────────────────────────────────
API_KEY     = "YOUR_API_KEY_HERE"
BASE_URL    = "https://epd-apim.environdec.com/stg/api/v1"
OUTPUT_FILE = "india_epds.csv"
PAGE_SIZE   = 100  # Max results per request

# ── CSV Fields ─────────────────────────────────────────────────────────────────
CSV_FIELDS = [
    "registration_number",
    "material_name",
    "material_category",
    "manufacturer_name",
    "country_of_origin",
    "gwp_a1a3",
    "gwp_unit",
    "declared_unit",
    "life_cycle_stages",
    "epd_programme_operator",
    "year_published",
    "valid_until",
    "epd_url",
    "raw_json"
]

HEADERS = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Accept": "application/json"
}

# ── Material category mapper ───────────────────────────────────────────────────
def categorize_material(name, description=""):
    """Map product name to a standard material category."""
    text = (name + " " + description).lower()
    if any(w in text for w in ["cement", "concrete", "mortar", "grout", "fly ash", "slag"]):
        return "Concrete & Cement"
    elif any(w in text for w in ["steel", "iron", "rebar", "reinforc", "metal"]):
        return "Steel & Metal"
    elif any(w in text for w in ["brick", "block", "masonry", "clay"]):
        return "Brick & Masonry"
    elif any(w in text for w in ["glass", "glazing"]):
        return "Glass"
    elif any(w in text for w in ["timber", "wood", "plywood", "lumber", "bamboo"]):
        return "Timber & Wood"
    elif any(w in text for w in ["ceramic", "tile", "porcelain", "sanitaryware"]):
        return "Ceramic & Tile"
    elif any(w in text for w in ["insulation", "rockwool", "glasswool", "foam"]):
        return "Insulation"
    elif any(w in text for w in ["aluminium", "aluminum"]):
        return "Aluminium"
    elif any(w in text for w in ["plastic", "polymer", "pvc", "hdpe", "pipe"]):
        return "Plastic & Polymer"
    elif any(w in text for w in ["paint", "coating", "varnish", "primer"]):
        return "Paint & Coating"
    elif any(w in text for w in ["aggregate", "stone", "sand", "gravel", "granite", "marble"]):
        return "Aggregate & Stone"
    elif any(w in text for w in ["gypsum", "plaster", "board"]):
        return "Gypsum & Board"
    else:
        return "Other"


# ── GWP extractor ──────────────────────────────────────────────────────────────
def extract_gwp(epd_data):
    """
    Try to extract A1-A3 GWP value from the EPD JSON.
    EPD data structures vary — this tries multiple known paths.
    """
    gwp_value = None
    gwp_unit  = None

    try:
        # Path 1: declarationContent > impacts
        impacts = epd_data.get("declarationContent", {}).get("impacts", [])
        for impact in impacts:
            indicator = str(impact.get("indicator", "")).upper()
            if "GWP" in indicator or "GLOBAL WARMING" in indicator.upper():
                modules = impact.get("modules", {})
                # Prefer A1-A3 combined, fall back to A1+A2+A3
                for key in ["A1-A3", "A1A2A3", "A1_A3"]:
                    if key in modules:
                        gwp_value = modules[key]
                        gwp_unit  = impact.get("unit", "kg CO2 eq")
                        break
                if gwp_value:
                    break

        # Path 2: top-level gwp field
        if gwp_value is None:
            gwp_value = epd_data.get("gwp") or epd_data.get("GWP")

        # Path 3: environmental indicators list
        if gwp_value is None:
            indicators = epd_data.get("environmentalIndicators", [])
            for ind in indicators:
                if "gwp" in str(ind.get("name", "")).lower():
                    gwp_value = ind.get("value")
                    gwp_unit  = ind.get("unit", "kg CO2 eq")
                    break

    except Exception:
        pass

    return gwp_value, gwp_unit


# ── Life cycle stage extractor ─────────────────────────────────────────────────
def extract_stages(epd_data):
    """Extract declared life cycle stages."""
    try:
        stages = epd_data.get("declaredLifeCycleStages", [])
        if stages:
            return ", ".join(stages)
        # Try alternative path
        scope = epd_data.get("declarationContent", {}).get("scope", "")
        if scope:
            return scope
    except Exception:
        pass
    return None


# ── Main fetcher ───────────────────────────────────────────────────────────────
def fetch_india_epds():
    """Fetch all Indian EPDs from the API with pagination."""

    if API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please replace YOUR_API_KEY_HERE with your actual API key")
        print("Find your key at: https://epd-apim.developer.azure-api.net/profile")
        return

    print("=" * 55)
    print("  Open India EPD Database — API Fetcher")
    print("=" * 55)
    print()

    all_epds   = []
    skip       = 0
    page       = 1
    total_seen = 0

    while True:
        print(f"Fetching page {page} (skip={skip}, take={PAGE_SIZE})...")

        params = {
            "SearchString": "India",
            "Skip": skip,
            "Take": PAGE_SIZE
        }

        try:
            response = requests.get(
                f"{BASE_URL}/EPDs",
                headers=HEADERS,
                params=params,
                timeout=30
            )

            if response.status_code == 401:
                print("ERROR: API key invalid or subscription not yet active.")
                print("Check your subscription status at the developer portal.")
                return

            if response.status_code == 403:
                print("ERROR: Access forbidden. Subscription may still be pending approval.")
                return

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                print(response.text[:500])
                return

            data = response.json()

            # Handle both list response and paginated object response
            if isinstance(data, list):
                epds = data
            elif isinstance(data, dict):
                epds = data.get("data", data.get("results", data.get("items", [])))
            else:
                epds = []

            if not epds:
                print(f"No more results at page {page}. Done.")
                break

            total_seen += len(epds)
            print(f"  Got {len(epds)} EPDs (total so far: {total_seen})")

            for epd in epds:
                row = process_epd(epd)
                if row:
                    all_epds.append(row)

            # If we got fewer results than page size, we're done
            if len(epds) < PAGE_SIZE:
                break

            skip += PAGE_SIZE
            page += 1
            time.sleep(0.3)  # Be respectful to the API

        except requests.exceptions.Timeout:
            print("ERROR: Request timed out. Check your internet connection.")
            break
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to API. Check your internet connection.")
            break
        except json.JSONDecodeError:
            print("ERROR: API returned invalid JSON.")
            print(response.text[:500])
            break

    # ── Filter for India only ──────────────────────────────────────────────────
    india_epds = [e for e in all_epds if is_indian_epd(e)]
    print(f"\nTotal fetched: {len(all_epds)}")
    print(f"Indian EPDs identified: {len(india_epds)}")

    if not india_epds:
        print("\nNo Indian EPDs found. The search may need adjustment.")
        print("Saving all results instead for manual review...")
        india_epds = all_epds

    # ── Save to CSV ────────────────────────────────────────────────────────────
    save_to_csv(india_epds)


def is_indian_epd(row):
    """Check if EPD is from India."""
    country = str(row.get("country_of_origin", "")).lower()
    manufacturer = str(row.get("manufacturer_name", "")).lower()
    return "india" in country or "india" in manufacturer


def process_epd(epd):
    """Extract structured fields from a single EPD JSON object."""
    try:
        # Registration number
        reg_num = (
            epd.get("registrationNumber") or
            epd.get("declarationNumber") or
            epd.get("id", "")
        )

        # Product name
        name = (
            epd.get("name") or
            epd.get("productName") or
            epd.get("declarationName", "Unknown")
        )

        # Manufacturer
        manufacturer = (
            epd.get("declaredBy") or
            epd.get("manufacturer") or
            epd.get("companyName") or
            epd.get("organizationName", "")
        )
        if isinstance(manufacturer, dict):
            manufacturer = manufacturer.get("name", "")

        # Country
        country = (
            epd.get("countryOfManufacture") or
            epd.get("country") or
            epd.get("geography", "")
        )
        if isinstance(country, dict):
            country = country.get("name", country.get("code", ""))

        # Declared unit
        declared_unit = (
            epd.get("declaredUnit") or
            epd.get("functionalUnit", "")
        )

        # Programme operator
        programme = (
            epd.get("programOperator") or
            epd.get("programmeOperator") or
            epd.get("programmeOperatorName", "International EPD System")
        )
        if isinstance(programme, dict):
            programme = programme.get("name", "")

        # Dates
        published = epd.get("publishedDate") or epd.get("validFrom", "")
        valid_until = epd.get("validUntil") or epd.get("expiryDate", "")

        # Extract year only from date strings
        if published and len(str(published)) >= 4:
            published = str(published)[:4]
        if valid_until and len(str(valid_until)) >= 4:
            valid_until = str(valid_until)[:4]

        # GWP
        gwp_value, gwp_unit = extract_gwp(epd)

        # Life cycle stages
        stages = extract_stages(epd)

        # Material category
        category = categorize_material(str(name))

        # EPD URL
        epd_url = (
            epd.get("url") or
            epd.get("pdfUrl") or
            f"https://www.environdec.com/library/epd/{reg_num}" if reg_num else ""
        )

        return {
            "registration_number": reg_num,
            "material_name":       name,
            "material_category":   category,
            "manufacturer_name":   manufacturer,
            "country_of_origin":   country,
            "gwp_a1a3":            gwp_value,
            "gwp_unit":            gwp_unit or "kg CO2 eq",
            "declared_unit":       declared_unit,
            "life_cycle_stages":   stages,
            "epd_programme_operator": programme,
            "year_published":      published,
            "valid_until":         valid_until,
            "epd_url":             epd_url,
            "raw_json":            json.dumps(epd)[:500]  # First 500 chars for debugging
        }

    except Exception as e:
        print(f"  Warning: Could not process EPD: {e}")
        return None


def save_to_csv(epds):
    """Save EPD list to CSV."""
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(epds)

    print(f"\n✓ Saved {len(epds)} EPDs to {OUTPUT_FILE}")
    print(f"\nSummary by category:")

    categories = {}
    for e in epds:
        cat = e.get("material_category", "Other")
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    fetch_india_epds()
