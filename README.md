# FitCoach AI

FitCoach AI is an intelligent, personalized AI fitness and workout assistant built on the **Google Agent Development Kit (ADK)** and deployed on **Google Cloud Vertex AI Agent Runtime**. 

![FitCoach AI Demo](demo.gif)

---

## ⚡ Key Capabilities & Implemented Tools

FitCoach AI connects to Google Cloud services and specialized tools implemented in `app/agent.py`:

* **🧠 Persistent Memory (Vertex AI Memory Bank)**
  * Uses `VertexAiMemoryBankService` and `PreloadMemoryTool` to remember user-stated fitness goals, medical conditions, preferences, and dietary allergies across conversation sessions.
* **🏋️ Exercise Catalog & Workout Logger (Google Cloud Firestore)**
  * `list_exercises`: Queries exercises filtered by category (e.g., Strength, Bodyweight, Core).
  * `get_exercise_details`: Retrieves execution details, target muscles, and recommended sets/reps.
  * `add_exercise`: Adds custom exercises directly into the Firestore catalog.
  * `log_workout_session`: Records completed workout logs (sets, reps, weight, duration, notes) to Firestore.
* **📸 Exercise Photo Generation (Vertex AI Image Generation)**
  * `generate_exercise_image`: Generates realistic posture illustration photos using `gemini-3.1-flash-lite-image` in the `global` region, saves them to Playground Artifacts, and uploads them to Google Cloud Storage.
* **🎥 Exercise Video Generation (Vertex AI Omni Model)**
  * `generate_exercise_video`: Generates short movement videos using `gemini-omni-flash-preview` in the `global` region, saves them as Playground Artifacts, and uploads them to Google Cloud Storage.
* **🗄️ Media Storage (Google Cloud Storage)**
  * Stores generated exercise posture photos and video clips in a public GCS bucket (`fit-coach-media-c8c5574b200d`) for inline rendering.
* **🎛️ Agent-to-User Interface (A2UI v0.8)**
  * Formats workout routines and exercise cards using `A2uiSchemaManager` (v0.8) and `a2ui_callback` into flat UI components (`Card`, `Column`, `Row`, `Text`, `Image`).
* **💻 Strength & Health Calculations (Agent Engine Sandbox Code Executor)**
  * Uses `AgentEngineSandboxCodeExecutor` to safely run Python code for complex One-Rep Max (1RM) calculations and target heart rate zone estimations.
* **🔥 Daily Motivation & Utilities**
  * `get_daily_motivation`: Fetches motivational fitness quotes.
  * `get_weather` & `get_current_time`: Helper tools for outdoor workout planning.

---

## 📋 Feature Status

| Feature / Integration | Implementation Status |
| :--- | :--- |
| Firestore Exercise Catalog & Activity Logs | ✅ Implemented |
| Vertex AI Memory Bank | ✅ Implemented |
| A2UI v0.8 Structured Cards | ✅ Implemented |
| Imagen Posture Photo Generation | ✅ Implemented |
| Omni Model Movement Video Generation | ✅ Implemented |
| GCS Media Bucket Uploads | ✅ Implemented |
| Sandbox Code Executor (1RM Calculations) | ✅ Implemented |
| Automated Meal Calorie Barcode Scanner | ⏳ Planned, not yet implemented |

---

## 🚀 Local Setup & Running Instructions

### Prerequisites
* Python 3.11+
* Google Cloud CLI (`gcloud`) authenticated with Application Default Credentials (`gcloud auth application-default login`)

### Installation & Execution

1. **Clone & Set Up Virtual Environment**:
   ```bash
   git clone <repository-url>
   cd fit-coach
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r frontend/requirements.txt
   ```

2. **Configure Environment Variables**:
   Set required project credentials:
   ```bash
   export GOOGLE_CLOUD_PROJECT="qwiklabs-gcp-03-c8c5574b200d"
   export GOOGLE_CLOUD_LOCATION="us-east1"
   export GOOGLE_GENAI_USE_VERTEXAI="true"
   export AGENT_DIRECTORY="app"
   ```

3. **Start Local Agent Backend**:
   ```bash
   uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
   ```

4. **Start Local Frontend Web UI**:
   In a separate terminal session:
   ```bash
   cd frontend
   python main.py
   ```
