# Data Ingestion

This directory contains data files for ingestion.

## Shelters Data

1. Paste the CSV data into `shelters.csv`.
2. Ensure the headers match: `Number,State,State_Code,Organization_Name,Type,Email,Phone,Website,Address,City,Zip_Code,Description`
3. Run the ingestion script:
   ```bash
   cd backend
   python tools/ingest_shelters.py
   ```
