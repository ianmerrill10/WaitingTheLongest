# Waiting The Longest™ - Copilot Agent Instructions for Shelter Data Collection

## Mission Statement

You are assisting with **Waiting The Longest™**, a platform dedicated to highlighting shelter animals who have been waiting the longest for adoption. Your mission is to help build a comprehensive database of non-profit animal adoption organizations across all 50 US states.

This data will be used to:
- Connect potential adopters with shelters near them
- Enrich animal records with shelter contact information
- Help animals find forever homes faster

## Data Collection Guidelines

### What to Collect

Collect information for **non-profit animal adoption organizations** including:
- Animal shelters (municipal, county, city)
- Rescue organizations
- Humane societies
- SPCAs (Society for the Prevention of Cruelty to Animals)
- ASPCA affiliates
- Animal sanctuaries
- Foster-based rescue networks
- Non-profit animal welfare organizations

### What to EXCLUDE

**Do NOT include:**
- Retail pet stores (Petco, PetSmart, etc.)
- For-profit breeders
- Puppy mills
- Backyard breeders
- Commercial animal sellers
- Pet shops that sell animals for profit
- Any organization that breeds and sells animals for profit

### Data Fields to Collect

For each organization, collect the following information:

| Field | Required | Max Length | Description |
|-------|----------|------------|-------------|
| `name` | **Yes** | 200 chars | Official organization name |
| `type` | Yes | - | Organization type (shelter, rescue, humane_society, spca, aspca, sanctuary, foster_network, nonprofit) |
| `email` | No | 200 chars | Contact email address |
| `phone` | No | 50 chars | Contact phone number |
| `website` | No | - | Official website URL |
| `address` | No | 300 chars | Street address |
| `city` | No | 100 chars | City name |
| `state` | **Yes** | 2 chars | State abbreviation (e.g., TX, CA) |
| `zip_code` | No | 20 chars | ZIP/postal code |
| `description` | No | 1000 chars | Brief mission statement or description |

## All 50 US States Reference

| Abbreviation | State Name | Abbreviation | State Name |
|-------------|------------|--------------|------------|
| AL | Alabama | MT | Montana |
| AK | Alaska | NE | Nebraska |
| AZ | Arizona | NV | Nevada |
| AR | Arkansas | NH | New Hampshire |
| CA | California | NJ | New Jersey |
| CO | Colorado | NM | New Mexico |
| CT | Connecticut | NY | New York |
| DE | Delaware | NC | North Carolina |
| FL | Florida | ND | North Dakota |
| GA | Georgia | OH | Ohio |
| HI | Hawaii | OK | Oklahoma |
| ID | Idaho | OR | Oregon |
| IL | Illinois | PA | Pennsylvania |
| IN | Indiana | RI | Rhode Island |
| IA | Iowa | SC | South Carolina |
| KS | Kansas | SD | South Dakota |
| KY | Kentucky | TN | Tennessee |
| LA | Louisiana | TX | Texas |
| ME | Maine | UT | Utah |
| MD | Maryland | VT | Vermont |
| MA | Massachusetts | VA | Virginia |
| MI | Michigan | WA | Washington |
| MN | Minnesota | WV | West Virginia |
| MS | Mississippi | WI | Wisconsin |
| MO | Missouri | WY | Wyoming |

## Output Format Specification

When collecting shelter data for a state, output JSON in this exact format:

```json
{
  "state": "TX",
  "state_full": "Texas",
  "collection_date": "2025-12-04",
  "shelters": [
    {
      "name": "Austin Pets Alive!",
      "type": "rescue",
      "email": "info@austinpetsalive.org",
      "phone": "(512) 961-6519",
      "website": "https://www.austinpetsalive.org",
      "address": "1156 West Cesar Chavez Street",
      "city": "Austin",
      "state": "TX",
      "zip_code": "78703",
      "description": "Austin Pets Alive! is a nonprofit organization dedicated to promoting and providing the resources, education, and programs needed to eliminate the killing of homeless companion animals in Austin."
    },
    {
      "name": "Dallas Animal Services",
      "type": "shelter",
      "email": "dallasanimalservices@dallascityhall.com",
      "phone": "(214) 670-8246",
      "website": "https://dallasanimalservices.org",
      "address": "1818 N Westmoreland Rd",
      "city": "Dallas",
      "state": "TX",
      "zip_code": "75212",
      "description": "Dallas Animal Services operates Dallas' only open-admission animal shelter and is committed to finding homes for all adoptable pets."
    }
  ],
  "total_count": 2,
  "notes": "Focused on major metropolitan areas and well-known rescues"
}
```

## Workflow Instructions

### Processing States

1. **Process one state at a time** to avoid overwhelming the system
2. **Start with larger states** that have more shelters (TX, CA, FL, NY, etc.)
3. **Verify organization legitimacy** before including

### Supported Prompts

You can respond to prompts like:
- `"Collect shelters for Texas"` or `"Collect TX shelters"`
- `"What's the next state to collect?"`
- `"Show collection progress"`
- `"Insert [STATE] shelters into database"`
- `"List completed states"`
- `"How many shelters have been collected?"`

### Quality Guidelines

1. **Verify Non-Profit Status**: Only include legitimate 501(c)(3) organizations or municipal shelters
2. **Current Information**: Prioritize recently verified contact information
3. **Complete Records**: Include as many fields as possible for each shelter
4. **No Duplicates**: Check for duplicate entries before adding
5. **Accurate Geography**: Ensure city/state/zip combinations are correct

## Database Integration

The collected data integrates with the existing `Shelter` model:

```python
class Shelter(Base):
    __tablename__ = "shelters"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), index=True)
    source = Column(String(50))  # Use "copilot_agent_collection"
    external_id = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(Text, nullable=True)
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    total_animals = Column(Integer, default=0)
```

### Source Field

All shelters collected by this agent should use:
```
source = "copilot_agent_collection"
```

This distinguishes them from shelters imported via API (e.g., `rescuegroups`).

## File Storage

Collected data is stored in:
- `backend/data/collected_shelters/{STATE}_shelters.json`
- Example: `backend/data/collected_shelters/TX_shelters.json`

Progress is tracked in:
- `backend/data/state_collection_tracker.json`

## Using the Shelter Collector Tool

After collecting data, use the Python tool to process it:

```bash
# Show collection progress
python backend/tools/shelter_collector.py --show-progress

# Get next state to collect
python backend/tools/shelter_collector.py --next-state

# Process a state file
python backend/tools/shelter_collector.py --file TX_shelters.json

# Insert from saved file to database
python backend/tools/shelter_collector.py --state TX --insert
```

## Example Collection Session

**User**: Collect shelters for Vermont

**Agent Response**:
```json
{
  "state": "VT",
  "state_full": "Vermont",
  "collection_date": "2025-12-04",
  "shelters": [
    {
      "name": "North Country Animal League",
      "type": "humane_society",
      "email": "info@ncal.com",
      "phone": "(802) 888-5065",
      "website": "https://ncal.com",
      "address": "16 Mountain View Meadow Road",
      "city": "Morrisville",
      "state": "VT",
      "zip_code": "05661",
      "description": "North Country Animal League is a private, nonprofit humane society serving Lamoille County and surrounding areas."
    }
  ],
  "total_count": 1,
  "notes": "Vermont is a small state with fewer shelters"
}
```

## Important Notes

1. **Data Quality Over Quantity**: It's better to have fewer accurate records than many inaccurate ones
2. **Respect Privacy**: Only include publicly available contact information
3. **Mission Focus**: Remember, the goal is to help shelter animals get adopted faster
4. **Regular Updates**: Shelter information changes - note collection dates for future updates
