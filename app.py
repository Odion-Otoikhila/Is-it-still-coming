
import os
import time
import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

load_dotenv("api_key.env")

app = Flask(__name__)
API_KEY = os.getenv("TFI_API_KEY")
URL = "https://api.nationaltransport.ie/gtfsr/v2/Vehicles"

cache = {"data": [], "time": 0}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/vehicles")
def vehicles():
    # Cache data so repeated requests don't hit TFI unnecessarily

    try:
        response = requests.get(
            URL,
            headers={"x-api-key": API_KEY},
            timeout=15
        )
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        buses = []

        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue

            vehicle = entity.vehicle

            if not vehicle.HasField("position"):
                continue

            buses.append({
                "id": vehicle.vehicle.id or entity.id,
                "route": vehicle.trip.route_id,
                "trip_id": vehicle.trip.trip_id,
                "lat": vehicle.position.latitude,
                "lon": vehicle.position.longitude,
                "speed": vehicle.position.speed if vehicle.position.HasField("speed") else None,
                "bearing": vehicle.position.bearing if vehicle.position.HasField("bearing") else None,
                "timestamp": int(vehicle.timestamp) if vehicle.HasField("timestamp") else None
            })

        cache["data"] = buses
        cache["time"] = time.time()

        return jsonify(buses)

    except requests.RequestException as error:
        return jsonify({"error": str(error)}), 502

import route_paths
route_paths.install(app)


# TFI RATE LIMIT FIX
import time
import threading
from flask import request, make_response, jsonify

tfi_lock = threading.Lock()
last_attempt = 0
last_good_data = None
INTERVAL = 65

@app.before_request
def check_tfi_cache():
    global last_attempt

    if request.path != "/api/vehicles":
        return None

    with tfi_lock:
        now = time.monotonic()

        if now - last_attempt < INTERVAL:
            if last_good_data is not None:
                response = make_response(last_good_data, 200)
                response.mimetype = "application/json"
                response.headers["X-Feed-Status"] = "cached"
                response.headers["Cache-Control"] = "no-store"
                return response

            return jsonify({"error": "Waiting for TFI"}), 503

        last_attempt = now

@app.after_request
def save_tfi_response(response):
    global last_good_data

    if request.path != "/api/vehicles":
        return response

    if response.headers.get("X-Feed-Status"):
        return response

    with tfi_lock:
        data = response.get_json(silent=True)

        if response.status_code == 200 and isinstance(data, list):
            last_good_data = response.get_data()
            response.headers["X-Feed-Status"] = "fresh"

        elif last_good_data is not None:
            response = make_response(last_good_data, 200)
            response.mimetype = "application/json"
            response.headers["X-Feed-Status"] = "stale"

    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    if not API_KEY:
        raise ValueError("Missing TFI_API_KEY")
    app.run(debug=True)

