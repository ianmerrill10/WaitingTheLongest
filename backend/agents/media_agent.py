import logging
from datetime import datetime

class MediaAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_image_prompt(self, animal_data, style="realistic"):
        """
        Generates a prompt for an image generation model (e.g., DALL-E).
        """
        self.logger.info(f"Generating image prompt for {animal_data.get('name')}")
        
        prompt = f"A high-quality, {style} photo of a {animal_data.get('breed')} named {animal_data.get('name')}. "
        prompt += f"The dog looks happy and hopeful. Background is a sunny park. "
        prompt += "Professional photography, 4k, highly detailed."
        
        return {
            "prompt": prompt,
            "style": style,
            "created_at": datetime.now().isoformat()
        }

    def create_canva_template_data(self, animal_data):
        """
        Prepares data to be sent to a Canva template via API (conceptual).
        """
        self.logger.info(f"Preparing Canva data for {animal_data.get('name')}")
        
        # This would match the fields in a Canva Data Merge or API integration
        data = {
            "PetName": animal_data.get('name'),
            "DaysWaiting": f"{animal_data.get('days_waiting')} Days",
            "Breed": animal_data.get('breed'),
            "Location": f"{animal_data.get('city')}, {animal_data.get('state')}",
            "PhotoURL": animal_data.get('photo_url'),
            "CallToAction": "Adopt Me Today!",
            "WebsiteURL": "waitingthelongest.com"
        }
        
        return {
            "integration_type": "canva_data_merge",
            "data": data,
            "created_at": datetime.now().isoformat()
        }

    def generate_video_slideshow_script(self, animal_data):
        """
        Generates a script/timeline for a video slideshow generator.
        """
        self.logger.info(f"Generating video script for {animal_data.get('name')}")
        
        script = [
            {"time": "0:00", "image": "photo_1.jpg", "text": f"Meet {animal_data.get('name')}", "transition": "fade"},
            {"time": "0:05", "image": "photo_2.jpg", "text": f"Waiting {animal_data.get('days_waiting')} Days", "transition": "slide_left"},
            {"time": "0:10", "image": "photo_3.jpg", "text": "Loves Cuddles & Walks", "transition": "zoom_in"},
            {"time": "0:15", "image": "logo.jpg", "text": "Adopt at WaitingTheLongest.com", "transition": "fade_out"}
        ]
        
        return {
            "script": script,
            "duration": 20,
            "created_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    agent = MediaAgent()
    print(agent.create_canva_template_data({
        "name": "Max", 
        "days_waiting": 365, 
        "breed": "German Shepherd", 
        "city": "Denver", 
        "state": "CO",
        "photo_url": "http://example.com/max.jpg"
    }))
