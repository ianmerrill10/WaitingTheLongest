import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import SessionLocal
from app.models import Article
from datetime import datetime

def seed_article():
    db = SessionLocal()
    
    # Check if article exists
    existing = db.query(Article).filter(Article.slug == "first-30-days-checklist").first()
    if existing:
        print("Article already exists.")
        db.close()
        return

    article = Article(
        title="First 30 Days Checklist",
        slug="first-30-days-checklist",
        category="Adoption Guides",
        content="""
            <p>Bringing a new pet home is an exciting time, but it can also be stressful for both you and your new companion. The first 30 days are crucial for establishing a bond and setting the foundation for a happy life together.</p>
            
            <h2>Week 1: Decompression</h2>
            <p>Your new pet needs time to adjust. Keep things quiet and low-key. Don't invite all your friends over to meet them just yet. Let them explore their new environment at their own pace.</p>
            <ul>
                <li>Set up a safe space (crate or specific room)</li>
                <li>Establish a consistent routine for feeding and potty breaks</li>
                <li>Keep walks short and in quiet areas</li>
            </ul>

            <h2>Week 2: Routine & Bonding</h2>
            <p>Now that your pet is settling in, you can start to introduce more structure. Consistency is key to helping them feel secure.</p>
            <ul>
                <li>Start basic training sessions (sit, stay, come)</li>
                <li>Introduce more interactive toys</li>
                <li>Gradually increase exercise duration</li>
            </ul>
        """,
        read_time="5 min read",
        created_at=datetime.now(),
        is_published=True,
        views=0
    )
    db.add(article)
    db.commit()
    print("Article added successfully.")
    db.close()

if __name__ == "__main__":
    seed_article()
