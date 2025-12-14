"""
===============================================================================
Waiting The Longest™ - Email Templates
===============================================================================
Purpose: HTML email templates for newsletter and notification emails.
         Ensures consistent branding across all email communications.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class EmailTemplates:
    """HTML email templates for various campaigns."""
    
    # Brand colors
    PRIMARY_COLOR = "#2563EB"
    SECONDARY_COLOR = "#7C3AED"
    TEXT_COLOR = "#1F2937"
    TEXT_LIGHT = "#6B7280"
    BG_COLOR = "#F8FAFC"
    
    @classmethod
    def _base_template(cls, content: str, preview_text: str = "") -> str:
        """Wrap content in base email template."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Waiting The Longest™</title>
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse: collapse;}}
        .mso-line-height {{mso-line-height-rule: exactly;}}
    </style>
    <![endif]-->
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: {cls.BG_COLOR};
            color: {cls.TEXT_COLOR};
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        .header {{
            background: linear-gradient(135deg, {cls.PRIMARY_COLOR}, {cls.SECONDARY_COLOR});
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            color: #ffffff;
            margin: 0;
            font-size: 24px;
        }}
        .header p {{
            color: rgba(255,255,255,0.9);
            margin: 5px 0 0;
            font-size: 14px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: {cls.PRIMARY_COLOR};
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        .footer {{
            background-color: {cls.TEXT_COLOR};
            padding: 20px;
            text-align: center;
            color: rgba(255,255,255,0.8);
            font-size: 12px;
        }}
        .footer a {{
            color: rgba(255,255,255,0.8);
        }}
        .pet-card {{
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            overflow: hidden;
            margin: 15px 0;
        }}
        .pet-card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
        }}
        .pet-card-info {{
            padding: 15px;
        }}
        .pet-name {{
            font-size: 18px;
            font-weight: 600;
            margin: 0 0 5px;
        }}
        .days-badge {{
            display: inline-block;
            background-color: {cls.PRIMARY_COLOR};
            color: #ffffff;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div style="display:none;font-size:1px;color:#ffffff;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
        {preview_text}
    </div>
    <div class="email-container">
        <div class="header">
            <h1>Waiting The Longest™</h1>
            <p>Because Every Day Matters</p>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>
                <a href="{{{{unsubscribe_url}}}}">Unsubscribe</a> | 
                <a href="{{{{preferences_url}}}}">Email Preferences</a>
            </p>
            <p>© {datetime.now().year} Waiting The Longest™. All rights reserved.</p>
            <p style="font-size: 10px; margin-top: 10px;">
                As an Amazon Associate, we earn from qualifying purchases.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    @classmethod
    def weekly_newsletter(cls, animals: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
        """Generate weekly "Longest Waiting" newsletter."""
        
        # Build pet cards HTML
        pet_cards = ""
        for animal in animals[:6]:
            pet_cards += f"""
            <div class="pet-card">
                <img src="{animal.get('photo_url', '')}" alt="{animal.get('name', 'Pet')}">
                <div class="pet-card-info">
                    <p class="pet-name">{animal.get('name', 'Unknown')}</p>
                    <p style="color:{cls.TEXT_LIGHT};margin:5px 0;">{animal.get('breed', '')} • {animal.get('location', '')}</p>
                    <span class="days-badge">{animal.get('days_waiting', 0)} days waiting</span>
                    <p style="margin-top:10px;">
                        <a href="{animal.get('url', '#')}" class="button" style="font-size:14px;padding:8px 16px;">Meet {animal.get('name', 'Them')}</a>
                    </p>
                </div>
            </div>
            """
        
        content = f"""
            <h2 style="margin-top:0;">This Week's Longest Waiting Pets 🐾</h2>
            
            <p>These amazing animals have been patiently waiting for their forever homes. 
            Can you help them find the love they deserve?</p>
            
            <div style="background:{cls.BG_COLOR};padding:15px;border-radius:8px;margin:20px 0;">
                <p style="margin:0;"><strong>{stats.get('available_animals', 0)}</strong> animals waiting</p>
                <p style="margin:5px 0 0;"><strong>{stats.get('longest_wait_days', 0)}</strong> days longest wait</p>
            </div>
            
            {pet_cards}
            
            <p style="text-align:center;margin-top:30px;">
                <a href="https://waitingthelongest.com" class="button">See All Animals</a>
            </p>
            
            <hr style="border:none;border-top:1px solid #E2E8F0;margin:30px 0;">
            
            <h3>Why Adopt a Long-Waiting Pet?</h3>
            <ul style="color:{cls.TEXT_LIGHT};">
                <li>They're often overlooked simply because of age or color</li>
                <li>Shelter staff know their personalities well</li>
                <li>You're literally saving a life</li>
                <li>The bond you'll form is incredible</li>
            </ul>
        """
        
        return cls._base_template(
            content,
            f"🐾 {len(animals)} pets waiting {animals[0].get('days_waiting', 0)}+ days need you!"
        )
    
    @classmethod
    def success_story(cls, story: Dict[str, Any]) -> str:
        """Generate success story celebration email."""
        
        content = f"""
            <h2 style="margin-top:0;">🎉 Happy Tails: {story.get('pet_name', 'A Pet')} Found a Home!</h2>
            
            <div class="pet-card">
                <img src="{story.get('photo_url', '')}" alt="{story.get('pet_name', 'Pet')}">
                <div class="pet-card-info">
                    <p class="pet-name">{story.get('pet_name', 'Unknown')}</p>
                    <span class="days-badge">Waited {story.get('days_waited', 0)} days</span>
                </div>
            </div>
            
            <blockquote style="border-left:4px solid {cls.PRIMARY_COLOR};padding-left:15px;margin:20px 0;font-style:italic;color:{cls.TEXT_LIGHT};">
                "{story.get('story_text', '')[:300]}..."
            </blockquote>
            
            <p>After <strong>{story.get('days_waited', 0)} days</strong> of waiting, 
            {story.get('pet_name', 'this wonderful pet')} finally found their forever family!</p>
            
            <p>Stories like this remind us why we do what we do. Every adoption is a victory. 💕</p>
            
            <p style="text-align:center;margin-top:30px;">
                <a href="https://waitingthelongest.com/success-stories" class="button">Read More Stories</a>
            </p>
        """
        
        return cls._base_template(
            content,
            f"🎉 After {story.get('days_waited', 0)} days, {story.get('pet_name', 'a pet')} found their forever home!"
        )
    
    @classmethod
    def welcome_email(cls, subscriber_name: Optional[str] = None) -> str:
        """Generate welcome email for new subscribers."""
        
        greeting = f"Hi {subscriber_name}!" if subscriber_name else "Welcome!"
        
        content = f"""
            <h2 style="margin-top:0;">{greeting} Welcome to the Pack! 🐾</h2>
            
            <p>Thank you for joining Waiting The Longest™! You're now part of a community 
            dedicated to helping shelter animals who have waited the longest find loving homes.</p>
            
            <h3>What to Expect</h3>
            <ul style="color:{cls.TEXT_LIGHT};">
                <li><strong>Weekly Newsletter</strong> - Every Sunday, we'll send you the week's longest-waiting pets</li>
                <li><strong>Success Stories</strong> - Heartwarming adoption updates</li>
                <li><strong>Tips & Resources</strong> - Pet care advice and product recommendations</li>
            </ul>
            
            <p style="text-align:center;margin:30px 0;">
                <a href="https://waitingthelongest.com" class="button">Start Browsing Pets</a>
            </p>
            
            <hr style="border:none;border-top:1px solid #E2E8F0;margin:30px 0;">
            
            <p style="font-size:14px;color:{cls.TEXT_LIGHT};">
                <strong>Quick Tip:</strong> Favorite the pets you're interested in, 
                and we'll remind you if they're still waiting!
            </p>
        """
        
        return cls._base_template(
            content,
            "🐾 Welcome to Waiting The Longest! Let's find homes for shelter pets together."
        )
    
    @classmethod
    def still_waiting_reminder(cls, animal: Dict[str, Any], days_since_favorited: int) -> str:
        """Generate "still waiting" reminder for favorited animal."""
        
        content = f"""
            <h2 style="margin-top:0;">{animal.get('name', 'Your Favorite')} is Still Waiting 💔</h2>
            
            <p>You favorited {animal.get('name', 'this pet')} {days_since_favorited} days ago, 
            and they're still looking for their forever home.</p>
            
            <div class="pet-card">
                <img src="{animal.get('photo_url', '')}" alt="{animal.get('name', 'Pet')}">
                <div class="pet-card-info">
                    <p class="pet-name">{animal.get('name', 'Unknown')}</p>
                    <p style="color:{cls.TEXT_LIGHT};margin:5px 0;">{animal.get('breed', '')} • {animal.get('location', '')}</p>
                    <span class="days-badge">{animal.get('days_waiting', 0)} days waiting</span>
                </div>
            </div>
            
            <p><strong>Total wait:</strong> {animal.get('days_waiting', 0)} days</p>
            
            <p>Could you be the one to give {animal.get('name', 'them')} the happy ending they deserve?</p>
            
            <p style="text-align:center;margin-top:30px;">
                <a href="{animal.get('url', 'https://waitingthelongest.com')}" class="button">
                    Learn About {animal.get('name', 'This Pet')}
                </a>
            </p>
            
            <p style="text-align:center;color:{cls.TEXT_LIGHT};font-size:14px;margin-top:20px;">
                Not ready to adopt? Consider sharing {animal.get('name', 'their profile')} with friends!
            </p>
        """
        
        return cls._base_template(
            content,
            f"💔 {animal.get('name', 'Your favorite pet')} has been waiting {animal.get('days_waiting', 0)} days..."
        )
