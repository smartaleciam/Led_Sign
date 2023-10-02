import RPi.GPIO as GPIO
import os
from datetime import datetime
import subprocess
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
#from gsmmodem import GsmModem
from ftplib import FTP

app = Flask(__name__)

# Setup GPIO's
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
button = 20
senPIR = 16
buttonSts = GPIO.LOW
senPIRSts = GPIO.LOW
# Set button and PIR sensor pins as an input
GPIO.setup(button, GPIO.IN)   
GPIO.setup(senPIR, GPIO.IN)


# Initialize the SIM7600G-H modem
#modem = GsmModem('/dev/ttyUSB2')  # Replace with the correct serial port
#modem.connect()

# FTP server settings
ftp_host = 'ftp.example.com'  # Replace with your FTP server's host
ftp_user = 'your_ftp_username'
ftp_password = 'your_ftp_password'

# UFW Firewall Status
potential_attacks = []
def get_ufw_status():
    try:
        result = subprocess.check_output(['ufw', 'status'], universal_newlines=True)
        return result
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def analyze_logs():
    # Read UFW logs (adjust the log file path as needed)
    log_file_path = '/var/log/ufw.log'
    with open(log_file_path, 'r') as log_file:
        log_lines = log_file.readlines()

    # Define a regular expression pattern to identify potential attacks
    attack_pattern = r'UFW BLOCK.*SRC=([\d.]+)'

    for line in log_lines:
        match = re.search(attack_pattern, line)
        if match:
            potential_attacks.append(match.group(1))
################################################################

@app.route('/')
def home():
    # Read Sensors Status
    buttonSts = GPIO.input(button)
    senPIRSts = GPIO.input(senPIR)
    templateData = {
        'button'  : buttonSts,
        'senPIR'  : senPIRSts,
    }
    return render_template('index.html', **templateData)

@app.route('/get_firewall_status')
def get_firewall_status():
    ufw_status = get_ufw_status()
    return ufw_status

@app.route('/get_firewall_attacks')
def get_firewall_attacks():
    return jsonify(potential_attacks)

@app.route('/get_marker_locations')
def get_marker_locations():
#    data = request.json  # Assuming data is sent as JSON
    data = [
        {'latitude': '-35.1402308', 'longitude': '139.2871538', 'label': '<b>Led Sign</b><hr>Signal : <br>Battery : <br>Status : <br>Last : '},
        {'latitude': '-35.1402308', 'longitude': '139.28', 'label': '<b>Generator</b><hr>Signal : <br>Battery : <br>Status : <br>Last : '},
        {'latitude': '-35.1402308', 'longitude': '139.29', 'label': '<b>Light Tower</b><hr>Signal : <br>Battery : <br>Status : <br>Last : '},
    ]
    return jsonify(data)

@app.route('/send_sms')
def send_sms():
    
    return render_template('send_sms.html')

@app.route('/sending_sms', methods=['POST'])
def sending_sms():
    recipient = request.form['recipient']
    message_body = request.form['message']
    modem.sendSms(recipient, message_body)
    
    return ('Message sent successfully')

@app.route('/receive_sms')
def receive_sms():
#    messages = modem.listStoredSms()
    messages = 'hello'
    return render_template('receive_sms.html', messages=messages)

@app.route('/update_gps', methods=['POST'])
def update_gps():
    data = request.json  # Assuming data is sent as JSON
    latitude = data['latitude']
    longitude = data['longitude']
    
    # Process and store GPS data as needed (e.g., in a database)

    return jsonify({"message": "GPS data received successfully"})

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            with FTP(ftp_host) as ftp:
                ftp.login(ftp_user, ftp_password)
                ftp.storbinary('STOR ' + uploaded_file.filename, uploaded_file)
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return 'File uploaded successfully'
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
