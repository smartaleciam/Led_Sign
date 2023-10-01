 
from flask import Flask, request, jsonify

app = Flask(__name__)

# Route to receive GPS data
@app.route('/update_gps', methods=['POST'])
def update_gps():
    data = request.json  # Assuming data is sent as JSON
    latitude = data['latitude']
    longitude = data['longitude']
    
    # Process and store GPS data as needed (e.g., in a database)

    return jsonify({"message": "GPS data received successfully"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
