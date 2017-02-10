#! /usr/bin/python
#  _____      _                       _   
# |_   _|    | |                     | |  
#   | | _ __ | |_ ___ _ __ _ __   ___| |_ 
#   | || '_ \| __/ _ \ '__| '_ \ / _ \ __|
#  _| || | | | ||  __/ |  | | | |  __/ |_ 
#  \___/_| |_|\__\___|_|  |_| |_|\___|\__|
#                      __                 
#                     / _|                
#                ___ | |_                 
#               / _ \|  _|                
#              | (_) | |                  
#               \___/|_|                  
#  _____                         _        
# /  ___|                       | |       
# \ `--.  ___  ___  ___  ___  __| |___    
#  `--. \/ _ \/ _ \/ _ \/ _ \/ _` / __|   
# /\__/ /  __/  __/  __/  __/ (_| \__ \   
# \____/ \___|\___|\___|\___|\__,_|___/ 
#
# A raspberry pi timelapse and environmental logging script,
#  originally designed with plants in mind.
#
# Branched from the awesome work at Pimoroni by L. Doig, Jan 2017
# 
# Based on: https://github.com/pimoroni/internet-of-seeds
# Also inspired by: 
#         https://github.com/pimoroni/enviro-phat
#         http://stackoverflow.com/questions/38876429/how-to-convert-from-rgb-values-to-color-temperature
#         http://community.thingspeak.com/tutorials/update-a-thingspeak-channel-using-mqtt-on-a-raspberry-pi/
#
# This takes the original internet of seeds code, and changes the sensors
#  from the flotilla to the envrio pHAT.
#
# Also adds in:
#               Colour temperature calculations based off the RGB values
#               Blinking LEDs to warn people of imminent camera use
#               MQTT support for data logging to thingspeak
#
# This script requires the envrio pHAT from Pimoroni and a pi camera.
# 
# The following libraries need to be installed:
#   NUMPY via:      pip install numpy
#   SCIPY via:      pip install scipy
#   COLOUR via:     pip install colour
#   PAHO-MQTT via:  pip install paho-mqtt
#   PSUTIL via:		pip install psutil 
#   PILLOW via:     pip install pillow
#   ENVRIOPHAT via: curl -sS https://get.pimoroni.com/envirophat | bash
#
# Note that this is a one shot script, it does not loop. 
# To run over and over, it is required to setup a crontab entry. 
#
# Import all required libraries:
import os
import shutil
import datetime
import picamera
import pandas as pd
import numpy as np
import colour
import time
import ssl
import json
import psutil
import paho.mqtt.publish as publish
from PIL import Image, ImageFont, ImageDraw
from sparkblocks import spark
from envirophat import light, weather, leds

## CONFIG ##
config_f = 'config.json'          # All the private stuff is stored in here
log_f = 'InternetOfSeeeeds.log'   # Local Log File
rawpic = '1_RawImages/'           # Folder for raw images
tispic = '2_TiSImages/'           # Folder for overlaid images
timesperday = 144                 # Once per 10min = 10/60*24 = 144 (required for sparks). Make sure this matches cron.
mqttHost = "mqtt.thingspeak.com"

with open(config_f) as f: 
 config = json.load(f) 
TS_channelID = config['thingspeak']['cid'] 
TS_apiKey = config['thingspeak']['apikey'] 

# Using SSL Websockets for MQTT communication to thingspeak
tTransport = "websockets"
tTLS = {'ca_certs':"/etc/ssl/certs/ca-certificates.crt",'tls_version':ssl.PROTOCOL_TLSv1}
tPort = 443
topic = "channels/" + TS_channelID + "/publish/" + TS_apiKey
## END CONFIG ##

## Captures an image and copies to latest.jpg. Needs to be passed a datetime
#   object for the timestamped image, t.
#  Note: Captures in 1440x1080p.
def capture_image(t):
  ts = t.strftime('%Y-%m-%d-%H-%M')
  cam = picamera.PiCamera()
  cam.resolution = (1440, 1080)
  cam.hflip = True
  cam.vflip = True
  filename = rawpic + 'image-' + t.strftime('%Y-%m-%d-%H-%M') + '.jpg'
  cam.capture(filename, quality=100)
  shutil.copy2(filename, rawpic + 'latest.jpg')
  return filename

## Overlays the timestamp and sensor values on the latest captured image. Needs
## to be passed a datetime object and the dictionary of sensor values.
def timestamp_image(t, sensor_vals, sparks, watermark=False):
  ts_read = t.strftime('%H:%M, %a. %d %b %Y')
  img = Image.open(rawpic + 'latest.jpg')
  img = img.resize((1438, 1080))
  if watermark == True:
    wm = Image.open('watermark.png')
    img.paste(wm, (0, 996), wm)
  draw = ImageDraw.Draw(img)
  font = ImageFont.truetype('Roboto-Regular.ttf', 36)
  spark_font = ImageFont.truetype('arial-unicode-ms.ttf', 16)
  draw.text((10, 10), ts_read, (255, 255, 255), font=font)
  draw.text((10, 50), 'Temp: {0:.1f}'.format(sensor_vals['temperature']), (255, 255, 255), font=font)
  draw.text((10, 90), 'Press: {0:.0f}'.format(sensor_vals['pressure']), (255, 255, 255), font=font)
  draw.text((10, 130), 'Light: {0:.0f}'.format(sensor_vals['light']), (255, 255, 255), font=font)
  draw.text((10, 170), 'RGB: ' + ','.join([str(int(i)) for i in sensor_vals['colour']]), (255, 255, 255), font=font)
  draw.text((10, 210), 'CCT:  {0:.0f}'.format(sensor_vals['cct']), (255, 255, 255), font=font)
  for i in range(len(sparks)):
    draw.text((10, 265 + i * 25), sparks[i], (255, 255, 255), font=spark_font)
  filename = tispic + 'latest_ts.jpg'
  img.save(filename)
  
  filenamets = tispic + 'image_ts-' + t.strftime('%Y-%m-%d-%H-%M') + '.jpg'
  shutil.copy2(filename, filenamets)

  return filename  

