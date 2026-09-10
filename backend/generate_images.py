import pandas as pd
from pathlib import Path
import hashlib
import random


BASE_DIR = Path(__file__).resolve().parent.parent

PROJECT_FILE = BASE_DIR / "data" / "projects.csv"
IMAGE_FILE = BASE_DIR / "data" / "project_images.csv"


def generate_images():

    projects = pd.read_csv(PROJECT_FILE)

    images = []

    random.seed(42)

    for index, project in projects.iterrows():

        project_id = str(project["project_id"])

        latitude = project["latitude"]
        longitude = project["longitude"]

        # Normally every project gets one image
        image_id = f"IMG{index + 1:05d}"

        image_path = (
            f"evidence/images/{image_id}.jpg"
        )

        # Create a deterministic image hash
        image_hash = hashlib.md5(
            project_id.encode()
        ).hexdigest()

        similarity_score = 0.0

        status = "Valid"

        # Synthetic reused-image scenarios
        if index % 60 == 0:

            image_hash = hashlib.md5(
                b"REUSED_DEMO_IMAGE"
            ).hexdigest()

            similarity_score = 0.95

            status = "Potentially Reused"

        images.append({
            "image_id": image_id,
            "project_id": project_id,
            "image_path": image_path,
            "latitude": latitude,
            "longitude": longitude,
            "upload_date": project["start_date"],
            "image_hash": image_hash,
            "similarity_score": similarity_score,
            "status": status
        })

    images_df = pd.DataFrame(images)

    images_df.to_csv(
        IMAGE_FILE,
        index=False
    )

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       IMAGE DATA GENERATION")
    print("==========================================")

    print(
        "\nImages generated:",
        len(images_df)
    )

    print("\nSaved to:")
    print(IMAGE_FILE)

    print("\nPotentially reused images:")

    print(
        (images_df["status"] == "Potentially Reused").sum()
    )

    print("\nSample image records:\n")

    print(
        images_df.head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    generate_images()