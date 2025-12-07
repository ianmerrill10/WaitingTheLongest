import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def fix_schema():
    columns_to_add = [
        ("facebook_url", "TEXT"),
        ("instagram_url", "TEXT"),
        ("twitter_url", "TEXT"),
        ("tiktok_url", "TEXT"),
        ("org_type", "VARCHAR(50)")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE shelters ADD COLUMN {col_name} {col_type}"))
                print(f"Added {col_name} column")
            except Exception as e:
                print(f"Column {col_name} might already exist or error: {e}")
        
        conn.commit()
    print("Schema fix completed.")

if __name__ == "__main__":
    fix_schema()