## Reads the Envriophat sensor values and stores them in a dictionary.
def read_sensors():
  lights = light.light()
  rgb = light.rgb()  
  temp = round(weather.temperature(),2)
  pres = round(weather.pressure(),2)
  r = round(rgb[0],1)
  g = round(rgb[1],1)
  b = round(rgb[2],1)
  
  #Conversion to CCT, ref http://stackoverflow.com/questions/38876429/how-to-convert-from-rgb-values-to-color-temperature
  RGBnp = np.array([r,g,b]) # Assuming sRGB encoded colour values.
  XYZ = colour.sRGB_to_XYZ(RGBnp / 255) # Conversion to tristimulus values.
  xy = colour.XYZ_to_xy(XYZ)  # Conversion to chromaticity coordinates.
  CCT = round(colour.xy_to_CCT_Hernandez1999(xy),0)   # Conversion to correlated colour temperature in K.

  # Disk Space from psutil
  disk = psutil.disk_usage('/')
  disk_free = disk.free / 2**20 # 2^20 = Megabytes
    
  vals = {}
  vals['light'] = lights
  vals['colour'] = (r, g, b)
  vals['cct'] = round(CCT,0)
  vals['temperature'] = temp
  vals['pressure'] = pres
  vals['diskfree'] = disk_free
  return vals 

## Bins the row and compresses the data by a factor equal to the bin size.
def compress(data, bin=2):
  compressed = ((data + data.shift(-1)) / bin)[::bin]
  compressed = compressed.tolist()
  return compressed

## Creates sparklines in Unicode blocks for last 24 hrs of data.
def sparklines(data, timesperday):
  df = pd.read_csv(data, sep='\t')
  last_day = df[-timesperday:]
  temps = last_day['temp']
  press = last_day['press']
  light = last_day['light']
  cct = last_day['cct']
  sl_temps = spark(compress(temps, bin=4))
  sl_press = spark(compress(press, bin=4))
  sl_light = spark(compress(light, bin=4))
  sl_cct = spark(compress(cct, bin=4))
  return (sl_temps, sl_press, sl_light,sl_cct)

## Writes the sensor values to a tab-separated text file (Local Logging).
def log_values(t, sensor_vals, data):
  filename = data
  ts = t.strftime('%Y-%m-%d-%H-%M')
  sensor_str = '%s\t%.2f\t%.2f\t%i\t%i\t%i\t%i\t%i\t%i\n' % (ts, sensor_vals['temperature'], sensor_vals['pressure'], sensor_vals['light'], sensor_vals['colour'][0], sensor_vals['colour'][1], sensor_vals['colour'][2],sensor_vals['cct'], sensor_vals['diskfree'])
  if not os.path.isfile(filename):
    out = open(filename, 'a')
    out.write('time\ttemp\tpress\tlight\tred\tgreen\tblue\tcct\tdf\n')
    out.write(sensor_str)
  else:
    out = open(filename, 'a')
    out.write(sensor_str)
  out.close()

## Code to blink the LED on the light measuring sensor
def blink_LED(hold, dwell, seq=1):
  for x in range(seq):
    leds.on()
    time.sleep(hold) 
    leds.off()
    time.sleep(hold)
  time.sleep(dwell)
  return

## Send the sensor values to ThingSpeak
# Ref: http://community.thingspeak.com/tutorials/update-a-thingspeak-channel-using-mqtt-on-a-raspberry-pi/
def send_values(t, sensor_vals):
  #Build the payload string
  # ASSUMPTION: Field 1 = Temp, Field 2 = Pressure, Field 3 = Light, Field 4 = CCT, Field 5 = Disk Space.
  tPayload = "field1=" + str(sensor_vals['temperature']) \
             + "&field2=" + str(sensor_vals['pressure']) \
			 + "&field3=" + str(sensor_vals['light']) \
			 + "&field4=" + str(sensor_vals['cct']) \
			 + "&field5=" + str(sensor_vals['diskfree'])
  #print t.strftime('%Y-%m-%d-%H-%M') + ": Payload: " + tPayload # Print the values if required for debug, otherwise comment out
  # attempt to publish this data to the topic 
  try:
      publish.single(topic, payload=tPayload, hostname=mqttHost, port=tPort, tls=tTLS, transport=tTransport)
  except:
      print t.strftime('%Y-%m-%d-%H-%M') + ": There was an error while publishing the MQTT data."	
    
## Run the functions.
t = datetime.datetime.now()               # Get the time
blink_LED(.1,.25,3)                       # In 3 ....
blink_LED(.1,.25,2)                       # ... 2 ...
blink_LED(.1,0,1)                         # ... 1 ...
img = capture_image(t)                    # Take a picture!
sensor_vals = read_sensors()              # Read the sensors
#print t.strftime('%Y-%m-%d-%H-%M') + ": Sensors: " + sensor_vals    # Print the values if required for debug, otherwise comment out
data = log_f                              # Data log file
log_values(t, sensor_vals, data)          # Store the sensor values in the log 
sparks = sparklines(data, timesperday)    # Spark line graph
latest = timestamp_image(t, sensor_vals, sparks, watermark=False)  # Watermark the picture with the data
send_values(t, sensor_vals)                  # Log values to ThingSpeak
