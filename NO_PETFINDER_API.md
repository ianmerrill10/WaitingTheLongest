# IMPORTANT: THERE IS NO PETFINDER API

**Date Added**: December 5, 2025
**Status**: PERMANENT POLICY

## Facts

1. **Petfinder does NOT have a public API.**
2. **Do NOT attempt to integrate with Petfinder API.**
3. **Do NOT write code that references "Petfinder API".**
4. **Do NOT suggest Petfinder as a data source for integration.**

## Historical Context

During development, there was confusion about Petfinder potentially having an API. After thorough investigation:

- Petfinder deprecated their public API years ago
- Their website uses JavaScript-rendered content that requires browser automation
- They actively block scraping attempts
- There is NO legitimate API endpoint available

## Approved Data Sources

Use these instead:

1. **RescueGroups.org** - Our primary data source with free API access
2. **Best Friends Network** - Scrape their public directory (we built a scraper)
3. **Individual shelter websites** - Direct contact info scraping
4. **State/county shelter registries** - Public government records

## DO NOT

- Reference Petfinder API in any code
- Attempt to scrape Petfinder.com
- Suggest Petfinder integration to the team
- Create functions expecting Petfinder API responses

This policy exists to prevent wasted development time on a non-existent integration.

---
*This file was created to prevent future confusion. It should NEVER be deleted.*
