import requests
import pandas as pd
from google.cloud import bigquery
from google.cloud import storage
import os
import json
from datetime import datetime

# -----------------------------------
# Configuration from environment vars
# -----------------------------------
PROJECT_ID = os.getenv("PROJECT_ID", "du-data-490720")
DATASET = os.getenv("DATASET", "du_operational")
TABLE = os.getenv("TABLE", "du_university_chapters")
BUCKET_NAME = os.getenv("BUCKET_NAME", "du_ingestion_data")

# API URL for Ducks Unlimited university chapters
API_URL = (
    "https://services2.arcgis.com/5I7u4SJE1vUr79JC/arcgis/rest/services/"
    "UniversityChapters_Public/FeatureServer/0/query?"
    "where=1%3D1&outFields=*&outSR=4326&f=json"
)

# -----------------------------------
# Step 1: Fetch data from API
# -----------------------------------
def fetch_api_data():
    """
    Fetch JSON data from the ArcGIS API.
    """
    response = requests.get(API_URL, timeout=60)
    response.raise_for_status()
    return response.json()


# -----------------------------------
# Step 2: Save raw JSON to GCS
# -----------------------------------
def upload_to_gcs(data):
    """
    Upload raw API response JSON to Google Cloud Storage
    for raw zone / audit / debugging purpose.
    """
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"raw/api_data_{timestamp}.json"

    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        json.dumps(data),
        content_type="application/json"
    )

    return f"gs://{BUCKET_NAME}/{blob_name}"


# -----------------------------------
# Step 3: Transform JSON to DataFrame
# -----------------------------------
def transform_data(data):
    """
    Flatten API response into a pandas DataFrame.

    Extracts:
    - object_id
    - chapter_id
    - chapter_name
    - city
    - state
    - longitude
    - latitude
    - ingestion_time

    Longitude comes from geometry.x
    Latitude comes from geometry.y
    """
    features = data.get("features", [])

    if not features:
        print("No features found in API response.")
        return pd.DataFrame()

    ingestion_ts = datetime.now()
    records = []

    for feature in features:
        attributes = feature.get("attributes", {}) or {}
        geometry = feature.get("geometry", {}) or {}

        records.append({
            "object_id": attributes.get("OBJECTID"),
            "chapter_id": attributes.get("ChapterID"),
            "chapter_name": attributes.get("University_Chapter"),
            "city": attributes.get("City"),
            "state": attributes.get("State"),
            "longitude": geometry.get("x"),
            "latitude": geometry.get("y"),
            "ingestion_time": ingestion_ts
        })

    df = pd.DataFrame(records)
    return df


# -----------------------------------
# Step 4: Load DataFrame to BigQuery
# -----------------------------------
def load_to_bigquery(df):
    """
    Load DataFrame into BigQuery.

    WRITE_TRUNCATE means:
    - delete existing table data
    - load fresh data from current run

    autodetect=True means:
    - if table does not exist, BigQuery can create it automatically
    - schema is inferred from pandas DataFrame
    """
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    return f"Loaded {len(df)} rows into {table_id}"


# -----------------------------------
# Main ETL flow
# -----------------------------------
def run():
    """
    Main ETL flow:
    1. Fetch data from API
    2. Save raw JSON to GCS
    3. Transform JSON to structured DataFrame
    4. Refresh BigQuery table with latest full snapshot
    """
    print(f"Starting ingestion for project: {PROJECT_ID}")

    # Fetch API response
    data = fetch_api_data()

    # Save raw JSON to GCS
    gcs_path = upload_to_gcs(data)
    print(f"Raw JSON uploaded to: {gcs_path}")

    # Transform data
    df = transform_data(data)

    if df.empty:
        print("No data found to load into BigQuery.")
        return

    # Load to BigQuery
    result = load_to_bigquery(df)
    print(result)

    # Print sample rows for verification
    print(df.head())


# -----------------------------------
# Run script
# -----------------------------------
if __name__ == "__main__":
    run()