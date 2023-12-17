import RPi.GPIO as GPIO
import os
import datetime
import time
import subprocess
import re
import eventlet
import psutil
import matplotlib.pyplot as plt
import base64
#import cv2
import paho.mqtt.client as mqtt
import os
import logging
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, send, emit
from ftplib import FTP, FTP_TLS
from ftputil import FTPHost, session, tool
from io import BytesIO
from flask_fontawesome import FontAwesome

#################################################################
#cap = cv2.VideoCapture(0)  # Use the appropriate camera index (0 for the default camera)

##################################################################
# Set the IP address of the FPP system to control
FPP_API_URL = 'http://192.168.1.2/api'
# FTP server settings
FTP_SERVER_ADDRESS = 'ftp.192.168.1.2'  # Replace with your FTP server's host
FTP_USER = 'fpp'
FTP_PASS = 'falcon'
FTP_PORT = 22   # Use port 22 for FTPS
##################################################################
# Set the log file location and log level
log_file = '/home/smartalec/sign/logs/sign_system.log'  # Log to a file
log_level = 'ERROR'
logging.basicConfig(level=logging.ERROR)   # Adjust the log level as needed (e.g., INFO, DEBUG, WARNING, and ERROR.)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(log_level)
formatter = logging.Formatter( '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(file_handler)
#tool.log = logging.getLogger()  # Redirect ftputil logging to the root logger
###################################################################
app = Flask(__name__)
app.logger.addHandler(file_handler)
app.config['SECRET_KEY'] = 'MontyPython_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}  # Define allowed file extensions
app.config['MAX_FILE_SIZE'] = 10 * 1024 * 1024  # 10 MB max file size
#socketio = SocketIO(app, async_mode='gevent')  # Use Gevent async mode
socketio = SocketIO(app)
#socketio = SocketIO(app, cors_allowed_origins=[ http://192.168.1.140 ])
fa = FontAwesome(app)
####################################################################
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
#####################################################################
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

##########################################################################
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
#######################################################################
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
    return str(psutil.cpu_percent(interval=1))

def getDiskSpace():
    p = os.popen("df -h /")
    i = 0
    while 1:
        i = i +1
        line = p.readline()
        if i==2:
            return(line.split()[1:5])

def get_network_speed():
    # Get the current network usage in bytes per second
    network_speed_up = psutil.net_io_counters().bytes_recv
    network_speed_down = psutil.net_io_counters().bytes_sent
    time.sleep(1)
    incoming_speed = psutil.net_io_counters().bytes_recv - network_speed_up
    outgoing_speed = psutil.net_io_counters().bytes_sent - network_speed_down
    return incoming_speed, outgoing_speed

def update_stats():
    while True:
        current_time = datetime.datetime.utcnow().strftime('%H:%M:%S')
        socketio.emit('update_time', current_time)
        cpu_temp = getCPUtemperature()  # Get CPU Temperature
        socketio.emit('cpu_temp', cpu_temp)
        cpu_usage = getCPUuse()
        socketio.emit('cpu_usage', cpu_usage)
        DISK_stats = getDiskSpace()
        disk_left = DISK_stats[2]
        socketio.emit('disk_free', disk_left)
        battery = psutil.sensors_battery()  # Get battery status and info
        if battery is not None:
            battery_percent = battery.percent
            battery_voltage = battery.volt
        else:
            battery_percent = "N/A"
            battery_voltage = "N/A"
        socketio.emit('batt_volt', battery_voltage)
        socketio.emit('batt_percent', battery_percent)
        speed_up, speed_down = get_network_speed()
        socketio.emit('speed', {'speed_up': speed_up,'speed_down': speed_down} )
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

    # Render the HTML template with the chart
    templateData = {
        'button'  : buttonSts,
        'senPIR'  : senPIRSts,
        'DISK_total'  : DISK_total,
        'DISK_used'  : DISK_used,
        'DISK_free'  : DISK_left,
        'DISK_P'  : DISK_perc,
        'chart_base64'  : chart_base64
     }
    return render_template('index.html', **templateData)

def gen():
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        yield f'data:image/jpeg;base64,{jpg_as_text}'

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

@app.route('/fpp_connect')
def fpp_commands():
#   Access the FPP Rasp Pi over API commands    
    return render_template('fpp_connect.html')

@app.route('/shell')
def shell():
    return render_template('shell.html')

@app.route('/ftp_directory')
def ftp_directory():
#    ssh = paramiko.SSHClient()
# automatically add keys without requiring human intervention
#    ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
#    ssh.connect(FTP_SERVER_ADDRESS, username=FTP_USER, password=FTP_PASS)
#    ftp = ssh.open_sftp()
#    directory_files = ftp.listdir()
    directory_files = 'hello'
    return render_template('ftp_directory.html', directory_files=directory_files)

@app.route('/update_gps', methods=['POST'])
def update_gps():
    data = request.json  # Assuming data is sent as JSON
    latitude = data['latitude']
    longitude = data['longitude']
    # Process and store GPS data as needed (e.g., in a database)

    return jsonify({"message": "GPS data received successfully"})

@app.route('/upload_file')
def upload_file():
    return render_template('upload_file.html')

@app.route('/ftp_upload', methods=['GET', 'POST'])
def ftp_upload():
    if request.method == 'POST':
        try:
            file = request.files['file']
            if file:
                with FTP(FTP_SERVER_ADDRESS) as ftp:
                    ftp.login(FTP_USER, FTP_PASS)
                     # Define the target directory on the FTP server (e.g., /media/)
                    target_directory = '/media/'

                    # Save the file locally
                    local_file_path = f"{target_directory}{file.filename}"
                    with open(local_file_path, 'wb') as local_file:
                        file.save(local_file)

                    # Upload the file to the FTP server
                    with open(local_file_path, 'rb') as local_file:
                        ftp.storbinary(f"STOR {local_file_path}", local_file)

                    # List the contents of the FTP directory
                    directory_contents = ftp.nlst(target_directory)

                socketio.emit('file_uploaded', file.filename)
        except Exception as e:
            socketio.emit('file_upload_error', str(e))
    return render_template('ftp_upload.html')

###################################################################################

@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    print(client_ip,' - Connected')
    emit('stream', {'data': 'Connected'})
    
@socketio.on('disconnect')
def handle_disconnect():
    client_ip = request.remote_addr
    print(client_ip,' - Disconnected')

@socketio.on('stream')
def handle_connect():
    emit('stream', {'data': 'Connected'})
 
@socketio.on('send_fpp')
def handle_command(data):
    command = data['command']
    try:
        response = requests.get(f"{FPP_API_URL}/{command}")
        if response.status_code == 200:
            result = response.json()
            socketio.emit('command_response', result)
        else:
            socketio.emit('command_response', {'error': 'Command failed'})
    except Exception as e:
        socketio.emit('command_response', {'error': str(e)})

####################################################################################

if __name__ == '__main__':
#  app.run(host='0.0.0.0', port=8081, debug=True)
    socketio.start_background_task(update_stats)
    eventlet.monkey_patch()
    print('- WebPage Started')
    socketio.run(app, host='0.0.0.0', port=8080)
