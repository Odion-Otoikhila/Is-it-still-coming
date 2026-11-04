import requests
import zipfile
import io
import os

URL = "https://www.transportforireland.ie/transitData/Data/GTFS_All.zip"

def download_gtfs():
    if os.path.exists("gtfs/trips.txt"):
        print("GTFS data already downloaded")
        return

    print("Downloading GTFS data...")

    response = requests.get(URL, timeout=120)
    response.raise_for_status()

    os.makedirs("gtfs", exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        zip_file.extractall("gtfs")

    print("GTFS data downloaded!")

if __name__ == "__main__":
    download_gtfs()
