## Internet of Seeds

![Plants side](plants_side.jpg)

Hello! This is my branch of Pimoroni's [Internet of Seeds](http://blog.pimoroni.com/the-internet-of-seeds/). I modified it to use the envrio pHAT, calculate the Colour Corrected Temperature (CCT) of the light, log the data to thingspeak, and only take pictures at certain hours of the day.

In case you are wondering, I have nothing to do with Pimoroni, I've just shopped there before using my own hard earned script and are using their products for this, but thats it. 

Hardware wise, its not dissimilar to the original. An [IKEA VÄXER hydroponics system](http://www.ikea.com/gb/en/catalog/products/S29158684/) is combined with a Raspberry Pi Zero and camera, along with the envirophat from Pimoroni.

In future, a water level monitor and humidity sensor might be added, but will get to that later. Its probably possible to have the raspberry control the light, but when a simple AC timer switch is so cheap, thats the solution used here.

If you want to know more, the original Pimoroni blog post has a lot of infomation [here.](http://blog.pimoroni.com/the-internet-of-seeds/)

## Pre-requisites

You'll need to install the python-picamera, pandas, tweepy, sparkblocks, numpy, scipy, colour, paho-mqtt, psutil, pillow and envirophat libraries.

```
sudo apt-get install python-picamera python-pandas
sudo pip install tweepy
sudo pip install py-sparkblocks
sudo pip install numpy
sudo pip install scipy
sudo pip install colour
sudo pip install paho-mqtt
sudo pip install psutil 
sudo pip install pillow
curl -sS https://get.pimoroni.com/envirophat | bash
```

We've used [Roboto](https://www.fontsquirrel.com/fonts/roboto) as the font for our 
timestamping and sensor data overlay. You'll also
need [Arial Unicode MS](http://www.myfontfree.com/arial-unicode-ms-myfontfreecom126f36926.htm)
for the sparklines

To use tweepy to tweet, you'll need to set up a new app on the
[Twitter developer site](https://dev.twitter.com/). It's free to do. You'll
then need to add your own consumer and access keys and secrets in a config.json 
file. See [config.example.json](config.example.json) as an example.

The paths in the shell scripts assume that this repo is in your home directory.

We'd also suggest using a large micro SD card, preferably 64GB, since you'll
be capturing a lot of images.

## Using the scripts

We chose to use cron to run the two Python scripts via a couple of shell
scripts.

You can do the following to run the image capture/data logging script every 10
minutes and the tweeting script 3 times daily, at 06:05, 12:05 and 18:05.

After typing `crontab -e`, add the following lines to the bottom.

```
*/10 * * * * sh /home/pi/internet-of-seeds/internet-of-seeds.sh >> /home/pi/internet-of-seeds/data/cron.log
05 06,12,18 * * * sh /home/pi/internet-of-seeds/internet-of-seeds-tweet.sh >> /home/pi/internet-of-seeds/data/cron.log
```

This also logs all of the standard output to a file named `cron.log` in the
data directory.
