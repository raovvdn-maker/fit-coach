import glob
import os
import time
import uuid
from google.cloud import storage
from playwright.sync_api import sync_playwright

PROJECT_ID = "qwiklabs-gcp-03-c8c5574b200d"
GCS_BUCKET_NAME = "fit-coach-media-c8c5574b200d"
FRONTEND_URL = "https://fit-coach-frontend-301517884346.us-east1.run.app"
VIDEO_DIR = "demo_videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

def record_demo():
    print("Starting Playwright demo recording...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        
        page = context.new_page()
        
        print(f"Navigating to {FRONTEND_URL}...")
        page.goto(FRONTEND_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # Step 1: Click the first quick prompt chip
        print("Executing Demo Step 1: Requesting workout routine...")
        chip1 = page.locator(".prompt-chip").first
        if chip1.is_visible():
            chip1.click()
        else:
            page.fill("#input", "Generate a chest & triceps workout routine with exercise cards")
            page.locator("#form").evaluate("f => f.requestSubmit()")
            
        print("Waiting for Agent response 1...")
        page.wait_for_selector(".msg.agent", timeout=30000)
        # Wait until typing dots are hidden
        page.wait_for_selector(".typing-dots", state="hidden", timeout=30000)
        time.sleep(6)
        
        # Step 2: Richer prompt showing tool calls, database lookup & image generation
        print("Executing Demo Step 2: Requesting exercise photo & 1RM calculation...")
        prompt2 = "Show me a photo illustration for proper squat posture and calculate my 1RM bench press for 185 lbs at 6 reps"
        
        input_el = page.locator("#input")
        input_el.click()
        for char in prompt2:
            input_el.type(char, delay=20)
            
        time.sleep(0.5)
        page.locator("#form").evaluate("f => f.requestSubmit()")
        
        print("Waiting for Agent response 2 (Image generation & code execution)...")
        # Wait until 2 agent message bubbles are present
        page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 2", timeout=45000)
        page.wait_for_selector(".typing-dots", state="hidden", timeout=45000)
        time.sleep(8)
        
        print("Finishing demo recording...")
        page_video = page.video
        video_path = page_video.path() if page_video else None
        
        context.close()
        browser.close()
        
        print(f"Recorded video saved locally at: {video_path}")
        return video_path

def upload_and_save_video(local_video_path):
    if not local_video_path or not os.path.exists(local_video_path):
        vids = glob.glob(os.path.join(VIDEO_DIR, "*.webm"))
        if vids:
            local_video_path = vids[-1]

    if not local_video_path or not os.path.exists(local_video_path):
        raise FileNotFoundError("Recorded video file not found.")

    with open(local_video_path, "rb") as f:
        video_bytes = f.read()

    filename = f"fitcoach_demo_{uuid.uuid4().hex[:8]}.webm"

    # Upload to Cloud Storage
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type="video/webm")
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    print(f"Demo video uploaded to Cloud Storage: {public_url}")
    return public_url, local_video_path

if __name__ == "__main__":
    vid_path = record_demo()
    public_url, path = upload_and_save_video(vid_path)
    print("DEMO RECORDING COMPLETE!")
