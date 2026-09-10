import pandas as pd
from pathlib import Path
import random


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Input and output files
PROJECT_FILE = BASE_DIR / "data" / "projects.csv"
DOCUMENT_FILE = BASE_DIR / "data" / "documents.csv"


def generate_documents():

    # Load project data
    projects = pd.read_csv(PROJECT_FILE)

    documents = []

    document_types = [
        "Sanction Letter",
        "Utilization Certificate",
        "Completion Certificate",
        "Inspection Report"
    ]

    random.seed(42)

    for index, project in projects.iterrows():

        project_id = project["project_id"]

        # Choose one document type for each project
        document_type = document_types[
            index % len(document_types)
        ]

        # Normally the document amount matches
        amount = project["utilized_amount"]

        contractor = project["contractor"]

        location = (
            str(project["district"])
            + ", "
            + str(project["state"])
        )

        status = project["status"]

        # Introduce synthetic mismatches
        # for demonstration purposes.
        if index % 50 == 0:
            amount = amount * 1.25

        if index % 75 == 0:
            contractor = "Different Contractor"

        if index % 100 == 0:
            location = "Different Location"

        documents.append({
            "document_id": f"DOC{index + 1:05d}",
            "project_id": project_id,
            "document_type": document_type,
            "document_date": project["sanction_date"],
            "amount": amount,
            "contractor": contractor,
            "location": location,
            "file_path": "",
            "extracted_text": (
                f"Document for project {project_id}. "
                f"Type: {document_type}. "
                f"Amount: {amount}. "
                f"Contractor: {contractor}. "
                f"Location: {location}."
            ),
            "status": status
        })

    documents_df = pd.DataFrame(documents)

    documents_df.to_csv(
        DOCUMENT_FILE,
        index=False
    )

    print("\n==========================================")
    print("       MPLAD-GUARD AI")
    print("   DOCUMENT DATA GENERATION")
    print("==========================================")

    print("\nDocuments generated:", len(documents_df))

    print("\nSaved to:")
    print(DOCUMENT_FILE)

    print("\nSample documents:\n")

    print(
        documents_df.head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    generate_documents()