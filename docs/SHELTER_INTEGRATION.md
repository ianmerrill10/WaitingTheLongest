# Shelter Integration Guide

Welcome! This guide explains how to get your shelter's animals featured on Waiting The Longest™.

## Overview

Waiting The Longest™ aggregates data from animal welfare networks to highlight animals who have been waiting the longest for adoption. By ensuring your shelter's data is properly listed, you can give your long-term residents the extra visibility they deserve.

## Data Sources

We currently pull data from:

### Primary Sources
- **RescueGroups** - Our primary data source
- **Best Friends Network** - For participating shelters

### Coming Soon
- Petfinder
- ASPCA Partner Network
- Direct API integration

## Getting Listed

### Option 1: RescueGroups (Recommended)

If your shelter uses RescueGroups:

1. **Ensure your account is active** at [rescuegroups.org](https://rescuegroups.org)
2. **Enable API access** in your organization settings
3. **Your animals will automatically appear** in our database within 24 hours

### Option 2: Contact Us

If you use a different shelter management system, contact us at shelters@waitingthelongest.com to discuss integration options.

## Optimizing Your Listings

### Photos
- **Use high-quality photos** - Clear, well-lit images get more attention
- **Show personality** - Action shots and play photos work great
- **Multiple angles** - Provide at least 2-3 photos per animal
- **Size**: Minimum 600x400 pixels recommended

### Descriptions
Write engaging descriptions that:
- Highlight the animal's personality
- Mention likes and dislikes
- Include relevant history (if appropriate)
- Avoid sad or desperate language
- Use positive, hopeful framing

**Example**:
> "Meet Buddy! This 5-year-old gentleman has been patiently waiting for his perfect match. Buddy loves morning walks, car rides, and curling up next to you on the couch. He's great with kids and other dogs, and his house-training is excellent. Could you be Buddy's happily ever after?"

### Accurate Data

- **Intake Date**: Enter the correct date the animal arrived at your shelter
- **Update promptly**: Mark animals as adopted as soon as possible
- **Species/Breed**: Be specific and accurate
- **Age**: Keep age categories consistent

## Best Practices

### 1. Regular Updates
- Update your listings at least weekly
- Remove adopted animals promptly
- Refresh photos periodically

### 2. Complete Profiles
Animals with complete profiles get more views:
- [ ] Name
- [ ] Species and breed
- [ ] Age
- [ ] Gender
- [ ] Size (for dogs)
- [ ] Description
- [ ] At least 2 photos
- [ ] Accurate intake date

### 3. Special Needs
Don't hide special needs—highlight them positively:
- "Looking for a patient family"
- "Would thrive as an only pet"
- "Special diet to keep him healthy"

## Data Syncing

### How It Works
1. We query the RescueGroups API every 6 hours
2. New animals are added to our database
3. Updated animals have their information refreshed
4. Animals marked as adopted are hidden from listings

### Wait Time Calculation
We calculate wait time from the intake date you provide. This means:
- Transfers should use their original intake date OR current shelter's intake date (your choice)
- Returns should use their new intake date
- Foster returns should maintain their original intake date

## Troubleshooting

### My animals aren't appearing
1. Check your RescueGroups account is active
2. Verify API access is enabled
3. Ensure animals are marked as "Available"
4. Wait 24 hours after making changes

### Photos aren't showing
- Ensure photos are publicly accessible URLs
- Check file format (JPEG, PNG, WebP supported)
- Verify URL doesn't require authentication

### Incorrect information
- Update the information in your shelter management system
- Changes will sync within 6 hours
- For urgent corrections, contact us

## Integration Benefits

### For Your Shelter
- **Increased visibility** for long-term residents
- **No cost** to participate
- **Automated syncing** - no manual updates needed
- **Analytics** - understand which animals get attention

### For Animals
- **Dedicated spotlight** for overlooked pets
- **Wider audience** beyond local area
- **Compelling presentation** optimized for adoption

## Contact Us

### General Inquiries
shelters@waitingthelongest.com

### Technical Support
support@waitingthelongest.com

### Partnership Opportunities
partners@waitingthelongest.com

---

## API Integration (Advanced)

For shelters that want direct integration, we offer a REST API.

### Authentication
Contact us for API credentials.

### Endpoints

```
POST /api/v1/shelters/register
POST /api/v1/animals/bulk-update
GET  /api/v1/animals/by-shelter/{shelter_id}
```

### Rate Limits
- 100 requests per minute
- Bulk updates: 1000 animals per request

### Sample Request

```json
POST /api/v1/animals/bulk-update
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "animals": [
    {
      "external_id": "A123456",
      "name": "Buddy",
      "species": "Dog",
      "breed": "Labrador Mix",
      "age": "Adult",
      "gender": "Male",
      "intake_date": "2023-01-15",
      "photo_urls": ["https://..."],
      "description": "Friendly lab mix..."
    }
  ]
}
```

Contact us for full API documentation.

---

Thank you for your dedication to helping animals find homes! 🐾
