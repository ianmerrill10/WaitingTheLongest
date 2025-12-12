# Data Inventory

**Last Updated:** 2025-12-11
**Total Unique Organizations:** ~28,000-32,000 (estimated after deduplication)
**Total Raw Records:** ~57,600

---

## Primary Data Sources

### 1. IRS Animal Organizations (`irs_animal_orgs.json`)

| Metric | Value |
|--------|-------|
| **Records** | 40,085 |
| **File Size** | 20.5 MB |
| **Source** | IRS 501(c)(3) Exempt Organizations |
| **Coverage** | 58 states/territories |

This is the most comprehensive dataset containing ALL registered animal-related nonprofits in the US. Each record includes:
- EIN (tax ID)
- Organization name
- Address (street, city, state, zip)
- NTEE code (nonprofit classification)
- Financial data (income, revenue, assets)
- Contact info (when available)

**Top 10 States:**

| State | Count |
|-------|-------|
| CA | 4,663 |
| TX | 3,255 |
| FL | 3,113 |
| NY | 1,964 |
| PA | 1,535 |
| NC | 1,414 |
| OH | 1,330 |
| AZ | 1,198 |
| VA | 1,150 |
| IL | 1,085 |

---

### 2. RescueGroups.org (`rescuegroups_orgs.json`)

| Metric | Value |
|--------|-------|
| **Records** | 5,050 |
| **File Size** | 3.6 MB |
| **Source** | RescueGroups.org API |
| **Coverage** | Active rescue organizations |

Contains organizations actively listing animals on RescueGroups.org platform.

---

### 3. Best Friends Network (`bf_network_orgs.json` / `bf_network_orgs.csv`)

| Metric | Value |
|--------|-------|
| **Records** | 6,012 |
| **File Size** | 2.0 MB (JSON) / 1.1 MB (CSV) |
| **Source** | Best Friends Animal Society Partner Directory |
| **Coverage** | Network partner organizations |

Organizations partnered with Best Friends Animal Society.

---

### 4. Shelters Backup (`shelters_backup.json`)

| Metric | Value |
|--------|-------|
| **Records** | 6,462 |
| **File Size** | 2.6 MB |
| **Source** | Deduplicated aggregation |
| **Coverage** | Verified active shelters |

Deduplicated list of verified, active animal shelters.

---

## Derived/Processed Data

### Master Lists (`master_lists/`)

| File | Records | Size | Description |
|------|---------|------|-------------|
| `orgs_by_state.json` | 40,085 | 29.4 MB | IRS data organized by state |
| `master_addresses.json` | 40,060 | 7.1 MB | Extracted addresses for geocoding |
| `master_addresses.csv` | 40,060 | 3.1 MB | CSV version for import |
| `summary_stats.json` | - | 15.2 MB | Statistical summaries |

### Collected Shelters (`collected_shelters/`)

50 state-specific JSON files with curated shelter data:
- Total: 1,170 organizations
- Each file: `{STATE}_shelters.json`
- Notable: Maine has 159 organizations (most per state in this set)

### Master Shelter Database (`master_shelter_database.json`)

| Metric | Value |
|--------|-------|
| **Records** | 1,170 |
| **File Size** | 0.6 MB |
| **Purpose** | Curated, verified organizations |

---

## Supplementary Data

### State-Specific Files

| File | Records | Description |
|------|---------|-------------|
| `florida_rescues.csv` | 122 | Florida rescue organizations |
| `maryland_rescues.csv` | 203 | Maryland rescue organizations |
| `shelters.csv` | 368 | General shelter list |
| `nj_shelters.txt` | - | New Jersey shelters |
| `oregon_rescues.txt` | - | Oregon rescue organizations |
| `ri_animal_welfare_report.txt` | - | Rhode Island welfare report |

### Reference Data

| File | Description |
|------|-------------|
| `dog_breeds.json` | 206 KB - Dog breed reference data |
| `akc_rescue_network.txt` | AKC rescue network organizations |
| `national_registry_report.txt` | National registry summary |

---

## Data Quality Notes

1. **Duplicates**: Organizations may appear in multiple sources. The IRS dataset is canonical for nonprofit status.

2. **Contact Info**: Many IRS records lack email/phone/website. Best Friends and RescueGroups have better contact coverage.

3. **Active Status**: IRS data includes inactive organizations. Shelters_backup.json is filtered for active only.

4. **Geographic Coverage**: All 50 US states plus DC, Puerto Rico, Virgin Islands, Guam, and other territories.

---

## Usage

### Loading IRS Data
```python
import json
with open('irs_animal_orgs.json', 'r') as f:
    orgs = json.load(f)
print(f"Loaded {len(orgs)} organizations")
```

### Ingesting Shelters
```bash
cd backend
python tools/ingest_shelters.py
```

---

## For AI Agents

When working with shelter data:
1. Use `irs_animal_orgs.json` for comprehensive nonprofit lookup
2. Use `shelters_backup.json` for verified active shelters
3. Use state files in `collected_shelters/` for per-state queries
4. Update this file when adding new data sources
