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
# A raspberry pi timelapse and envirometal logging script,
#  originally designed with plants in mind.
#
# Branched from the awesome work at pimoroni by L. Doig, Jan 2017
# 
# Based on: https://github.com/pimoroni/internet-of-seeds
# Also inspired by: 
#         https://github.com/pimoroni/enviro-phat
#         http://stackoverflow.com/questions/38876429/how-to-convert-from-rgb-values-to-color-temperature
#
# This takes the original internet of seeds code, and changes the sensors
#  from the flotilla to the envrio pHAT.
#
# Also adds in:
#               Colour temperature calculations based off the RGB values
#               Blinking LEDs to warn people of imminent camera use
#               (WIP!) MQTT support for data logging
#
# This script requires the envrio pHAT from Pimoroni and a pi camera.
# 
# The following libaries need to be installed:
#   NUMPY via:      pip install numpy
#   SCIPY via:      pip install scipy
#   COLOUR via:     pip install colour
#   ENVRIOPHAT via: curl -sS https://get.pimoroni.com/envirophat | bash
#
# Note that this is a one shot script, it does not loop. 
# To run over and over, it is required to setup a crontab entry. 
#
import os
import shutil
import datetime
import picamera
import pandas as pd
import PIL
import numpy as np
import colour
import time
from PIL import Image, ImageFont, ImageDraw
from sparkblocks import spark
from envirophat import light, weather, leds

## Captures an image and copies to latest.jpg. Needs to be passed a datetime
## object for the timestamped image, t.
def capture_image(t):
  ts = t.strftime('%Y-%m-%d-%H-%M')
  cam = picamera.PiCamera()
  cam.resolution = (1438, 1080)
  cam.hflip = True
  cam.vflip = True
  filename = 'data/image-' + t.strftime('%Y-%m-%d-%H-%M') + '.jpg'
  cam.capture(filename, quality=100)
  shutil.copy2(filename, 'data/latest.jpg')
  return filename

## Overlays the timestamp and sensor values on the latest captured image. Needs
## to be passed a datetime object and the dictionary of sensor values.
def timestamp_image(t, sensor_vals, sparks, watermark=False):
  ts_read = t.strftime('%H:%M, %a. %d %b %Y')
  img = Image.open('data/latest.jpg')
  img = img.resize((1438, 1080))
  if watermark == True:
    wm = Image.open('data/watermark.png')
    img.paste(wm, (0, 996), wm)
  draw = ImageDraw.Draw(img)
  font = ImageFont.truetype('data/Roboto-Regular.ttf', 36)
  spark_font = ImageFont.truetype('data/arial-unicode-ms.ttf', 16)
  draw.text((10, 10), ts_read, (255, 255, 255), font=font)
  draw.text((10, 50), 'Temp: {0:.1f}'.format(sensor_vals['temperature']), (255, 255, 255), font=font)
  draw.text((10, 90), 'Press: {0:.0f}'.format(sensor_vals['pressure']), (255, 255, 255), font=font)
  draw.text((10, 130), 'Light: {0:.0f}'.format(sensor_vals['light']), (255, 255, 255), font=font)
  draw.text((10, 170), 'RGB: ' + ','.join([str(int(i)) for i in sensor_vals['colour']]), (255, 255, 255), font=font)
  draw.text((10, 210), 'CCT:  {0:.0f}'.format(sensor_vals['cct']), (255, 255, 255), font=font)
  for i in range(len(sparks)):
    draw.text((10, 265 + i * 25), sparks[i], (255, 255, 255), font=spark_font)
  filename = 'data/latest_ts.jpg'
  img.save(filename)
  
  filenamets = 'data/image_ts-' + t.strftime('%Y-%m-%d-%H-%M') + '.jpg'
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

  vals = {}
  vals['light'] = lights
  vals['colour'] = (r, g, b)
  vals['cct'] = round(CCT,0)
  vals['temperature'] = temp
  vals['pressure'] = pres
  return vals 

## Bins the row and compresses the data by a factor equal to the bin size.
def compress(data, bin=2):
  compressed = ((data + data.shift(-1)) / bin)[::bin]
  compressed = compressed.tolist()
  return compressed

## Creates sparklines in Unicode blocks for last 24 hrs of data.
def sparklines(data):
  df = pd.read_csv(data, sep='\t')
  last_day = df[-144:]
  temps = last_day['temp']
  press = last_day['press']
  light = last_day['light']
  cct = last_day['cct']
  sl_temps = spark(compress(temps, bin=4))
  sl_press = spark(compress(press, bin=4))
  sl_light = spark(compress(light, bin=4))
  sl_cct = spark(compress(cct, bin=4))
  return (sl_temps, sl_press, sl_light,sl_cct)

## Writes the sensor values to a tab-separated text file.
def log_values(t, sensor_vals):
  filename = 'data/internet-of-seeds.log'
  ts = t.strftime('%Y-%m-%d-%H-%M')
  sensor_str = '%s\t%.2f\t%.2f\t%i\t%i\t%i\t%i\t%i\n' % (ts, sensor_vals['temperature'], sensor_vals['pressure'], sensor_vals['light'], sensor_vals['colour'][0], sensor_vals['colour'][1], sensor_vals['colour'][2],sensor_vals['cct'])
  if not os.path.isfile(filename):
    out = open(filename, 'a')
    out.write('time\ttemp\tpress\tlight\tred\tgreen\tblue\tcct\n')
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

## Run the functions.
t = datetime.datetime.now()               # Get the time
blink_LED(.1,.25,3)                       # In 3 ....
blink_LED(.1,.25,2)                       # ... 2 ...
blink_LED(.1,0,1)                         # ... 1 ...
img = capture_image(t)                    # Take a picture!
sensor_vals = read_sensors()              # Read the sensors
#print sensor_vals                        # Print the values if required for debug
data = 'data/internet-of-seeds.log'       # Data log file
log_values(t, sensor_vals)                # Store the sensor values in the log 
sparks = sparklines(data)                 # Spark line graph
latest = timestamp_image(t, sensor_vals, sparks, watermark=False)  