# Copyright 2026 Google LLC
# Seed script for fit-coach Firestore database.

from google.cloud import firestore

# CRITICAL: Project ID is hardcoded to avoid Agent Platform project number issue
PROJECT_ID = "qwiklabs-gcp-03-c8c5574b200d"

INITIAL_EXERCISES = [
    {
        "id": "pushups",
        "name": "Push-Ups",
        "category": "Bodyweight",
        "target_muscle": "Chest & Triceps",
        "difficulty": "Beginner",
        "recommended_sets": 3,
        "recommended_reps": "15-20",
        "calories_burned_per_min": 7,
        "description": "Standard upper body bodyweight exercise focusing on chest, shoulders, and triceps strength.",
    },
    {
        "id": "barbell_squat",
        "name": "Barbell Back Squat",
        "category": "Strength",
        "target_muscle": "Quadriceps & Glutes",
        "difficulty": "Intermediate",
        "recommended_sets": 4,
        "recommended_reps": "8-12",
        "calories_burned_per_min": 10,
        "description": "Compound lower body exercise utilizing a barbell placed across the upper back.",
    },
    {
        "id": "pullups",
        "name": "Pull-Ups",
        "category": "Bodyweight",
        "target_muscle": "Back & Biceps",
        "difficulty": "Intermediate",
        "recommended_sets": 3,
        "recommended_reps": "8-10",
        "calories_burned_per_min": 8,
        "description": "Upper body pulling exercise targeting the latissimus dorsi, rhomboids, and biceps.",
    },
    {
        "id": "plank",
        "name": "Forearm Plank",
        "category": "Core",
        "target_muscle": "Abs & Core",
        "difficulty": "Beginner",
        "recommended_sets": 3,
        "recommended_reps": "60 seconds",
        "calories_burned_per_min": 4,
        "description": "Isometric core endurance exercise maintaining a push-up position on forearms.",
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("exercises")

    for item in INITIAL_EXERCISES:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"  - Seeded exercise: {item['name']} (ID: {item['id']})")

    print(f"Successfully seeded {len(INITIAL_EXERCISES)} exercises into Firestore!")


if __name__ == "__main__":
    seed_database()
