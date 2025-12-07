import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

def migrate_db():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE shelters ADD COLUMN description TEXT"))
            print("Added description column")
        except Exception as e:
            print(f"Description column might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE shelters ADD COLUMN last_verified_at DATETIME"))
            print("Added last_verified_at column")
        except Exception as e:
            print(f"last_verified_at column might already exist: {e}")
            
        conn.commit()

if __name__ == "__main__":
    migrate_db()
