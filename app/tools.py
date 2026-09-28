# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud import firestore
from google.adk.tools import ToolContext

PROJECT_ID = "qwiklabs-gcp-03-3746c509ea15"
COLLECTION_NAME = "destinations"

_db_instance = None

def get_firestore_client():
    """Returns a cached Firestore client for the hardcoded project ID."""
    global _db_instance
    if _db_instance is not None:
        return _db_instance
    
    try:
        db = firestore.Client(project=PROJECT_ID)
        # Verify access
        list(db.collections(retry=None, timeout=2))
        _db_instance = db
        return _db_instance
    except Exception:
        # Fallback for local dev environment using active gcloud credential token
        import subprocess, google.auth.credentials
        class GcloudCredentials(google.auth.credentials.Credentials):
            def refresh(self, request):
                token = subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()
                self.token = token
        creds = GcloudCredentials()
        creds.refresh(None)
        _db_instance = firestore.Client(project=PROJECT_ID, credentials=creds)
        return _db_instance


def get_destination(destination_id: str) -> dict:
    """Fetch detailed information for a specific travel destination from Firestore by its ID.

    Args:
        destination_id: The unique ID of the destination (e.g., 'kyoto-bamboo-grove', 'santorini-oia-sunset').

    Returns:
        A dictionary containing destination details or an error message if not found.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(COLLECTION_NAME).document(destination_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return {"error": f"Destination with ID '{destination_id}' not found."}
    except Exception as e:
        return {"error": f"Failed to retrieve destination: {str(e)}"}


def search_destinations(query: str = "", category: str = "") -> list[dict]:
    """Search or list travel destinations from Firestore matching a search term or category filter.

    Args:
        query: Optional search term to filter destinations by name, city, country, or description.
        category: Optional category string to filter by (e.g. 'Nature & Scenery', 'Culture & Shopping').

    Returns:
        A list of destination dictionaries matching the query filters.
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection(COLLECTION_NAME)
        docs = collection_ref.stream()
        
        results = []
        q_lower = query.strip().lower()
        cat_lower = category.strip().lower()
        
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            
            # Category match
            if cat_lower and cat_lower not in data.get("category", "").lower():
                continue
            
            # Query keyword match across fields
            if q_lower:
                text_corpus = " ".join([
                    data.get("name", ""),
                    data.get("city", ""),
                    data.get("country", ""),
                    data.get("category", ""),
                    data.get("description", ""),
                    " ".join(data.get("tags", []))
                ]).lower()
                
                if q_lower not in text_corpus:
                    continue
            
            results.append(data)
            
        return results
    except Exception as e:
        return [{"error": f"Failed to search destinations: {str(e)}"}]


def add_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    description: str,
    rating: float = 4.5,
    tags: str = ""
) -> dict:
    """Add a new travel destination document to Firestore.

    Args:
        name: Name of the destination (e.g. 'Mount Fuji').
        city: Nearest city or region.
        country: Country where destination is located.
        category: Category (e.g. 'Nature & Scenery', 'Adventure').
        description: Brief overview of the location.
        rating: Optional rating out of 5.0 (default 4.5).
        tags: Comma-separated list of tags (e.g. 'hiking, scenic, mountain').

    Returns:
        A dictionary with the created destination details and document ID.
    """
    try:
        db = get_firestore_client()
        
        # Generate clean ID from name
        doc_id = name.lower().replace(" ", "-").replace("'", "").replace("&", "and")
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else tags
        
        item_data = {
            "id": doc_id,
            "name": name,
            "city": city,
            "country": country,
            "category": category,
            "description": description,
            "rating": rating,
            "tags": tag_list
        }
        
        db.collection(COLLECTION_NAME).document(doc_id).set(item_data)
        return {"status": "success", "message": f"Successfully created destination '{name}'", "destination": item_data}
    except Exception as e:
        return {"error": f"Failed to add destination: {str(e)}"}


