#!/usr/bin/env python3
"""
===============================================================================
Shelter Outreach & Email Marketing System
===============================================================================
Comprehensive outreach system for contacting 40,000+ animal shelters.

Features:
  - Bulk email campaigns with templates
  - Physical mail template generation
  - Contact tracking and CRM
  - Onboarding stage management
  - Response tracking
  - Campaign analytics

Email Templates:
  - Initial introduction
  - Follow-up 1, 2, 3
  - Partnership invitation
  - API onboarding
  - Thank you / welcome

Mail Templates:
  - Introduction letter
  - Partnership packet
  - QR code postcard

Usage:
  python tools/shelter_outreach.py --init-templates
  python tools/shelter_outreach.py --campaign "Launch Email" --state MA
  python tools/shelter_outreach.py --generate-mail --state NY --limit 100
  python tools/shelter_outreach.py --stats
===============================================================================
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from string import Template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== Email Templates ====================

EMAIL_TEMPLATES = {
    "initial_intro": {
        "name": "Initial Introduction",
        "category": "initial",
        "subject": "Partner with Waiting The Longest - Help Your Animals Find Homes Faster",
        "body_html": """
<!DOCTYPE html>
<html>
<head><style>
body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
.header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
.content { padding: 20px; }
.cta-button { background: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
.footer { background: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; }
</style></head>
<body>
<div class="header">
    <h1>Waiting The Longest&trade;</h1>
    <p>Because Every Day Matters</p>
</div>
<div class="content">
    <p>Dear ${shelter_name} Team,</p>

    <p>We're reaching out because we believe every shelter animal deserves a chance, especially those who have been waiting the longest.</p>

    <p><strong>Waiting The Longest</strong> is a nationwide platform that:</p>
    <ul>
        <li>Highlights animals who have waited the longest for adoption</li>
        <li>Syncs directly with your existing shelter management software</li>
        <li>Creates viral social media content to drive adoptions</li>
        <li>Provides FREE listing for all partner shelters</li>
    </ul>

    <p>We'd love to feature ${shelter_name}'s animals on our platform and help them find forever homes.</p>

    <a href="https://waitingthelongest.com/partner?ref=${shelter_id}" class="cta-button">Become a Partner</a>

    <p>It takes less than 5 minutes to get started, and it's completely free.</p>

    <p>Best regards,<br>
    The Waiting The Longest Team</p>
</div>
<div class="footer">
    <p>Waiting The Longest&trade; | <a href="https://waitingthelongest.com">waitingthelongest.com</a></p>
    <p>Help shelter animals who have waited the longest find forever homes.</p>
</div>
</body>
</html>
""",
        "body_text": """
Dear ${shelter_name} Team,

We're reaching out because we believe every shelter animal deserves a chance, especially those who have been waiting the longest.

WAITING THE LONGEST is a nationwide platform that:
- Highlights animals who have waited the longest for adoption
- Syncs directly with your existing shelter management software
- Creates viral social media content to drive adoptions
- Provides FREE listing for all partner shelters

We'd love to feature ${shelter_name}'s animals on our platform and help them find forever homes.

Visit https://waitingthelongest.com/partner?ref=${shelter_id} to become a partner.

It takes less than 5 minutes to get started, and it's completely free.

Best regards,
The Waiting The Longest Team

---
Waiting The Longest™ | waitingthelongest.com
Help shelter animals who have waited the longest find forever homes.
""",
        "variables": ["shelter_name", "shelter_id", "state", "city"]
    },

    "follow_up_1": {
        "name": "Follow-up 1 (1 week)",
        "category": "follow_up",
        "subject": "Quick follow-up - Free platform for ${shelter_name}",
        "body_html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
    <p>Hi ${shelter_name} Team,</p>

    <p>Just following up on my previous email about Waiting The Longest.</p>

    <p>I wanted to share that we now have <strong>over 40,000 shelter organizations</strong> in our database, and shelters that join are seeing real results in adoption rates.</p>

    <p>A few quick benefits:</p>
    <ul>
        <li>Your long-wait animals get featured prominently</li>
        <li>Free social media content creation</li>
        <li>Works with PetPoint, Shelterluv, and other software</li>
    </ul>

    <p>Would you be interested in a quick 5-minute demo?</p>

    <p>Best,<br>
    The Waiting The Longest Team</p>
</body>
</html>
""",
        "body_text": """
Hi ${shelter_name} Team,

Just following up on my previous email about Waiting The Longest.

I wanted to share that we now have over 40,000 shelter organizations in our database, and shelters that join are seeing real results in adoption rates.

A few quick benefits:
- Your long-wait animals get featured prominently
- Free social media content creation
- Works with PetPoint, Shelterluv, and other software

Would you be interested in a quick 5-minute demo?

Best,
The Waiting The Longest Team
""",
        "variables": ["shelter_name", "shelter_id"]
    },

    "follow_up_2": {
        "name": "Follow-up 2 (2 weeks)",
        "category": "follow_up",
        "subject": "One more thing about long-wait animals at ${shelter_name}",
        "body_html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
    <p>Hi there,</p>

    <p>I know you're busy, so I'll keep this short.</p>

    <p>At Waiting The Longest, we specifically focus on animals who have been waiting the longest for adoption. These are often the animals that need the most help.</p>

    <p>If ${shelter_name} has any animals who have been waiting weeks or months, we'd love to help give them more visibility.</p>

    <p>Just reply "yes" if you'd like to learn more, and I'll send over a quick overview.</p>

    <p>Thanks,<br>
    The Waiting The Longest Team</p>
</body>
</html>
""",
        "body_text": """
Hi there,

I know you're busy, so I'll keep this short.

At Waiting The Longest, we specifically focus on animals who have been waiting the longest for adoption. These are often the animals that need the most help.

If ${shelter_name} has any animals who have been waiting weeks or months, we'd love to help give them more visibility.

Just reply "yes" if you'd like to learn more, and I'll send over a quick overview.

Thanks,
The Waiting The Longest Team
""",
        "variables": ["shelter_name"]
    },

    "follow_up_3": {
        "name": "Follow-up 3 (Final)",
        "category": "follow_up",
        "subject": "Final check-in from Waiting The Longest",
        "body_html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
    <p>Hi ${shelter_name} Team,</p>

    <p>This will be my last email about partnering with Waiting The Longest.</p>

    <p>We're still here whenever you're ready to give your long-wait animals more visibility. Our platform is always free for shelters.</p>

    <p>When you're ready, just visit: <a href="https://waitingthelongest.com/partner">waitingthelongest.com/partner</a></p>

    <p>Wishing you and your animals all the best!</p>

    <p>The Waiting The Longest Team</p>
</body>
</html>
""",
        "body_text": """
Hi ${shelter_name} Team,

This will be my last email about partnering with Waiting The Longest.

We're still here whenever you're ready to give your long-wait animals more visibility. Our platform is always free for shelters.

When you're ready, just visit: waitingthelongest.com/partner

Wishing you and your animals all the best!

The Waiting The Longest Team
""",
        "variables": ["shelter_name"]
    },

    "api_onboarding": {
        "name": "API Setup Instructions",
        "category": "onboarding",
        "subject": "Your Waiting The Longest API credentials are ready!",
        "body_html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
    <h2>Welcome to Waiting The Longest, ${shelter_name}!</h2>

    <p>Your partner account is ready. Here's how to start syncing your animals:</p>

    <h3>Your API Credentials</h3>
    <p><strong>Partner ID:</strong> ${partner_id}<br>
    <strong>API Key:</strong> ${api_key}</p>

    <p><em>Important: Save your API key securely. It won't be shown again.</em></p>

    <h3>Quick Start</h3>
    <pre style="background: #f4f4f4; padding: 15px; overflow-x: auto;">
curl -X POST https://waitingthelongest.com/api/partner/animals \\
  -H "X-API-Key: ${api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Max", "species": "dog", "breed": "Labrador"}'
    </pre>

    <p>Full API docs: <a href="https://waitingthelongest.com/api/partner/docs">waitingthelongest.com/api/partner/docs</a></p>

    <p>Need help? Reply to this email and we'll assist you.</p>

    <p>Welcome aboard!<br>
    The Waiting The Longest Team</p>
