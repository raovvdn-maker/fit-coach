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

import base64
import datetime
import io
import json
import os
import uuid
from zoneinfo import ZoneInfo
import imageio
from PIL import Image
import requests
from google import genai
from google.cloud import firestore, storage

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

# CRITICAL: Hardcode GCP Project ID and Cloud Storage Bucket Name
PROJECT_ID = "qwiklabs-gcp-03-c8c5574b200d"
GCS_BUCKET_NAME = "fit-coach-media-c8c5574b200d"


def get_firestore_client():
    return firestore.Client(project=PROJECT_ID)


def list_exercises(category: str = "") -> list[dict]:
    """Retrieve exercises from the Firestore database, optionally filtered by category.

    Args:
        category: Optional category filter (e.g. 'Bodyweight', 'Strength', 'Core').

    Returns:
        A list of exercise dictionaries.
    """
    db = get_firestore_client()
    query_ref = db.collection("exercises")
    if category:
        query_ref = query_ref.where("category", "==", category)

    docs = query_ref.stream()
    return [doc.to_dict() for doc in docs]


def get_exercise_details(exercise_id: str) -> dict:
    """Get detailed information for a specific exercise by ID.

    Args:
        exercise_id: The unique identifier of the exercise (e.g. 'pushups', 'barbell_squat').

    Returns:
        A dictionary with exercise details or an error message if not found.
    """
    db = get_firestore_client()
    doc = db.collection("exercises").document(exercise_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Exercise '{exercise_id}' not found."}


def add_exercise(
    exercise_id: str,
    name: str,
    category: str,
    target_muscle: str,
    difficulty: str,
    description: str,
    recommended_sets: int = 3,
    recommended_reps: str = "10-12",
) -> str:
    """Add a new exercise to the Firestore catalog.

    Args:
        exercise_id: Unique slug/id for the exercise (e.g., 'lunges').
        name: Full title of the exercise.
        category: Exercise category (e.g., 'Legs', 'Cardio', 'Strength').
        target_muscle: Primary muscle group targeted.
        difficulty: Difficulty level ('Beginner', 'Intermediate', 'Advanced').
        description: Description of proper form and execution.
        recommended_sets: Number of sets.
        recommended_reps: Repetition range.

    Returns:
        Confirmation message string.
    """
    db = get_firestore_client()
    item = {
        "id": exercise_id,
        "name": name,
        "category": category,
        "target_muscle": target_muscle,
        "difficulty": difficulty,
        "description": description,
        "recommended_sets": recommended_sets,
        "recommended_reps": recommended_reps,
    }
    db.collection("exercises").document(exercise_id).set(item)
    return f"Exercise '{name}' (ID: {exercise_id}) successfully added to Firestore!"


def log_workout_session(
    exercise_id: str,
    sets_completed: int,
    reps_per_set: int,
    weight_lbs: float = 0.0,
    duration_minutes: int = 0,
    notes: str = "",
) -> str:
    """Logs a completed workout session to Firestore.

    Args:
        exercise_id: The ID or name of the exercise performed (e.g. 'pushups', 'barbell_squat').
        sets_completed: Number of sets completed.
        reps_per_set: Number of repetitions per set.
        weight_lbs: Weight used in lbs (0 for bodyweight exercises).
        duration_minutes: Duration of the session in minutes.
        notes: Optional user notes on effort or performance.

    Returns:
        A confirmation message string with the log ID.
    """
    db = get_firestore_client()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_doc = {
        "exercise_id": exercise_id,
        "sets_completed": sets_completed,
        "reps_per_set": reps_per_set,
        "weight_lbs": weight_lbs,
        "duration_minutes": duration_minutes,
        "notes": notes,
        "timestamp": timestamp,
    }
    _, doc_ref = db.collection("workout_logs").add(log_doc)
    return f"Successfully logged workout for '{exercise_id}' (Log ID: {doc_ref.id})!"


def get_daily_motivation() -> dict:
    """Fetches a random motivational quote from a public API to inspire fitness training.

    Reads optional MOTIVATION_API_KEY from environment variables if set.

    Returns:
        A dictionary containing the motivational quote and author.
    """
    api_key = os.environ.get("MOTIVATION_API_KEY", "")
    headers = {"X-Api-Key": api_key} if api_key else {}
    try:
        resp = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=5)
        if resp.status_code == 200:
            item = resp.json()[0]
            return {
                "quote": item.get("q", "No pain, no gain."),
                "author": item.get("a", "FitCoach"),
            }
    except Exception as e:
        pass
    return {
        "quote": "Success starts with self-discipline.",
        "author": "FitCoach Motivation",
    }


