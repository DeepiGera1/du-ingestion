import requests
import pandas as pd
import os
import json
from datetime import datetime

# -------------------------------
# Configuration
# -------------------------------
API_URL = "https://services2.arcgis.com/5I7u4SJE1vUr79JC/arcgis/rest/services/UniversityChapters_Public/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json"
LOCAL_RAW_FOLDER = "raw_data"       # Folder to save raw JSON
LOCAL_CURATED_FOLDER = "curated_data"  # Folder to save CSV

# Create folders if they don't exist
os.makedirs(LOCAL_RAW_FOLDER, exist_ok=True)
os.makedirs(LOCAL_CURATED_FOLDER, exist_ok=True)


# -------------------------------
# Step 1: Fetch API data
# -------------------------------
def fetch_api_data():
    """
    Fetch data from ArcGIS API and return JSON.
    Returns empty features list if JSON decode fails.
    """
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Raise error if HTTP status is not 2xx
        data = response.json()
        return data
    except json.JSONDecodeError:
        print("Warning: API did not return valid JSON. Returning empty data.")
        return {"features": []}
    except requests.RequestException as e:
        print(f"Error fetching API: {e}")
        return {"features": []}


# -------------------------------
# Step 2: Save raw JSON locally
# -------------------------------
def upload_to_local(data):
    """
    Save raw JSON locally with a timestamped filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(LOCAL_RAW_FOLDER, f"api_data_{timestamp}.json")

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    return file_path


# -------------------------------
# Step 3: Transform JSON → DataFrame
# -------------------------------
def transform_data(data):
    """
    Normalize ArcGIS JSON features into a flat DataFrame
    Each feature has an 'attributes' dict that we extract
    """
    features = data.get("features", [])
    attributes = [f.get("attributes", {}) for f in features]

    if not attributes:
        print("No features found in API response.")
        return pd.DataFrame()  # Return empty DataFrame

    df = pd.json_normalize(attributes)
    df["ingestion_time"] = datetime.now()  # Add ingestion timestamp
    return df


# -------------------------------
# Step 4: Save DataFrame locally as CSV
# -------------------------------
def load_to_local_csv(df):
    """
    Save DataFrame as CSV locally with timestamped filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(LOCAL_CURATED_FOLDER, f"api_data_{timestamp}.csv")
    df.to_csv(file_path, index=False)
    return file_path


# -------------------------------
# Main ETL flow
# -------------------------------
def main_local():
    print("Starting local ETL pipeline...")

    # Step 1: Fetch API data
    data = fetch_api_data()

    # Step 2: Save raw JSON locally
    raw_file = upload_to_local(data)
    print(f"Raw JSON saved at: {raw_file}")

    # Step 3: Transform JSON to DataFrame
    df = transform_data(data)

    # Step 4: Save curated CSV locally
    if not df.empty:
        curated_file = load_to_local_csv(df)
        print(f"Curated CSV saved at: {curated_file}")
    else:
        print("No data to save to CSV.")

    print("Local ETL pipeline completed.")


# -------------------------------
# Run the ETL locally
# -------------------------------
if __name__ == "__main__":
    main_local()