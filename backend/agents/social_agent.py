import logging
from datetime import datetime

class SocialMediaAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_instagram_post(self, animal_data):
        """
        Generates an Instagram caption and hashtags.
        """
        self.logger.info(f"Generating Instagram post for {animal_data.get('name')}")
        
        # Placeholder for LLM integration
        caption = f"💔 {animal_data.get('name')} has been waiting {animal_data.get('days_waiting')} days.\n\n"
        caption += f"This {animal_data.get('breed')} is looking for a forever home in {animal_data.get('location')}.\n\n"
        caption += "Link in bio to adopt! 🐾"
        
        hashtags = "#adoptme #shelterdog #waitingthelongest #rescuedog"
        
        return {
            "platform": "instagram",
            "caption": caption,
            "hashtags": hashtags,
            "created_at": datetime.now().isoformat()
        }

    def generate_tweet(self, animal_data):
        """
        Generates a tweet (max 280 chars).
        """
        self.logger.info(f"Generating Tweet for {animal_data.get('name')}")
        
        # Placeholder for LLM integration
        text = f"URGENT: {animal_data.get('name')} has been waiting {animal_data.get('days_waiting')} days! 🚨\n\n"
        text += f"Help us find this {animal_data.get('breed')} a home. RT to save a life! 🔄\n\n"
        text += f"https://waitingthelongest.com/animal/{animal_data.get('id')}"
        
        return {
            "platform": "twitter",
            "text": text,
            "created_at": datetime.now().isoformat()
        }

    def generate_tiktok_script(self, animal_data):
        """
        Generates a script for a TikTok video.
        """
        self.logger.info(f"Generating TikTok script for {animal_data.get('name')}")
        
        # Placeholder for LLM integration
        script = f"""
        [Scene: Sad music playing, close up of {animal_data.get('name')}'s face]
        Text Overlay: Day {animal_data.get('days_waiting')} of waiting...
        
        [Scene: {animal_data.get('name')} playing or wagging tail]
        Voiceover: This is {animal_data.get('name')}. They are the sweetest {animal_data.get('breed')}.
        
        [Scene: Contact info]
        Text Overlay: Link in bio to adopt!
        """
        
        return {
            "platform": "tiktok",
            "script": script,
            "created_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    agent = SocialMediaAgent()
    print(agent.generate_tweet({"name": "Luna", "days_waiting": 500, "breed": "Pitbull", "id": 123}))
