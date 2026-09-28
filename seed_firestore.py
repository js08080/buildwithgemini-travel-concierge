import sys
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-3746c509ea15"
COLLECTION_NAME = "destinations"

SAMPLE_DESTINATIONS = [
    {
        "id": "kyoto-bamboo-grove",
        "name": "Arashiyama Bamboo Grove",
        "city": "Kyoto",
        "country": "Japan",
        "category": "Nature & Scenery",
        "rating": 4.8,
        "price_level": "$$",
        "description": "A breathtaking natural forest of towering bamboo stalks in western Kyoto, offering tranquil walking paths.",
        "tags": ["nature", "scenic", "peaceful", "photography"]
    },
    {
        "id": "santorini-oia-sunset",
        "name": "Oia Sunset Lookout",
        "city": "Santorini",
        "country": "Greece",
        "category": "Sightseeing & Views",
        "rating": 4.9,
        "price_level": "$$$",
        "description": "Iconic whitewashed buildings with blue domes overlooking the Aegean Sea during golden hour sunsets.",
        "tags": ["sunset", "romantic", "sea", "scenic"]
    },
    {
        "id": "amalfi-coast-drive",
        "name": "Amalfi Coastal Road & Ravello",
        "city": "Amalfi",
        "country": "Italy",
        "category": "Coastal Exploration",
        "rating": 4.7,
        "price_level": "$$$$",
        "description": "Dramatic cliffside coastal roads connecting cliff-perched towns, lemon groves, and Mediterranean views.",
        "tags": ["coastal", "scenic", "luxury", "roadtrip"]
    },
    {
        "id": "istanbul-grand-bazaar",
        "name": "Grand Bazaar",
        "city": "Istanbul",
        "country": "Turkey",
        "category": "Culture & Shopping",
        "rating": 4.6,
        "price_level": "$$",
        "description": "One of the largest and oldest covered markets in the world, filled with spices, lanterns, ceramics, and teas.",
        "tags": ["culture", "shopping", "historic", "food"]
    },
    {
        "id": "banff-lake-louise",
        "name": "Lake Louise & Moraine Lake",
        "city": "Banff",
        "country": "Canada",
        "category": "Mountain Adventure",
        "rating": 4.9,
        "price_level": "$$$",
        "description": "Vibrant turquoise glacier-fed lakes surrounded by snow-capped peaks in the Canadian Rockies.",
        "tags": ["mountains", "lakes", "hiking", "scenic"]
    }
]

def get_firestore_client():
    """Returns a Firestore client for the hardcoded project ID."""
    try:
        # Try standard initialization
        db = firestore.Client(project=PROJECT_ID)
        # Quick check if auth works
        list(db.collections(retry=None, timeout=2))
        return db
    except Exception:
        # Fallback for local environment using gcloud token
        import subprocess, google.auth.credentials
        class GcloudCredentials(google.auth.credentials.Credentials):
            def refresh(self, request):
                token = subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()
                self.token = token
        creds = GcloudCredentials()
        creds.refresh(None)
        return firestore.Client(project=PROJECT_ID, credentials=creds)

def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)
    
    for item in SAMPLE_DESTINATIONS:
        doc_id = item["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"Seeded document '{doc_id}' in '{COLLECTION_NAME}'.")
    
    print(f"Successfully seeded {len(SAMPLE_DESTINATIONS)} items to Firestore!")

if __name__ == "__main__":
    seed_database()