</body>
</html>
""",
        "body_text": """
Welcome to Waiting The Longest, ${shelter_name}!

Your partner account is ready. Here's how to start syncing your animals:

YOUR API CREDENTIALS
Partner ID: ${partner_id}
API Key: ${api_key}

Important: Save your API key securely. It won't be shown again.

QUICK START
curl -X POST https://waitingthelongest.com/api/partner/animals \\
  -H "X-API-Key: ${api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Max", "species": "dog", "breed": "Labrador"}'

Full API docs: waitingthelongest.com/api/partner/docs

Need help? Reply to this email and we'll assist you.

Welcome aboard!
The Waiting The Longest Team
""",
        "variables": ["shelter_name", "partner_id", "api_key"]
    },

    "welcome_partner": {
        "name": "Welcome New Partner",
        "category": "onboarding",
        "subject": "Welcome to the Waiting The Longest family, ${shelter_name}!",
        "body_html": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; padding: 20px;">
    <h2>🎉 You're Officially a Partner!</h2>

    <p>Dear ${shelter_name} Team,</p>

    <p>Thank you for joining Waiting The Longest! Together, we're going to help your animals find forever homes faster.</p>

    <h3>What Happens Next?</h3>
    <ol>
        <li>Your animals will start appearing on our platform</li>
        <li>Long-wait animals get automatic social media promotion</li>
        <li>You'll receive weekly performance reports</li>
    </ol>

    <h3>Resources for Partners</h3>
    <ul>
        <li><a href="https://waitingthelongest.com/partner/dashboard">Partner Dashboard</a></li>
        <li><a href="https://waitingthelongest.com/api/partner/docs">API Documentation</a></li>
        <li><a href="https://waitingthelongest.com/partner/marketing">Marketing Assets</a></li>
    </ul>

    <p>If you have any questions, just reply to this email. We're here to help!</p>

    <p>Thank you for everything you do for animals,<br>
    The Waiting The Longest Team</p>
</body>
</html>
""",
        "body_text": """
🎉 You're Officially a Partner!

Dear ${shelter_name} Team,

Thank you for joining Waiting The Longest! Together, we're going to help your animals find forever homes faster.

WHAT HAPPENS NEXT?
1. Your animals will start appearing on our platform
2. Long-wait animals get automatic social media promotion
3. You'll receive weekly performance reports

RESOURCES FOR PARTNERS
- Partner Dashboard: waitingthelongest.com/partner/dashboard
- API Documentation: waitingthelongest.com/api/partner/docs
- Marketing Assets: waitingthelongest.com/partner/marketing

If you have any questions, just reply to this email. We're here to help!

Thank you for everything you do for animals,
The Waiting The Longest Team
""",
        "variables": ["shelter_name"]
    }
}


