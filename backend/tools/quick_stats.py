#!/usr/bin/env python3
"""Quick shelter stats for monitoring enrichment progress."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.database import SessionLocal, init_db
from app.models import Shelter

init_db()
db = SessionLocal()

total = db.query(Shelter).count()
e = db.query(Shelter).filter(Shelter.email != None, Shelter.email != '').count()
p = db.query(Shelter).filter(Shelter.phone != None, Shelter.phone != '').count()
fb = db.query(Shelter).filter(Shelter.facebook_url != None, Shelter.facebook_url != '').count()
ig = db.query(Shelter).filter(Shelter.instagram_url != None, Shelter.instagram_url != '').count()
tw = db.query(Shelter).filter(Shelter.twitter_url != None, Shelter.twitter_url != '').count()
tt = db.query(Shelter).filter(Shelter.tiktok_url != None, Shelter.tiktok_url != '').count()

print(f"Total: {total} | Email: {e} ({100*e/total:.1f}%) | Phone: {p} ({100*p/total:.1f}%) | FB: {fb} | IG: {ig} | TW: {tw} | TT: {tt}")
db.close()