def generate_destination_image(location_name: str, prompt: str = "") -> dict:
    """Generate a scenic postcard preview image for a travel destination and upload it to Cloud Storage.

    Args:
        location_name: Name of the destination (e.g. 'Kyoto Bamboo Grove', 'Santorini Sunset').
        prompt: Optional specific visual description prompt for the postcard preview.

    Returns:
        A dictionary containing the status, location name, and public image URL.
    """
    import io
    from PIL import Image, ImageDraw
    from google.cloud import storage

    bucket_name = "travel-concierge-assets-qwiklabs-gcp-03-3746c509ea15"
    clean_name = location_name.lower().replace(" ", "_").replace("'", "")
    filename = f"{clean_name}_preview.png"
    
    try:
        width, height = 800, 500
        img = Image.new("RGB", (width, height), color=(240, 244, 248))
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        for i in range(height):
            r = int(25 + (i / height) * 35)
            g = int(80 + (i / height) * 65)
            b = int(140 + (i / height) * 75)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
            
        # Draw postcard border
        draw.rectangle([20, 20, width - 20, height - 20], outline=(255, 255, 255), width=4)
        
        # Draw header text
        display_prompt = prompt if prompt else f"Scenic View of {location_name}"
        draw.text((40, 180), location_name.upper(), fill=(255, 255, 255))
        draw.text((40, 240), f'"{display_prompt}"', fill=(220, 235, 255))
        draw.text((40, 420), "TRAVEL CONCIERGE POSTCARD PREVIEW", fill=(200, 220, 240))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_file(buf, content_type="image/png")
        
        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        return {
            "status": "success",
            "location": location_name,
            "image_url": public_url,
            "message": f"Generated postcard preview for '{location_name}'."
        }
    except Exception as e:
        return {"error": f"Failed to generate destination image: {str(e)}"}


def get_live_weather(location: str) -> dict:
    """Fetch current real-world weather data for a travel destination using Open-Meteo public API.

    Args:
        location: City or location name (e.g. 'Kyoto', 'Paris', 'Santorini').

    Returns:
        A dictionary containing location, coordinates, temperature (C), humidity (%), and wind speed.
    """
    import urllib.request
    import urllib.parse
    import json
    import os

    try:
        # Step 1: Geocoding search
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1"
        headers = {"User-Agent": "TravelConcierge/1.0"}
        
        api_key = os.environ.get("OPEN_METEO_API_KEY")
        if api_key:
            headers["X-Api-Key"] = api_key

        req = urllib.request.Request(geo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return {"error": f"Location '{location}' not found."}

        loc_info = geo_data["results"][0]
        lat, lon = loc_info["latitude"], loc_info["longitude"]
        city_name = loc_info.get("name", location)
        country_name = loc_info.get("country", "")

        # Step 2: Live weather fetch
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        w_req = urllib.request.Request(weather_url, headers=headers)
        with urllib.request.urlopen(w_req, timeout=5) as w_resp:
            w_data = json.loads(w_resp.read().decode())

        current = w_data.get("current", {})
        return {
            "status": "success",
            "location": f"{city_name}, {country_name}".strip(", "),
            "latitude": lat,
            "longitude": lon,
            "temperature_celsius": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch live weather for '{location}': {str(e)}"}


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> dict:
    """Convert trip budget amounts between currencies using the Frankfurter public API.

    Args:
        amount: Numerical amount to convert (e.g. 500.0).
        from_currency: 3-letter source currency code (e.g. 'USD', 'EUR').
        to_currency: 3-letter target currency code (e.g. 'JPY', 'EUR', 'GBP').

    Returns:
        A dictionary containing the conversion amount, exchange rate, and converted total.
    """
    import urllib.request
    import json
    import os

    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()

    try:
        url = f"https://api.frankfurter.dev/v1/latest?amount={amount}&from={from_curr}&to={to_curr}"
        headers = {"User-Agent": "TravelConcierge/1.0"}
        
        api_key = os.environ.get("FRANKFURTER_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        converted_val = data.get("rates", {}).get(to_curr)
        if converted_val is None:
            return {"error": f"Unsupported currency code '{to_curr}' or conversion path."}

        return {
            "status": "success",
            "original_amount": amount,
            "from_currency": from_curr,
            "converted_amount": converted_val,
            "to_currency": to_curr,
            "exchange_date": data.get("date")
        }
    except Exception as e:
        return {"error": f"Failed to convert currency: {str(e)}"}


def geocode_address(address: str) -> dict:
    """Geocode an address into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: Human-readable street address or location name (e.g., '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing name, formatted address, and coordinates location (latitude, longitude).
    """
    import urllib.request
    import urllib.parse
    import json
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "error": "GOOGLE_MAPS_API_KEY is not configured or contains placeholder in .env.",
            "address": address
        }

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed for '{address}': status={data.get('status')}"}

        result = data["results"][0]
        loc = result.get("geometry", {}).get("location", {})
        return {
            "status": "success",
            "name": address,
            "address": result.get("formatted_address", address),
            "location": {
                "latitude": loc.get("lat"),
                "longitude": loc.get("lng")
            }
        }
    except Exception as e:
        return {"error": f"Failed to geocode address: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 1000.0
) -> dict:
    """Find nearby places of a given type around coordinates using Google Places API (New).

    Args:
        latitude: Target center latitude coordinate.
        longitude: Target center longitude coordinate.
        place_type: Type of place to search for (e.g. 'restaurant', 'tourist_attraction', 'museum', 'hotel').
        radius_meters: Search radius in meters (default 1000.0).

    Returns:
        A dictionary containing a list of nearby places with key fields (name, address, location).
    """
    import urllib.request
    import json
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "error": "GOOGLE_MAPS_API_KEY is not configured or contains placeholder in .env.",
            "latitude": latitude,
            "longitude": longitude
        }

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
        }
        
        payload = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius_meters
                }
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        raw_places = data.get("places", [])
        places_list = []
        for p in raw_places:
            places_list.append({
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "location": p.get("location", {})
            })

        return {
            "status": "success",
            "count": len(places_list),
            "places": places_list
        }
    except Exception as e:
        return {"error": f"Failed to search nearby places: {str(e)}"}


