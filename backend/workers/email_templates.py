"""
Waiting The Longest™ - Email Templates
========================================
HTML email templates for various notifications.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class EmailTemplate:
    """Base email template structure."""
    subject: str
    html_body: str
    text_body: str


class EmailTemplates:
    """Collection of email templates for the application."""
    
    # Common styles used across templates
    COMMON_STYLES = """
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #2c5530 0%, #4a7c4e 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 28px; }
        .content { background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }
        .footer { background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #2c5530; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .button:hover { background: #4a7c4e; }
        .animal-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin: 15px 0; background: #fafafa; }
        .animal-card img { width: 100%; max-width: 200px; border-radius: 4px; }
        .days-waiting { color: #2c5530; font-weight: bold; font-size: 18px; }
        .highlight { background: #fff3cd; padding: 2px 6px; border-radius: 3px; }
    """
    
    @classmethod
    def newsletter_welcome(cls, name: Optional[str] = None) -> EmailTemplate:
        """Welcome email for new newsletter subscribers."""
        greeting = f"Hi {name}!" if name else "Hi there!"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><style>{cls.COMMON_STYLES}</style></head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🐾 Welcome to Waiting The Longest™</h1>
                </div>
                <div class="content">
                    <h2>{greeting}</h2>
                    <p>Thank you for subscribing to our newsletter! You'll now receive updates about:</p>
                    <ul>
                        <li>🕐 Animals who have been waiting the longest for their forever homes</li>
                        <li>❤️ Heartwarming adoption success stories</li>
                        <li>🏠 Tips for pet adoption and care</li>
                        <li>📰 News from our partner shelters</li>
                    </ul>
                    <p>Every animal deserves a loving home, and we're grateful you're joining us in this mission.</p>
                    <a href="https://waitingthelongest.com" class="button">Visit Our Website</a>
                    <p><strong>Did you know?</strong> The average shelter pet waits 3-4 weeks for adoption, but some wait months or even years. Your awareness helps!</p>
                </div>
                <div class="footer">
                    <p>Waiting The Longest™ | Giving overlooked pets a voice</p>
                    <p><a href="{{{{unsubscribe_url}}}}">Unsubscribe</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
{greeting}

Thank you for subscribing to Waiting The Longest™!

You'll now receive updates about:
- Animals who have been waiting the longest for their forever homes
- Heartwarming adoption success stories
- Tips for pet adoption and care
- News from our partner shelters

Every animal deserves a loving home, and we're grateful you're joining us in this mission.

Visit us: https://waitingthelongest.com

-- 
Waiting The Longest™
Giving overlooked pets a voice
        """
        
        return EmailTemplate(
            subject="Welcome to Waiting The Longest™ 🐾",
            html_body=html_body,
            text_body=text_body,
        )
    
    @classmethod
    def weekly_digest(
        cls,
        longest_waiting: List[Dict[str, Any]],
        total_animals: int,
        adoptions_this_week: int,
    ) -> EmailTemplate:
        """Weekly digest email with longest-waiting animals."""
        
        animal_cards = ""
        for animal in longest_waiting[:5]:
            animal_cards += f"""
            <div class="animal-card">
                <table width="100%"><tr>
                    <td width="200">
                        <img src="{animal.get('photo_url', 'https://waitingthelongest.com/placeholder.png')}" alt="{animal['name']}">
                    </td>
                    <td style="padding-left: 15px; vertical-align: top;">
                        <h3 style="margin: 0;">{animal['name']}</h3>
                        <p style="margin: 5px 0;">{animal.get('breed', 'Mixed')} • {animal.get('age', 'Unknown age')}</p>
                        <p class="days-waiting">Waiting {animal['days_waiting']} days</p>
                        <p style="margin: 5px 0;">{animal.get('shelter_name', 'Local Shelter')}</p>
                        <a href="https://waitingthelongest.com/animal/{animal['id']}" class="button" style="font-size: 14px; padding: 8px 16px;">Meet {animal['name']}</a>
                    </td>
                </tr></table>
            </div>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><style>{cls.COMMON_STYLES}</style></head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🐾 This Week's Longest Waiters</h1>
                    <p style="margin: 10px 0 0 0;">Your weekly update from Waiting The Longest™</p>
                </div>
                <div class="content">
                    <h2>These pets need your help</h2>
                    <p>Here are the animals who have been waiting the longest this week:</p>
                    
                    {animal_cards}
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    
                    <h3>📊 This Week by the Numbers</h3>
                    <ul>
                        <li>Total animals waiting: <strong>{total_animals:,}</strong></li>
                        <li>Adoptions this week: <strong>{adoptions_this_week}</strong> 🎉</li>
                    </ul>
                    
                    <p style="text-align: center;">
                        <a href="https://waitingthelongest.com" class="button">See All Animals</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Waiting The Longest™ | Giving overlooked pets a voice</p>
                    <p><a href="{{{{unsubscribe_url}}}}">Unsubscribe</a> | <a href="{{{{preferences_url}}}}">Email Preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        animal_text = "\n".join([
            f"- {a['name']} ({a.get('breed', 'Mixed')}) - Waiting {a['days_waiting']} days"
            for a in longest_waiting[:5]
        ])
        
        text_body = f"""
This Week's Longest Waiters
===========================

These pets need your help:

{animal_text}

This Week by the Numbers:
- Total animals waiting: {total_animals:,}
- Adoptions this week: {adoptions_this_week}

Visit https://waitingthelongest.com to see all animals.

-- 
Waiting The Longest™
Giving overlooked pets a voice
        """
        
        return EmailTemplate(
            subject=f"🐾 {longest_waiting[0]['name'] if longest_waiting else 'A pet'} has been waiting {longest_waiting[0]['days_waiting'] if longest_waiting else '?'} days",
            html_body=html_body,
            text_body=text_body,
        )
    
    @classmethod
    def adoption_celebration(
        cls,
        animal_name: str,
        days_waited: int,
        shelter_name: str,
    ) -> EmailTemplate:
        """Celebration email when an animal gets adopted."""
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><style>{cls.COMMON_STYLES}</style></head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                    <h1>🎉 {animal_name} Found a Home!</h1>
                </div>
                <div class="content" style="text-align: center;">
                    <h2>After {days_waited} days of waiting...</h2>
                    <p style="font-size: 48px;">🏠❤️🐾</p>
                    <p><strong>{animal_name}</strong> from <strong>{shelter_name}</strong> has been adopted!</p>
                    <p>This is what it's all about. Every share, every view, every bit of awareness helps animals like {animal_name} find their forever homes.</p>
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                    <p>Want to help more pets like {animal_name}?</p>
                    <a href="https://waitingthelongest.com" class="button">See Who's Still Waiting</a>
                </div>
                <div class="footer">
                    <p>Waiting The Longest™ | Giving overlooked pets a voice</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
🎉 {animal_name} Found a Home!

After {days_waited} days of waiting, {animal_name} from {shelter_name} has been adopted!

This is what it's all about. Every share, every view, every bit of awareness helps animals find their forever homes.

Want to help more pets? Visit https://waitingthelongest.com

-- 
Waiting The Longest™
        """
        
        return EmailTemplate(
            subject=f"🎉 {animal_name} found a home after {days_waited} days!",
            html_body=html_body,
            text_body=text_body,
        )
    
    @classmethod
    def urgent_alert(
        cls,
        animal: Dict[str, Any],
        reason: str = "needs immediate attention",
    ) -> EmailTemplate:
        """Urgent alert for at-risk animals."""
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><style>{cls.COMMON_STYLES}</style></head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);">
                    <h1>⚠️ Urgent: {animal['name']} Needs Help</h1>
                </div>
                <div class="content">
                    <div class="animal-card" style="border-color: #dc2626;">
                        <h2 style="margin-top: 0;">{animal['name']}</h2>
                        <p><strong>Reason:</strong> {reason}</p>
                        <p><strong>Waiting:</strong> <span class="days-waiting">{animal['days_waiting']} days</span></p>
                        <p><strong>Location:</strong> {animal.get('shelter_name', 'Local Shelter')}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="https://waitingthelongest.com/animal/{animal['id']}" class="button" style="background: #dc2626;">Help {animal['name']} Now</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Waiting The Longest™ | Giving overlooked pets a voice</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
⚠️ URGENT: {animal['name']} Needs Help

{animal['name']} {reason}.

Details:
- Waiting: {animal['days_waiting']} days
- Location: {animal.get('shelter_name', 'Local Shelter')}

Please visit: https://waitingthelongest.com/animal/{animal['id']}

-- 
Waiting The Longest™
        """
        
        return EmailTemplate(
            subject=f"⚠️ URGENT: {animal['name']} needs your help!",
            html_body=html_body,
            text_body=text_body,
        )