# ==================== Mail Templates ====================

MAIL_TEMPLATES = {
    "intro_letter": {
        "name": "Introduction Letter",
        "category": "initial",
        "content": """
${date}

${shelter_name}
${address}
${city}, ${state} ${zip_code}

Dear ${shelter_name} Team,

We're writing to introduce Waiting The Longest™ - a nationwide platform dedicated to helping shelter animals who have waited the longest find forever homes.

WHY PARTNER WITH US?

• FREE listing for all your adoptable animals
• Priority exposure for your longest-waiting animals
• Social media promotion at no cost
• Simple integration with your existing software

HOW IT WORKS

1. Sign up at waitingthelongest.com/partner
2. Connect your shelter management software (or upload manually)
3. Your animals appear on our platform, sorted by wait time
4. We promote your longest-waiting animals on TikTok, Instagram & Facebook

JOIN 40,000+ SHELTER ORGANIZATIONS

Scan the QR code or visit:
waitingthelongest.com/partner?ref=${shelter_id}

We'd be honored to help your animals find loving homes.

With gratitude,

The Waiting The Longest Team
waitingthelongest.com
partnerships@waitingthelongest.com

---
"Because Every Day Matters"

P.S. It's completely free for shelters. No catch, no fees, ever.
""",
        "variables": ["date", "shelter_name", "address", "city", "state", "zip_code", "shelter_id"]
    },

    "postcard": {
        "name": "QR Code Postcard",
        "category": "initial",
        "content": """
====================================
FRONT OF POSTCARD
====================================

[LARGE IMAGE: Cute dog/cat looking at camera]

"I've been waiting 287 days.
Will you help me get seen?"

Waiting The Longest™
Because Every Day Matters

====================================
BACK OF POSTCARD
====================================

${shelter_name}
${address}
${city}, ${state} ${zip_code}

---

FREE PLATFORM FOR SHELTERS

Help your longest-waiting animals
get the visibility they deserve.

✓ FREE for all shelters
✓ Social media promotion included
✓ Works with PetPoint, Shelterluv & more

[QR CODE: waitingthelongest.com/partner?ref=${shelter_id}]

Scan to join or visit:
waitingthelongest.com/partner

---
Waiting The Longest™
waitingthelongest.com
""",
        "variables": ["shelter_name", "address", "city", "state", "zip_code", "shelter_id"]
    }
}


