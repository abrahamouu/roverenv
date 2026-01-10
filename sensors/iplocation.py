import requests
import time

def get_location():
    try:
        # Query the IP geolocation API
        response = requests.get("http://ip-api.com/json/")
        data = response.json()

        if data["status"] == "success":
            lat = data["lat"]
            lon = data["lon"]
            city = data.get("city", "Unknown")
            country = data.get("country", "Unknown")
            print(f"Location found: {lat}, {lon}")
            print(f"City: {city}, Country: {country}")
            return lat, lon
        else:
            print("Failed to get location:", data.get("message", "Unknown error"))
            return None, None

    except requests.RequestException as e:
        print("Error connecting to the geolocation service:", e)
        return None, None

if __name__ == "__main__":
    interval = 2

    print("Starting IP location sensor. Press Ctrl+C to stop.")
    while True:
        lat, lon = get_location()
        time.sleep(interval)
