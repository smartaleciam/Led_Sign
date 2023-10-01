 
import time
import json
import requests
from gps import gps, WATCH_ENABLE

# Initialize the GPSD client
session = gps.gps("localhost", "2947")
session.stream(WATCH_ENABLE | WATCH_ENABLE_JSON)

# Define your API endpoint URL
api_url = "https://your-api-website.com/endpoint"

try:
    while True:
        report = session.next()
        if report['class'] == 'TPV':
            latitude = report.get('lat', 0.0)
            longitude = report.get('lon', 0.0)
            
            # Create a JSON payload with GPS data
            gps_data = {
                "latitude": latitude,
                "longitude": longitude
            }
            
            # Send GPS data to your API
            headers = {'Content-Type': 'application/json'}
            response = requests.post(api_url, data=json.dumps(gps_data), headers=headers)
            
            if response.status_code == 200:
                print(f"GPS data sent successfully: {json.dumps(gps_data)}")
            else:
                print(f"Failed to send GPS data. Status code: {response.status_code}")
            
        time.sleep(1)

except KeyboardInterrupt:
    print("GPS data sending stopped.")
    session.close()
