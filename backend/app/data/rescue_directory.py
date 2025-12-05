"""Curated rescue directory and transport network metadata."""
from datetime import datetime


RESCUE_DIRECTORY = {
    "metadata": {
        "version": "2025-12-04",
        "generated_at": datetime.utcnow().isoformat(),
        "sources": [
            "Massachusetts Department of Agricultural Resources - Approved Shelter & Rescue List",
            "State & regional transport coalitions",
            "AKC Rescue Network public coordinator roster",
        ],
        "notes": "Dataset derived from partner briefings supplied by project stakeholders."
    },
    "states": {
        "massachusetts": [
            {
                "name": "Ahimsa Haven Animal Rescue",
                "location": "Templeton, MA",
                "phone": "978-297-2673",
                "email": "ahimsahaven@gmail.com",
                "website": "https://www.ahimsahaven.org",
                "license_type": "Local",
                "focus": ["shelter", "foster", "medical"],
                "description": "Volunteer-powered rescue providing humane care and local adoptions guided by the practice of non-violence."
            },
            {
                "name": "All For The Animals, Inc.",
                "location": "Sagamore Beach, MA",
                "email": "allfortheanimals@comcast.net",
                "website": "https://www.allfortheanimals.org",
                "license_type": "Local",
                "focus": ["foster-based"],
                "description": "Small foster collective serving the upper Cape with behaviorally matched placements."
            },
            {
                "name": "American Bullmastiff Association Rescue Service",
                "location": "Templeton, MA",
                "phone": "978-424-1044",
                "email": "BLACKSLATE@aol.com",
                "website": "https://bullmastiff.us/rescue",
                "license_type": "Import",
                "focus": ["breed-specific", "medical"],
                "description": "Breed club network coordinating intake of surrendered Bullmastiffs across the Northeast."
            },
            {
                "name": "Animal Protection Center of Southeastern Massachusetts",
                "location": "Brockton, MA",
                "phone": "508-586-2053",
                "email": "info@apcsm.org",
                "website": "https://www.apcsm.org",
                "license_type": "Import",
                "focus": ["education", "managed admission"],
                "description": "Managed-admission shelter serving Plymouth, Norfolk, and Bristol counties with adoption and outreach services."
            },
            {
                "name": "Animal Rescue League of Boston",
                "location": "Boston, MA",
                "phone": "617-426-9170",
                "email": "boston-adoption@arlboston.org",
                "website": "https://www.arlboston.org",
                "license_type": "Import",
                "focus": ["law enforcement", "veterinary", "transport"],
                "description": "State-wide agency with adoption centers in Boston, Brewster, and Dedham plus humane law enforcement authority."
            },
            {
                "name": "Animal Shelter Inc. of Sterling",
                "location": "Sterling, MA",
                "phone": "978-422-8585",
                "email": "staff@sterlingshelter.org",
                "website": "https://www.sterlingshelter.org",
                "license_type": "Import",
                "focus": ["no-kill shelter", "spay/neuter clinic"],
                "description": "High-volume adoption center with community veterinary programs and humane education."
            },
            {
                "name": "Baypath Humane Society of Hopkinton",
                "location": "Hopkinton, MA",
                "phone": "508-435-6938",
                "email": "info@baypathhumane.org",
                "website": "https://www.baypathhumane.org",
                "license_type": "Import",
                "focus": ["behavior", "foster"],
                "description": "Fast-placement shelter leveraging a deep foster bench for decompression and enrichment."
            },
            {
                "name": "Broken Tail Rescue",
                "location": "Worcester, MA",
                "phone": "508-494-0963",
                "email": "info@brokentailrescue.org",
                "website": "https://www.brokentailrescue.org",
                "license_type": "Local",
                "focus": ["foster-based", "spay/neuter"],
                "description": "All-volunteer rescue coordinating with municipal partners across Central Massachusetts."
            },
            {
                "name": "Buddy Dog Humane Society",
                "location": "Sudbury, MA",
                "phone": "978-443-6990",
                "email": "info@buddydoghs.org",
                "website": "https://www.buddydoghs.org",
                "license_type": "Import",
                "focus": ["no-kill shelter", "transport"],
                "description": "Legacy humane society (est. 1961) offering lifelong placement support and multi-state intake."
            },
            {
                "name": "Cape Ann Animal Aid",
                "location": "Gloucester, MA",
                "phone": "978-283-6055",
                "email": "info@capeannanimalaid.org",
                "website": "https://www.capeannanimalaid.org",
                "license_type": "Import",
                "focus": ["transport", "medical"],
                "description": "Christopher Cutler Rich Animal Shelter transporting dogs and cats from overburdened regions into New England homes."
            },
            {
                "name": "Dakin Humane Society",
                "location": "Springfield, MA",
                "phone": "413-781-4000",
                "email": "springfield@dakinhumane.org",
                "website": "https://www.dakinhumane.org",
                "license_type": "Import",
                "focus": ["high-volume spay/neuter", "community programs"],
                "description": "Western MA resource center moving 20,000+ animals annually through shelter, pet food pantry, and pet health services."
            },
            {
                "name": "Last Hope K9 Rescue",
                "location": "Boston, MA",
                "email": "info@lasthopek9.org",
                "website": "https://www.lasthopek9.org",
                "license_type": "Import",
                "focus": ["transport", "foster"],
                "description": "All-breed foster network importing at-risk dogs from Arkansas partners before matching with New England adopters."
            },
            {
                "name": "MSPCA–Angell",
                "location": "Statewide (Boston, Methuen, Salem, Centerville)",
                "phone": "617-522-5055",
                "email": "adoption@mspca.org",
                "website": "https://www.mspca.org",
                "license_type": "Import",
                "focus": ["open admission", "law enforcement", "veterinary"],
                "description": "Comprehensive humane society combining adoption centers, Angell Animal Medical Center, and statewide advocacy."
            },
            {
                "name": "Sweet Paws Rescue",
                "location": "Groveland, MA",
                "email": "info@sweetpawsrescue.org",
                "website": "https://www.sweetpawsrescue.org",
                "license_type": "Import",
                "focus": ["southern transport", "foster"],
                "description": "Grassroots rescue saving dogs and cats from Mississippi and Alabama, then placing them with Massachusetts foster homes."
            },
            {
                "name": "Worcester Animal Rescue League",
                "location": "Worcester, MA",
                "phone": "508-853-0030",
                "email": "info@worcesterarl.org",
                "website": "https://www.worcesterarl.org",
                "license_type": "Import",
                "focus": ["shelter", "public clinic"],
                "description": "Limited-intake shelter offering adoptions, dog training, and a community veterinary clinic for Central MA residents."
            }
        ]
    },
    "national": {
        "northeast_destination": [
            {
                "name": "North Shore Animal League America",
                "region": "Port Washington, NY",
                "website": "https://www.animalleague.org",
                "description": "World's largest no-kill adoption campus accepting large transport deliveries weekly."
            },
            {
                "name": "Animal Care Centers of NYC",
                "region": "New York City",
                "website": "https://www.nycacc.org",
                "contact": "311 (NYC)",
                "description": "Open-admission municipal safety net for the five boroughs partnering with over 200 rescue transfer groups."
            },
            {
                "name": "Brandywine Valley SPCA",
                "region": "PA / DE",
                "website": "https://www.bvspca.org",
                "description": "Regional hub operating multiple campuses and municipal contracts across Pennsylvania and Delaware."
            }
        ],
        "southern_source": [
            {
                "name": "Austin Animal Center",
                "region": "Austin, TX",
                "website": "https://www.austintexas.gov/department/animal-services",
                "contact": "data.austintexas.gov",
                "description": "Largest municipal no-kill shelter in the United States with >95% live release."
            },
            {
                "name": "Dallas Animal Services",
                "region": "Dallas, TX",
                "website": "https://www.dallasanimalservices.org",
                "description": "High-volume open-intake shelter (30k+ animals/year) powering progressive adoption and transfer programs."
            },
            {
                "name": "BARC Animal Shelter & Adoptions",
                "region": "Houston, TX",
                "website": "https://www.houstontx.gov/barc",
                "description": "City of Houston's field services, licensing, and shelter operations with heavy reliance on rescue partners."
            },
            {
                "name": "San Antonio Pets Alive!",
                "region": "San Antonio, TX",
                "website": "https://www.sanantoniopetsalive.org",
                "description": "Pulls exclusively from the municipal euthanasia list to create lifesaving capacity."
            },
            {
                "name": "God's Dogs Rescue",
                "region": "San Antonio, TX",
                "website": "https://www.godsdogsrescue.org",
                "description": "Massive foster network moving thousands of dogs each year to Pacific Northwest and Midwest adopters."
            }
        ],
        "florida_peninsula": [
            {
                "name": "Jacksonville Humane Society",
                "region": "Jacksonville, FL",
                "website": "https://www.jaxhumane.org",
                "description": "National leader in shelter medicine and community safety-net programming."
            },
            {
                "name": "Peggy Adams Animal Rescue League",
                "region": "Palm Beach County, FL",
                "website": "https://www.peggyadams.org",
                "description": "Large private shelter with high-volume sterilization clinics serving South Florida."
            },
            {
                "name": "Alaqua Animal Refuge",
                "region": "Walton County, FL",
                "website": "https://www.alaqua.org",
                "description": "100-acre refuge providing sanctuary services for companion animals and farm species."
            }
        ],
        "virginia_commonwealth": [
            {
                "name": "Richmond Animal Care & Control",
                "region": "Richmond, VA",
                "website": "https://www.rva.gov/animal-care-control",
                "description": "Open-admission municipal shelter with aggressive cruelty investigation work."
            },
            {
                "name": "Richmond SPCA",
                "region": "Richmond, VA",
                "website": "https://www.richmondspca.org",
                "description": "No-kill leader operating a public veterinary hospital and robust behavior center."
            },
            {
                "name": "Lynchburg Humane Society",
                "region": "Lynchburg, VA",
                "website": "https://www.lynchburghumane.org",
                "description": "Pet-centric community center offering intake diversion and high-save-rate sheltering."
            }
        ],
        "midwest_crossroads": [
            {
                "name": "PAWS Chicago",
                "region": "Chicago, IL",
                "website": "https://www.pawschicago.org",
                "description": "Renowned no-kill adoption and medical center serving as a regional transport destination."
            },
            {
                "name": "Cleveland Animal Protective League",
                "region": "Cleveland, OH",
                "website": "https://www.clevelandapl.org",
                "description": "Legacy humane society with humane investigations and comprehensive medical services."
            },
            {
                "name": "Toledo Area Humane Society",
                "region": "Maumee, OH",
                "website": "https://www.toledohumane.org",
                "description": "Oldest animal welfare organization in the region with court-appointed cruelty authority."
            }
        ],
        "west_coast_relief": [
            {
                "name": "San Diego Humane Society",
                "region": "San Diego, CA",
                "website": "https://www.sdhumane.org",
                "description": "County-wide safety net running multiple campuses and an emergency response program."
            },
            {
                "name": "Los Angeles Animal Services",
                "region": "Los Angeles, CA",
                "website": "https://www.laanimalservices.com",
                "description": "Six-shelter municipal system with some of the highest intake volumes in the country."
            },
            {
                "name": "Riverside County Department of Animal Services",
                "region": "Riverside, CA",
                "website": "https://www.rcdas.org",
                "description": "Large municipal service covering 7,300 square miles and collaborating with transport partners."
            },
            {
                "name": "Frosted Faces Foundation",
                "region": "Ramona, CA",
                "website": "https://www.frostedfacesfoundation.org",
                "description": "Senior-dog sanctuary providing lifelong medical care and hospice-level fostering."
            }
        ]
    },
    "akc_network": [
        {
            "breed": "Afghan Hound",
            "context": "Coat-intensive sighthound requiring specialized grooming and secure containment.",
            "contacts": [
                {"name": "Afghan Hound Club of America", "phone": "877-237-3728", "email": "affierescue@aol.com"},
                {"name": "North East Afghan Hound Rescue", "phone": "978-774-8966", "email": "neahr@comcast.net"}
            ]
        },
        {
            "breed": "Airedale Terrier",
            "context": "High-drive working terrier surrendered for energy and dominance challenges.",
            "contacts": [
                {"organization": "Starting Over Airedale Rescue", "phone": "231-798-4846"},
                {"organization": "Sunshine Airedalers of Florida", "phone": "407-625-2660"}
            ]
        },
        {
            "breed": "Akita",
            "context": "Large guardian breed with strict adopter screening requirements.",
            "contacts": [
                {"organization": "Akita Club of America", "phone": "480-518-5296", "email": "efulghum@paradigm-eng.com"},
                {"organization": "Akita Rescue Mid-Atlantic Coast", "phone": "703-730-0844", "email": "info@akitarescue.org"},
                {"organization": "Big East Akita Rescue", "phone": "609-388-7004"}
            ]
        },
        {
            "breed": "American Staffordshire Terrier",
            "context": "Breed-specific legislation compliance and housing navigation support.",
            "contacts": [
                {"organization": "ASTC Rescue", "phone": "408-776-8271", "contact": "Joyce Martin"}
            ]
        },
        {
            "breed": "Australian Cattle Dog",
            "context": "Mouthy herders requiring jobs and experienced adopters.",
            "contacts": [
                {"organization": "Australian Cattle Dog Rescue, Inc.", "phone": "423-536-8119", "email": "hammsh1969@hotmail.com"}
            ]
        },
        {
            "breed": "Basset Hound",
            "context": "Chronic ear, skin, and orthopedic cases needing medical fundraising.",
            "contacts": [
                {"organization": "Basset Hound Club of America", "email": "bhcs.cs@gmail.com"},
                {"organization": "New England Basset Hound Rescue", "region": "CT/MA"}
            ]
        },
        {
            "breed": "Beagle",
            "context": "Laboratory retirements and scent-driven escape risks.",
            "contacts": [
                {"organization": "Beagle Rescue League", "phone": "866-739-0350", "email": "info@beaglerescueleague.org"},
                {"organization": "Arizona Beagle Rescue", "phone": "623-977-1355"}
            ]
        },
        {
            "breed": "Bernese Mountain Dog",
            "context": "Short lifespan and oncology-heavy caseloads.",
            "contacts": [
                {"organization": "Bernese Mountain Dog Club of America", "email": "bmdrescue@clearwater.net"},
                {"organization": "Blue Ridge Bernese Mountain Dog Club", "phone": "660-342-6555"}
            ]
        },
        {
            "breed": "Bulldog",
            "context": "BOAS airway surgeries and orthopedic interventions routinely required.",
            "contacts": [
                {"organization": "Bulldog Club of America Rescue Network", "phone": "833-223-3833"},
                {"organization": "Chicago French Bulldog Rescue", "email": "mary@frenchieporvous.org"}
            ]
        },
        {
            "breed": "German Shepherd Dog",
            "context": "Second most surrendered working breed; strong protection drive.",
            "contacts": [
                {"organization": "Austin German Shepherd Rescue", "website": "https://www.austingermanshepherdrescue.org"},
                {"organization": "Virginia German Shepherd Rescue", "phone": "703-435-2840"}
            ]
        },
        {
            "breed": "Great Dane",
            "context": "Giant breed medical costs (bloat, cardiomyopathy) requiring regional fundraising.",
            "contacts": [
                {"organization": "Great Dane Rescue, Inc.", "phone": "734-454-3683"},
                {"organization": "San Antonio Great Dane Rescue", "phone": "210-724-3461"}
            ]
        },
        {
            "breed": "Pug",
            "context": "High frequency of eye surgeries and airway concerns.",
            "contacts": [
                {"organization": "Pug Dog Club of America", "phone": "812-454-4953"},
                {"organization": "DFW Pug Rescue Club", "phone": "817-329-4885"}
            ]
        },
        {
            "breed": "Siberian Husky",
            "context": "Escape artists requiring containment counseling and high exercise commitments.",
            "contacts": [
                {"organization": "Texas Husky Rescue", "phone": "877-TX-HUSKY"},
                {"organization": "Adopt A Husky (IL/MN)", "phone": "262-909-2244"}
            ]
        }
    ]
}
