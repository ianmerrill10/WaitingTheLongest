import logging
import random
import requests
from datetime import datetime
from slugify import slugify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000/api/articles"

# Pre-defined topics to simulate "AI Generation" for the demo
# In a real production environment, this would connect to an LLM API.
TOPICS = [
    # Adoption Guides
    {"title": "The First 24 Hours: A Survival Guide", "category": "Adoption Guides", "content": "The first 24 hours with a new pet are critical..."},
    {"title": "Puppy Proofing Your Apartment", "category": "Adoption Guides", "content": "Living in an apartment requires special puppy proofing..."},
    {"title": "Introducing a Rescue Dog to Cats", "category": "Adoption Guides", "content": "Slow and steady wins the race when introducing dogs and cats..."},
    {"title": "Adopting a Senior Dog: What to Expect", "category": "Adoption Guides", "content": "Senior dogs offer a unique and rewarding adoption experience..."},
    
    # Breed Information
    {"title": "The Truth About Pit Bulls", "category": "Breed Information", "content": "Pit Bulls are often misunderstood. Here are the facts..."},
    {"title": "Herding Breeds: Are They Right for You?", "category": "Breed Information", "content": "Herding breeds like Collies and Shepherds are intelligent but demanding..."},
    {"title": "Small Dog Syndrome: Fact or Fiction?", "category": "Breed Information", "content": "Small dogs often get a bad rap for being yappy..."},
    {"title": "Gentle Giants: Large Breed Care", "category": "Breed Information", "content": "Great Danes and Mastiffs are big dogs with big hearts..."},

    # Training & Behavior
    {"title": "Potty Training in 3 Days", "category": "Training & Behavior", "content": "While ambitious, potty training can be jumpstarted in a weekend..."},
    {"title": "Stop the Barking: Positive Reinforcement", "category": "Training & Behavior", "content": "Barking is communication, but excessive barking can be managed..."},
    {"title": "Leash Reactivity Explained", "category": "Training & Behavior", "content": "Does your dog lunge at other dogs on walks? This is reactivity..."},
    {"title": "Clicker Training for Beginners", "category": "Training & Behavior", "content": "Clicker training is a powerful positive reinforcement method..."},

    # Health & Wellness
    {"title": "The Dangers of Xylitol", "category": "Health & Wellness", "content": "Xylitol is a common sweetener that is deadly to dogs..."},
    {"title": "Flea and Tick Prevention 101", "category": "Health & Wellness", "content": "Parasites are more than just a nuisance; they carry disease..."},
    {"title": "Dental Health for Dogs", "category": "Health & Wellness", "content": "Bad breath isn't normal. Dental disease is common in pets..."},
    {"title": "Recognizing Heat Stroke", "category": "Health & Wellness", "content": "Heat stroke can happen quickly. Know the signs..."},
]

class KnowledgeAgent:
    def __init__(self):
        self.categories = [
            "Adoption Guides",
            "Breed Information",
            "Training & Behavior",
            "Health & Wellness"
        ]

    def get_existing_articles(self):
        try:
            response = requests.get(API_URL)
            if response.status_code == 200:
                return response.json().get("items", [])
            return []
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}")
            return []

    def determine_needed_category(self, articles):
        """Find the category with the fewest articles to ensure even distribution."""
        counts = {cat: 0 for cat in self.categories}
        for article in articles:
            if article['category'] in counts:
                counts[article['category']] += 1
        
        # Find category with minimum count
        min_cat = min(counts, key=counts.get)
        logger.info(f"Category distribution: {counts}. Target category: {min_cat}")
        return min_cat

    def generate_article(self, category):
        """
        Selects a topic from the pre-defined list that matches the category
        and hasn't been used yet.
        """
        # In a real agent, this would call an LLM to generate fresh content
        # based on the category.
        
        # Filter topics by category
        candidates = [t for t in TOPICS if t['category'] == category]
        
        # Simple random selection for demo purposes
        # Ideally we would check against existing titles to avoid duplicates
        if not candidates:
            logger.warning(f"No topics found for category {category}")
            return None
            
        topic = random.choice(candidates)
        
        # Generate a slug
        slug = slugify(topic['title'])
        
        return {
            "title": topic['title'],
            "category": topic['category'],
            "content": f"<h2>{topic['title']}</h2><p>{topic['content']}</p><p><em>Generated by Knowledge Agent on {datetime.now().strftime('%Y-%m-%d')}</em></p>",
            "slug": slug,
            "read_time": f"{random.randint(3, 8)} min read"
        }

    def run(self):
        logger.info("Knowledge Agent starting...")
        
        existing = self.get_existing_articles()
        target_category = self.determine_needed_category(existing)
        
        new_article_data = self.generate_article(target_category)
        
        if new_article_data:
            # Check if slug exists (simple check)
            if any(a['slug'] == new_article_data['slug'] for a in existing):
                logger.info(f"Article '{new_article_data['title']}' already exists. Skipping.")
                return

            try:
                response = requests.post(API_URL, json=new_article_data)
                if response.status_code == 200:
                    logger.info(f"Successfully created article: {new_article_data['title']}")
                else:
                    logger.error(f"Failed to create article: {response.text}")
            except Exception as e:
                logger.error(f"Error posting article: {e}")
        else:
            logger.info("No article generated.")

if __name__ == "__main__":
    agent = KnowledgeAgent()
    agent.run()
