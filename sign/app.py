import RPi.GPIO as GPIO
import os
import datetime
import time
import subprocess
import re
import eventlet
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO
#from gsmmodem import GsmModem
from ftplib import FTP
import psutil
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import paho.mqtt.client as mqtt
from flask_fontawesome import FontAwesome

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MontyPython_secret_key'
socketio = SocketIO(app, async_mode='gevent')  # Use Gevent async mode
fa = FontAwesome(app)

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

log_file_path = '/var/log/ufw.log'

# Initialize the SIM7600G-H modem
#modem = GsmModem('/dev/ttyUSB2')  # Replace with the correct serial port
#modem.connect()

# FTP server settings
ftp_host = 'ftp.signs.smartaleclights.com'  # Replace with your FTP server's host
ftp_user = 'your_ftp_username'
ftp_password = 'your_ftp_password'

# MQTT configuration
mqtt_broker = "localhost"
mqtt_port = 1883
mqtt_topic = "#"

# MQTT on_connect callback
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code %d" % rc)
    client.subscribe(mqtt_topic)

# MQTT on_message callback
def on_message(client, userdata, message):
    mqtt_data = message.payload.decode()
    socketio.emit('mqtt_data', mqtt_data)

# Initialize the MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

# UFW Firewall Status
potential_attacks = []
def get_ufw_status():
    try:
        result = subprocess.check_output(['sudo','ufw', 'status'], universal_newlines=True)
        return result
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def analyze_logs():
    # Read UFW logs (adjust the log file path as needed)
    with open(log_file_path, 'r') as log_file:
        log_lines = log_file.readlines()

    # Define a regular expression pattern to identify potential attacks
    attack_pattern = r'UFW BLOCK.*SRC=([\d.]+)'

    for line in log_lines:
        match = re.search(attack_pattern, line)
        if match:
            potential_attacks.append(match.group(1))

def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return(res.replace("temp=","").replace("'C\n",""))

def getRAMinfo():
    p = os.popen('free')
    i = 0
    while 1:
        i = i + 1
        line = p.readline()
        if i==2:
            return(line.split()[1:4])

# Return % of CPU used by user as a character string                                
def getCPUuse():
    return(str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip(\
)))

def getDiskSpace():
    p = os.popen("df -h /")
    i = 0
    while 1:
        i = i +1
        line = p.readline()
        if i==2:
            return(line.split()[1:5])

def update_stats():
    while True:
        current_time = datetime.datetime.utcnow().strftime('%H:%M:%S')
        socketio.emit('update_time', current_time)
        cpu_temp = getCPUtemperature()
        socketio.emit('cpu_temp', cpu_temp)
        cpu_usage = getCPUuse()
        socketio.emit('cpu_usage', cpu_usage)
        DISK_stats = getDiskSpace()
        disk_left = DISK_stats[2]
        socketio.emit('disk_free', disk_left)

        socketio.sleep(1)  # Emit updates every second

################################################################

@app.route('/')
def home():
    # Read Sensors Status
    buttonSts = GPIO.input(button)
    senPIRSts = GPIO.input(senPIR)
    DISK_space = getDiskSpace()
    # Output is in kb, here I convert it in Mb for readability
    RAM_stats = getRAMinfo()
    RAM_total = round(int(RAM_stats[0]) / 1000,1)
    RAM_used = round(int(RAM_stats[1]) / 1000,1)
    RAM_free = round(int(RAM_stats[2]) / 1000,1)

    # Disk information
    DISK_stats = getDiskSpace()
    DISK_total = DISK_stats[0]
    DISK_used = DISK_stats[1]
    DISK_left = DISK_stats[2]
    DISK_perc = DISK_stats[3]

    # Get disk usage statistics
    disk_usage = psutil.disk_usage('/')

    # Create a bar chart
    labels = ['Total', 'Used', 'Free']
    sizes = [disk_usage.total, disk_usage.used, disk_usage.free]

    fig, ax = plt.subplots()
    ax.bar(labels, sizes)

    # Save the chart to a BytesIO object
    chart_image = BytesIO()
    plt.savefig(chart_image, format='png')
    chart_image.seek(0)

    # Convert the chart to a base64-encoded image
    chart_base64 = base64.b64encode(chart_image.read()).decode('utf-8')

    # Get battery status and info
    battery = psutil.sensors_battery()
    if battery is not None:
        battery_percent = battery.percent
        battery_voltage = battery.volt
    else:
        battery_percent = "N/A"
        battery_voltage = "N/A"

    # Render the HTML template with the chart
 
    templateData = {
        'button'  : buttonSts,
        'senPIR'  : senPIRSts,
        'DISK_total'  : DISK_total,
        'DISK_used'  : DISK_used,
        'DISK_free'  : DISK_left,
        'DISK_P'  : DISK_perc,
        'chart_base64'  : chart_base64,
        'battery_percent'  : battery_percent,
        'battery_voltage'  : battery_voltage,
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
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return 'File uploaded successfully'
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('upload.html')

@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    print(client_ip,' - Connected')

if __name__ == '__main__':
#  app.run(host='0.0.0.0', port=8081, debug=True)
    socketio.start_background_task(update_stats)
    print('- WebPage Started')
    socketio.run(app, host='0.0.0.0', port=8080)
