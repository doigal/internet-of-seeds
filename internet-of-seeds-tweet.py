import json
import tweepy

## Function to tweet sensor values and a timestamped image. Needs to be passed
## status (timestamp and sensor values pulled from data log) and the latest
## image filename.
def tweet_pic(status, latest, config_f='config.json'):
  with open(config_f) as f:
    config = json.load(f)
  ckey = config['tweepy']['ckey']
  csecret = config['tweepy']['csecret']
  akey = config['tweepy']['akey']
  asecret = config['tweepy']['asecret']
  auth = tweepy.OAuthHandler(ckey, csecret)
  auth.set_access_token(akey, asecret)
  api = tweepy.API(auth)
  api.update_with_media(latest, status=status)

## Set the latest image filename, grab the last line from the data log.
tispic = '2_TiSImages/' # Folder for overlaid images
latest = tispic + 'latest_ts.jpg'

fn = 'InternetOfSeeeeds.log'
with open(fn) as f:
  for l in f.readlines():
    pass

## Format the sensor values nicely for tweeting, run the tweet_pic function.
sensor_vals = l.rstrip().split('\t')
status = '%s: Temp: %s C, Press: %s hPa, Light: %s lux, CCT: %sK, Disk Free: %s Mb' % (sensor_vals[0], sensor_vals[1], sensor_vals[2], sensor_vals[3], sensor_vals[7], sensor_vals[8])
#print status
tweet_pic(status, latest)
