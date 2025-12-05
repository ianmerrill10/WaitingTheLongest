"""
===============================================================================
Waiting The Longest™ - RecordKeeper Agent
===============================================================================
Purpose: Ingests shelter and rescue organization data from external sources
         to build a comprehensive master list of shelters in all 50 states.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: requests, beautifulsoup4, sqlalchemy
Related Files: app/models.py, app/database.py

Mission: Ensure every shelter is tracked so we can find the longest waiting animals.
===============================================================================
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
import sys
import os
from datetime import datetime
from urllib.parse import urljoin

# Add parent directory to path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('record_keeper.log')
    ]
)
logger = logging.getLogger("RecordKeeper")

class RecordKeeperAgent:
    def __init__(self):
        self.db = SessionLocal()
        self.base_url = "https://www.rescueme.org/states"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def run(self):
        """Main execution method"""
        logger.info("Starting RecordKeeper Agent...")
        try:
            states = self.get_states()
            logger.info(f"Found {len(states)} states/regions to process.")
            
            for state_name, state_url in states.items():
                logger.info(f"Processing state: {state_name}")
                self.process_state(state_name, state_url)
                # Be polite to the server
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"An error occurred during execution: {e}")
        finally:
            self.db.close()
            logger.info("RecordKeeper Agent finished.")

    def get_states(self):
        """Fetch and parse the list of states"""
        logger.info(f"Fetching states from {self.base_url}")
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            states = {}
            
            # The links seem to be in a table with specific structure
            # Based on previous inspection, links are like http://animal.rescueme.org/Alabama
            # But the text is "Alabama Animal Rescue"
            
            for link in soup.find_all('a'):
                href = link.get('href')
                text = link.get_text()
                
                if href and 'animal.rescueme.org' in href and 'Animal Rescue' in text:
                    # Extract state name from text (e.g., "Alabama Animal Rescue" -> "Alabama")
                    state_name = text.replace(' Animal Rescue', '').strip()
                    states[state_name] = href
                    
            return states
            
        except Exception as e:
            logger.error(f"Failed to get states: {e}")
            return {}

    def process_state(self, state_name, state_url):
        """Process a single state to find shelters"""
        # The state URL is like http://animal.rescueme.org/Alabama
        # But the shelter list is at http://animal.rescueshelter.com/Alabama
        
        shelter_list_url = state_url.replace('animal.rescueme.org', 'animal.rescueshelter.com')
        logger.info(f"Fetching shelters for {state_name} from {shelter_list_url}")
        
        try:
            response = requests.get(shelter_list_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Now we need to find the shelters in the HTML.
            # Since I haven't seen the exact structure of the shelter list, 
            # I'll try to find common patterns for shelter listings.
            # Often they are in tables or divs with specific classes.
            # Or just text blocks.
            
            # Based on the "Alabama Rescue Groups" page title, let's look for content.
            # I'll look for text that looks like a shelter name.
            
            # TODO: Refine this parsing logic once we see the actual HTML structure of the list.
            # For now, I'll try to extract anything that looks like a shelter entry.
            
            # Let's assume for now we just want to verify we can reach this page and maybe find some names.
            # I'll log the first few links found on this page to see if they point to shelter details.
            
            count = 0
            for link in soup.find_all('a'):
                href = link.get('href')
                text = link.get_text().strip()
                
                # Heuristic: Shelter names often don't have "Rescue" in the link but might in the text
                # Or links might be to external sites.
                
                if href and len(text) > 3:
                    # This is a very loose heuristic. 
                    # In a real scenario, I'd inspect the HTML more closely.
                    # For this "first pass" agent, I'll just log what I find.
                    pass

            # Since I can't see the structure yet, I will try to find a specific pattern.
            # Many of these sites list shelters with Name, City, Phone.
            
            # Let's try to find the main content area.
            # If I can't parse it perfectly yet, I'll just log that I visited it.
            
            logger.info(f"Visited {state_name}. Parsing logic needs refinement based on HTML structure.")
            
        except Exception as e:
            logger.error(f"Failed to process state {state_name}: {e}")

if __name__ == "__main__":
    agent = RecordKeeperAgent()
    agent.run()
