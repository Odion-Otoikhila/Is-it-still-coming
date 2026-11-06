
import os
import csv
import requests
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

load_dotenv("api_key.env")

api_key = os.getenv("TFI_API_KEY")

if not api_key:
    raise ValueError("Missing TFI_API_KEY")

url = "https://api.nationaltransport.ie/gtfsr/v2/Vehicles"

headers = {
    "x-api-key": api_key
}

response = requests.get(url, headers=headers, timeout=15)
print("Status:", response.status_code)
response.raise_for_status()

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

print("Live vehicles:", len(feed.entity))

# Load static trips
static_dic = {}

<<<<<<< Updated upstream
with open("gtfs/trips.txt") as file:
	trips = file.readlines()

static_dic = {}

for trip in trips:
	trip = trip.strip().split()
	static_dic[trip[-1]] = trip[0:-1]
	#time.sleep(0.5)

print(static_dic)

#for entity in feed.entity:
#    if entity.HasField("vehicle"):
#        print(entity.vehicle.trip)
    
=======
with open("gtfs/trips.txt", newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for trip in reader:
        static_dic[trip["trip_id"]] = trip

print("Static trips:", len(static_dic))

# Match live vehicles to static trips
for entity in feed.entity:
    if not entity.HasField("vehicle"):
        continue

    vehicle = entity.vehicle
    trip_id = vehicle.trip.trip_id

    if trip_id in static_dic:
        trip_info = static_dic[trip_id]

        print("Vehicle:", vehicle.vehicle.id)
        print("Route:", trip_info["route_id"])
        print("Trip:", trip_id)
        print("Latitude:", vehicle.position.latitude)
        print("Longitude:", vehicle.position.longitude)
        print("----------------------")

>>>>>>> Stashed changes
