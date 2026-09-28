# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

import json
import os
from pathlib import Path

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    get_destination,
    search_destinations,
    add_destination,
    generate_destination_image,
    get_live_weather,
    convert_currency,
    geocode_address,
    find_nearby_places,
    generate_travel_image,
    generate_travel_video,
)

# Load Agent Engine resource name from deployment_metadata.json if available
metadata_file = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
sandbox_resource_name = None

if metadata_file.exists():
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
            agent_engine_resource_name = meta.get("agent_engine_resource_name") or meta.get("reasoning_engine_resource_name")
            sandbox_resource_name = meta.get("sandbox_resource_name")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name,
    sandbox_resource_name=sandbox_resource_name,
)

# Memory Bank Configuration
PROJECT_ID = "qwiklabs-gcp-03-3746c509ea15"
LOCATION = "us-central1"
MEMORY_BANK_ID = "4234799270949027840"

async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Memory Bank for extraction."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None

def memory_service_builder():
    """Builds VertexAiMemoryBankService for deployed container runtime."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )

memory_service = memory_service_builder()


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build A2UI system prompt (version 0.8 with BasicCatalog)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Travel Concierge, a personalized AI travel assistant. You help users explore "
        "destinations, build customized itineraries, search travel database entries, add new places, "
        "fetch live weather, convert trip budget currencies, geocode addresses, find nearby places of "
        "interest, generate high-quality AI scenic images, and execute Python code safely in a sandbox environment. "
        "You remember user preferences, facts, and health/dietary restrictions (especially user allergies "
        "such as gluten, peanuts, shellfish, or dairy) across conversations using your Memory Bank. "
        "Always check preloaded memories for any stated user allergies and strictly account for them when "
        "suggesting places, restaurants, or travel itineraries."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        get_destination,
        search_destinations,
        add_destination,
        generate_destination_image,
        generate_travel_image,
        generate_travel_video,
        get_live_weather,
        convert_currency,
        geocode_address,
        find_nearby_places,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