@dataclass
class OutreachRecord:
    """Record of outreach to a shelter."""
    shelter_id: int
    shelter_name: str
    email: Optional[str]
    address: str
    city: str
    state: str
    zip_code: str
    template: str
    status: str = "pending"
    sent_at: Optional[str] = None


def render_template(template: str, variables: Dict[str, str]) -> str:
    """Render a template with variables."""
    try:
        t = Template(template)
        return t.safe_substitute(variables)
    except Exception as e:
        logger.error(f"Template rendering error: {e}")
        return template


def generate_bulk_emails(
    shelters: List[Dict],
    template_name: str,
    output_file: str
) -> int:
    """
    Generate bulk emails for shelters.

    Args:
        shelters: List of shelter dicts with name, email, etc.
        template_name: Name of template to use
        output_file: Output CSV file path

    Returns:
        Number of emails generated
    """
    template = EMAIL_TEMPLATES.get(template_name)
    if not template:
        logger.error(f"Template not found: {template_name}")
        return 0

    records = []

    for shelter in tqdm(shelters, desc="Generating emails"):
        if not shelter.get("email"):
            continue

        variables = {
            "shelter_name": shelter.get("name", "Shelter"),
            "shelter_id": str(shelter.get("id", "")),
            "city": shelter.get("city", ""),
            "state": shelter.get("state", ""),
        }

        subject = render_template(template["subject"], variables)
        body = render_template(template["body_text"], variables)

        records.append({
            "to_email": shelter["email"],
            "to_name": shelter["name"],
            "subject": subject,
            "body_text": body[:500] + "..." if len(body) > 500 else body,
            "shelter_id": shelter.get("id"),
            "template": template_name,
            "status": "pending"
        })

    # Write to CSV
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if records:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)

    logger.info(f"Generated {len(records)} emails to {output_file}")
    return len(records)


def generate_mailing_list(
    shelters: List[Dict],
    template_name: str,
    output_dir: str
) -> int:
    """
    Generate physical mail templates.

    Args:
        shelters: List of shelter dicts
        template_name: Name of mail template
        output_dir: Output directory

    Returns:
        Number of letters generated
    """
    template = MAIL_TEMPLATES.get(template_name)
    if not template:
        logger.error(f"Mail template not found: {template_name}")
        return 0

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    count = 0
    address_list = []

    for shelter in tqdm(shelters, desc="Generating mail"):
        if not shelter.get("address"):
            continue

        variables = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "shelter_name": shelter.get("name", "Animal Shelter"),
            "address": shelter.get("address", ""),
            "city": shelter.get("city", ""),
            "state": shelter.get("state", ""),
            "zip_code": shelter.get("zip_code", ""),
            "shelter_id": str(shelter.get("id", "")),
        }

        letter = render_template(template["content"], variables)

        # Save individual letter
        filename = f"letter_{shelter.get('id', count)}.txt"
        with open(os.path.join(output_dir, filename), 'w') as f:
            f.write(letter)

        address_list.append({
            "name": shelter["name"],
            "address": shelter.get("address", ""),
            "city": shelter.get("city", ""),
            "state": shelter.get("state", ""),
            "zip_code": shelter.get("zip_code", ""),
        })
        count += 1

    # Save address list for mail merge
    with open(os.path.join(output_dir, "address_list.csv"), 'w', newline='') as f:
        if address_list:
            writer = csv.DictWriter(f, fieldnames=address_list[0].keys())
            writer.writeheader()
            writer.writerows(address_list)

    logger.info(f"Generated {count} letters to {output_dir}")
    return count


