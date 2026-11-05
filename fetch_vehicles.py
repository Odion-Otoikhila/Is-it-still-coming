import os
import requests
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2
import time 

load_dotenv("api_key.env")

api_key = os.getenv("TFI_API_KEY")

url = "https://api.nationaltransport.ie/gtfsr/v2/Vehicles"

headers = {
    "x-api-key": api_key
}

response = requests.get(url, headers=headers, timeout=15)


print("Status:", response.status_code)

response.raise_for_status()

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

#print("Status:", response.status_code)
#print("Retry-After:", response.headers.get("Retry-After"))
#print("Response:", response.text[:500])

print(len(feed.entity))

with open("gtfs/trips.txt") as file:
	trips = file.readlines()

for trip in trips:
	print(trip)
	time.sleep(0.5)

#for entity in feed.entity:
    #if entity.HasField("vehicle"):
        #print(entity.vehicle.trip)
    