def generate_exercise_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates a fitness photo or visual illustration for an exercise, workout, posture, equipment, or meal using gemini-3.1-flash-lite-image in the global region.

    Saves the image as a Playground artifact and uploads the image bytes directly to Cloud Storage.

    Args:
        prompt: Description of the exercise visual, photo, posture form, or fitness scene to generate.
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"High quality realistic fitness photo: {prompt}",
    )

    part_data = response.candidates[0].content.parts[0]
    image_bytes = part_data.inline_data.data
    mime_type = part_data.inline_data.mime_type or "image/jpeg"
    filename = f"exercise_{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public GCS bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"


def convert_video_bytes_to_gif(video_bytes: bytes, max_fps: int = 10, max_width: int = 480) -> bytes:
    """Converts mp4/webm video bytes into an optimized looping GIF byte sequence."""
    try:
        reader = imageio.get_reader(video_bytes, format="mp4")
        frames = []
        for i, frame in enumerate(reader):
            if i % 2 == 0:
                img = Image.fromarray(frame)
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    height = int(float(img.height) * ratio)
                    img = img.resize((max_width, height), Image.Resampling.LANCZOS)
                frames.append(img)
        reader.close()
        if frames:
            output = io.BytesIO()
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=int(1000 / max_fps),
                loop=0,
            )
            return output.getvalue()
    except Exception as e:
        print(f"Warning: Failed to convert video bytes to GIF: {e}")
    return None


def generate_exercise_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short fitness animation video/GIF demonstration for an exercise or workout using gemini-omni-flash-preview in the global region.

    Converts the video into an animated GIF, saves it as a Playground artifact, and uploads the GIF bytes directly to Cloud Storage.

    Args:
        prompt: Description of the exercise visual or workout movement to generate.
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        The public HTTPS URL of the uploaded animated GIF in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    res = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short video of: {prompt}",
    )

    video_bytes = None
    mime_type = "video/mp4"

    # 1. Check res.output_video
    output_vid = getattr(res, "output_video", None)
    if output_vid:
        data = getattr(output_vid, "data", None) or getattr(output_vid, "bytes", None) or getattr(output_vid, "content", None)
        mime_type = getattr(output_vid, "mime_type", None) or "video/mp4"
        if isinstance(data, str):
            try:
                video_bytes = base64.b64decode(data)
            except Exception:
                video_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            video_bytes = data

    # 2. Check res.output / outputs array
    if not video_bytes:
        outputs = getattr(res, "output", None) or getattr(res, "outputs", None) or []
        if not outputs and isinstance(res, dict):
            outputs = res.get("output") or res.get("outputs") or []

        for item in outputs:
            item_type = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
            if item_type == "video":
                raw_data = getattr(item, "data", None) or (item.get("data") if isinstance(item, dict) else None)
                mime_type = getattr(item, "mime_type", None) or (item.get("mime_type") if isinstance(item, dict) else "video/mp4") or "video/mp4"
                if isinstance(raw_data, str):
                    try:
                        video_bytes = base64.b64decode(raw_data)
                    except Exception:
                        video_bytes = raw_data.encode("utf-8")
                elif isinstance(raw_data, bytes):
                    video_bytes = raw_data
                break

    if not video_bytes:
        raise RuntimeError("No video bytes returned from gemini-omni-flash-preview model.")

    want_gif = "gif" in prompt.lower() or "animat" in prompt.lower()
    if want_gif:
        gif_bytes = convert_video_bytes_to_gif(video_bytes)
        if gif_bytes:
            final_bytes = gif_bytes
            mime_type = "image/gif"
            ext = "gif"
        else:
            final_bytes = video_bytes
            mime_type = "video/mp4"
            ext = "mp4"
    else:
        final_bytes = video_bytes
        mime_type = "video/mp4"
        ext = "mp4"

    filename = f"exercise_video_{uuid.uuid4().hex[:8]}.{ext}"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=final_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload bytes directly to public GCS bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(final_bytes, content_type=mime_type)

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it to get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

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


# Load Agent Engine resource name from deployment_metadata.json if present
metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
agent_engine_resource_name = None
if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

MEMORY_BANK_ID = "7915206087475724288"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract and send session events to Vertex AI Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        pass
    return None


def memory_service_builder():
    """Builder for VertexAiMemoryBankService when deploying to Agent Runtime."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are fit-coach, an expert fitness assistant. Use your tools to lookup exercises, retrieve exercise details, log workout sessions, fetch motivational quotes, generate exercise visual illustrations and videos for requested exercises, and manage the exercise catalog. You also have code execution capabilities to run Python code safely in a sandbox when needed for complex calculations.",
    workflow_description="Analyze the user request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "CRITICAL MEMORY REQUIREMENT: You remember all user stated facts, preferences, medical conditions, and ALLERGIES from previous conversations. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_exercises,
        get_exercise_details,
        add_exercise,
        log_workout_session,
        get_daily_motivation,
        generate_exercise_image,
        generate_exercise_video,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