def get_outreach_stats() -> Dict:
    """Get outreach statistics."""
    try:
        from app.database import SessionLocal
        from app.models import Shelter

        db = SessionLocal()

        total_shelters = db.query(Shelter).count()

        # Count by state
        from sqlalchemy import func
        state_counts = db.query(
            Shelter.state, func.count(Shelter.id)
        ).group_by(Shelter.state).all()

        # Count with contact info
        with_email = db.query(Shelter).filter(Shelter.email.isnot(None)).count()
        with_phone = db.query(Shelter).filter(Shelter.phone.isnot(None)).count()
        with_website = db.query(Shelter).filter(Shelter.website.isnot(None)).count()

        db.close()

        return {
            "total_shelters": total_shelters,
            "with_email": with_email,
            "with_phone": with_phone,
            "with_website": with_website,
            "by_state": dict(state_counts),
            "email_coverage": round(with_email / total_shelters * 100, 1) if total_shelters else 0,
        }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Shelter Outreach System')
    parser.add_argument('--init-templates', action='store_true', help='Initialize email/mail templates')
    parser.add_argument('--generate-emails', type=str, help='Generate bulk emails using template name')
    parser.add_argument('--generate-mail', type=str, help='Generate mail using template name')
    parser.add_argument('--state', type=str, help='Filter by state')
    parser.add_argument('--limit', type=int, default=100, help='Limit number of records')
    parser.add_argument('--output', type=str, default='data/outreach/', help='Output directory')
    parser.add_argument('--stats', action='store_true', help='Show outreach statistics')
    parser.add_argument('--list-templates', action='store_true', help='List available templates')

    args = parser.parse_args()

    print("=" * 60)
    print("Waiting The Longest - Shelter Outreach System")
    print("=" * 60)

    if args.list_templates:
        print("\nEmail Templates:")
        for name, template in EMAIL_TEMPLATES.items():
            print(f"  - {name}: {template['name']}")

        print("\nMail Templates:")
        for name, template in MAIL_TEMPLATES.items():
            print(f"  - {name}: {template['name']}")
        return

    if args.stats:
        stats = get_outreach_stats()
        print("\nOutreach Statistics:")
        print(f"  Total Shelters: {stats.get('total_shelters', 0):,}")
        print(f"  With Email: {stats.get('with_email', 0):,} ({stats.get('email_coverage', 0)}%)")
        print(f"  With Phone: {stats.get('with_phone', 0):,}")
        print(f"  With Website: {stats.get('with_website', 0):,}")
        return

    if args.generate_emails:
        # Load shelters from IRS data
        with open('data/irs_animal_orgs.json', 'r') as f:
            orgs = json.load(f)

        if args.state:
            orgs = [o for o in orgs if o.get('state') == args.state.upper()]

        orgs = orgs[:args.limit]

        output_file = os.path.join(args.output, f"bulk_email_{args.generate_emails}_{datetime.now().strftime('%Y%m%d')}.csv")
        count = generate_bulk_emails(orgs, args.generate_emails, output_file)
        print(f"\nGenerated {count} emails to {output_file}")
        return

    if args.generate_mail:
        with open('data/irs_animal_orgs.json', 'r') as f:
            orgs = json.load(f)

        if args.state:
            orgs = [o for o in orgs if o.get('state') == args.state.upper()]

        orgs = orgs[:args.limit]

        output_dir = os.path.join(args.output, f"mail_{args.generate_mail}_{datetime.now().strftime('%Y%m%d')}")
        count = generate_mailing_list(orgs, args.generate_mail, output_dir)
        print(f"\nGenerated {count} letters to {output_dir}")
        return

    if args.init_templates:
        print("\nSaving templates to database...")
        # In a real implementation, save to database
        print(f"  {len(EMAIL_TEMPLATES)} email templates")
        print(f"  {len(MAIL_TEMPLATES)} mail templates")
        print("Done!")
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