async def generate_travel_image(item_name: str, tool_context: ToolContext, prompt: str = "") -> dict:
    """Generate a scenic travel image using gemini-3.1-flash-lite-image model in global region.

    Saves the image as an ADK artifact (Playground panel) and uploads it to public GCS bucket.

    Args:
        item_name: Name of the travel destination or landmark (e.g. 'Kyoto Bamboo Grove').
        tool_context: ADK ToolContext instance for saving artifacts.
        prompt: Optional visual detail prompt describing the image.

    Returns:
        A dictionary containing the status, item_name, and public GCS https URL.
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "travel-concierge-assets-qwiklabs-gcp-03-3746c509ea15"
    project_id = "qwiklabs-gcp-03-3746c509ea15"
    
    clean_name = item_name.lower().replace(" ", "_").replace("'", "").replace("/", "_")
    filename = f"{clean_name}_{uuid.uuid4().hex[:6]}.png"
    
    gen_prompt = prompt if prompt else f"A scenic postcard photograph of {item_name}"
    
    try:
        # Initialize Vertex AI client in global region
        client = genai.Client(vertexai=True, project=project_id, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=gen_prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        
        image_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break

        if not image_bytes:
            return {"error": f"No image data returned from gemini-3.1-flash-lite-image model for '{item_name}'."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        await tool_context.save_artifact(filename=filename, artifact=part_artifact)

        # 2. Upload image bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/png")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        return {
            "status": "success",
            "item_name": item_name,
            "image_url": public_url,
            "message": f"Successfully generated image for '{item_name}'."
        }
    except Exception as e:
        return {"error": f"Failed to generate travel image: {str(e)}"}


async def generate_travel_video(item_name: str, tool_context: ToolContext, prompt: str = "") -> dict:
    """Generate a short video clip for a travel destination or landmark using gemini-omni-flash-preview model in global region.

    Saves the generated video as an ADK artifact (Playground panel) and uploads it to public GCS bucket.

    Args:
        item_name: Name of the travel destination or landmark (e.g. 'Kyoto Bamboo Grove', 'Eiffel Tower Paris').
        tool_context: ADK ToolContext instance for saving artifacts.
        prompt: Optional visual detail prompt describing the video scene.

    Returns:
        A dictionary containing status, item_name, and public GCS video_url.
    """
    import uuid
    import base64
    from google import genai
    from google.genai import types
    from google.cloud import storage

    bucket_name = "travel-concierge-assets-qwiklabs-gcp-03-3746c509ea15"
    project_id = "qwiklabs-gcp-03-3746c509ea15"

    clean_name = item_name.lower().replace(" ", "_").replace("'", "").replace("/", "_")
    filename = f"{clean_name}_{uuid.uuid4().hex[:6]}.mp4"

    gen_prompt = prompt if prompt else f"A short cinematic video preview of travel destination {item_name}"

    try:
        # Initialize Vertex AI client in global region
        client = genai.Client(vertexai=True, project=project_id, location="global")
        
        # Interactions API call for gemini-omni-flash-preview video model
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=gen_prompt
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            data = getattr(interaction.output_video, "data", None)
            if isinstance(data, str):
                video_bytes = base64.b64decode(data)
            elif isinstance(data, bytes):
                video_bytes = data
        elif hasattr(interaction, "outputs"):
            for out in interaction.outputs:
                data = getattr(out, "data", None)
                if data:
                    video_bytes = base64.b64decode(data) if isinstance(data, str) else data
                    break

        if not video_bytes:
            return {"error": f"No video data returned from gemini-omni-flash-preview model for '{item_name}'."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=part_artifact)

        # 2. Upload video bytes directly to public Cloud Storage bucket (without writing local file)
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        return {
            "status": "success",
            "item_name": item_name,
            "video_url": public_url,
            "message": f"Successfully generated video preview for '{item_name}'."
        }
    except Exception as e:
        return {"error": f"Failed to generate travel video: {str(e)}"}





