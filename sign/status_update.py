from gsmmodem import GsmModem
import RPi.GPIO as GPIO
import eventlet
import serial
import subprocess
import re
import time
import pyudev
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, send, emit
import logging
##################################################################
# Set the log file location and log level
log_file = '/home/smartalec/sign/logs/status_update.log'  # Log to a file
log_level = 'ERROR'
logging.basicConfig(level=logging.ERROR)   # Adjust the log level as needed (e.g., INFO, DEBUG, WARNING, and ERROR.)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(log_level)
formatter = logging.Formatter( '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(file_handler)
################################################################
vendor_name = 'SimTech'	#Usb Name for 4G device
################################################################
app = Flask(__name__)
app.config['SECRET_KEY'] = 'MontyPython_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")
################################################################

def get_usb_device_id(vendor_name):
	try:
		# Run lsusb command to list USB devices
		lsusb_output = subprocess.check_output(['lsusb']).decode('utf-8')
		
		# Search for the vendor name in the lsusb output
		pattern = re.compile(r'Bus (\d+) Device (\d+): ID (\w+:\w+) (.*)'+vendor_name+'.*')
		match = pattern.search(lsusb_output)
		
		if match:
			# Extract the device ID from the matched line
			bus_number = match.group(1)
			device_number = str(int(match.group(2)))
			print(f"'{vendor_name}' Device found: Bus {bus_number}, Device {device_number}")
			return device_number
		else:
			print(f"No USB Device Named '{vendor_name}' found.")
			return 0

	except subprocess.CalledProcessError as e:
		print(f"Error running lsusb: {e}")
		return None


################################################################
device_number = get_usb_device_id(vendor_name)
if device_number != 0:
	device = '/dev/ttyUSB3'
	modem = GsmModem(device)
	ser = serial.Serial(device,115200)
	ser.flushInput()

################################################################

power_key = 6
rec_buff = ''
rec_buff2 = ''
time_count = 0

def send_at(command,back,timeout):
	rec_buff = ''
	ser.write((command+'\r\n').encode())
	time.sleep(timeout)
	if ser.inWaiting():
		time.sleep(0.01 )
		rec_buff = ser.read(ser.inWaiting())
	if rec_buff != '':
		if back not in rec_buff.decode():
#			print(command + ' ERROR')
#			print(command + ' back:\t' + rec_buff.decode())
			socketio.emit('gps_location', ' ERROR:\t' + rec_buff.decode())
			return 0
		else:
			
			
#			print(rec_buff.decode())

#			#Additions to Demo Code Written by Tim!
#			global GPSDATA
#			#print(GPSDATA)
#			GPSDATA = str(rec_buff.decode())
#			Cleaned = GPSDATA[13:]
			
			#print(Cleaned)
			
#			Lat = Cleaned[:2]
#			SmallLat = Cleaned[2:11]
#			NorthOrSouth = Cleaned[12]
#			
#			#print(Lat, SmallLat, NorthOrSouth)
#			
#			Long = Cleaned[14:17]
#			SmallLong = Cleaned[17:26]
#			EastOrWest = Cleaned[27]
#			
#			#print(Long, SmallLong, EastOrWest)   
#			FinalLat = float(Lat) + (float(SmallLat)/60)
#			FinalLong = float(Long) + (float(SmallLong)/60)
#			
#			if NorthOrSouth == 'S': FinalLat = -FinalLat
#			if EastOrWest == 'W': FinalLong = -FinalLong
#			
#			print(FinalLat, FinalLong)
#			
#			#print(FinalLat, FinalLong)
#			#print(rec_buff.decode())

			socketio.emit('gps_location', rec_buff.decode())

			return 1
	else:
		print('GPS is not ready')
		return 0

def get_gps_position():
	power_on(power_key)

	rec_null = True
	answer = 0
	socketio.emit('gps_location', 'Starting GPS session...')
#	print('Starting GPS session...')
	rec_buff = ''
	send_at('AT+CGPS=1,1','OK',1)
	time.sleep(2)
	while rec_null:
		answer = send_at('AT+CGPSINFO','+CGPSINFO: ',1)
		if 1 == answer:
			answer = 0
			if ',,,,,,' in rec_buff:
				print('GPS is not ready')
				rec_null = False
				time.sleep(1)
		else:
			print('error %d'%answer)
			rec_buff = ''
			send_at('AT+CGPS=0','OK',1)
			return False
		time.sleep(1.5)


def power_on(power_key):
#	print('SIM7600X is starting:')
	socketio.emit('gps_location', 'SIM7600X is starting:')
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(power_key,GPIO.OUT)
	time.sleep(0.1)
	GPIO.output(power_key,GPIO.HIGH)
	time.sleep(2)
	GPIO.output(power_key,GPIO.LOW)
	time.sleep(5)
	ser.flushInput()
#	print('SIM7600X is ready')
	socketio.emit('gps_location', 'SIM7600X is ready')

def power_down(power_key):
	print('SIM7600X is loging off:')
	GPIO.output(power_key,GPIO.HIGH)
	time.sleep(3)
	GPIO.output(power_key,GPIO.LOW)
	time.sleep(18)
	print('Good bye')

def update_stats():
	while True:
		device_number = get_usb_device_id(vendor_name)
		if device_number != 0:
			gps = get_gps_position()
		else:
			gps = "{'fucked','fucked'}"
		socketio.emit('gps_location', gps)
		socketio.sleep(1)  # Emit updates every second


################################################################
		
@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    print(client_ip,' - Connected')

################################################################

if __name__ == '__main__':
#	socketio.start_background_task(update_stats)
	eventlet.monkey_patch()
	print('- Data Server Started')
	socketio.run(app, host='0.0.0.0', port=8046)

#    if ser != None:
#        ser.close()
#        power_down(power_key)
#        GPIO.cleanup()
