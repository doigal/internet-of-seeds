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
# Timelapse assembly script.
#
# Part of the internet of seeeeds project! 
# L. Doig, Feb 2017
#
# G Streamer is installed by the following:
#  sudo sh -c 'echo deb http://vontaene.de/raspbian-updates/ . main >> /etc/apt/sources.list'
#  sudo apt-get update
#  sudo apt-get install libgstreamer1.0-0 liborc-0.4-0 gir1.2-gst-plugins-base-1.0 gir1.2-gstreamer-1.0 gstreamer1.0-alsa gstreamer1.0-omx gstreamer1.0-plugins-bad gstreamer1.0-plugins-base gstreamer1.0-plugins-base-apps gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-pulseaudio gstreamer1.0-tools gstreamer1.0-x libgstreamer-plugins-bad1.0-0 libgstreamer-plugins-base1.0-0
#
# Youtube upload is installed by the following:
#  sudo pip install --upgrade google-api-python-client progressbar2
#  wget https://github.com/tokland/youtube-upload/archive/master.zip
#  unzip master.zip
#  cd youtube-upload-master
#  sudo python setup.py install
#
# The gstreamer is launched by the following:
#  gst-launch-1.0 multifilesrc location=timelapse%04d.jpeg index=1 caps="image/jpeg,framerate=24/1" ! jpegdec ! omxh264enc ! avimux ! filesink location=timelapse.avi
#
# The python upload script is:
#  youtube-upload \
#    --title="A.S. Mutter" 
#    --description="A.S. Mutter plays Beethoven" \
#    --category=Music \
#    --tags="mutter, beethoven" \
#    --recording-date="2011-03-10T15:32:17.0Z" \
#    --default-language="en" \
#    --default-audio-language="en" \
#    --client-secrets=my_client_secrets.json \
#    --credentials-file=my_credentials.json \
#    --playlist "My favorite music" \
#    anne_sophie_mutter.flv
#
# Ideally the youtube upload would be imported as a python libary, but this isnt a perfect world :p
#
# Note that this is a one shot script, it does not loop. 
# To run over and over, it is required to setup a crontab entry. 
# The script is setup with the idea of running on the first of the month, to assemble the previous months images.
# Example CronTab, to run at 00:05 on the first of each month:
#   5 0 1 * * sh /home/pi/internet-of-seeds/internet-of-seeds-timelapse.sh >> /home/pi/internet-of-seeds/data/cron.log
#
# Import all required libraries:
import datetime, json, glob, os, subprocess

## CONFIG ##
config_f = 'config.json'          # All the private stuff is stored in here
rawpic = '1_RawImages/'           # Folder for raw images
tispic = '2_TiSImages/'           # Folder for overlaid images
timvid = '3_TiLVideos/'           # Folder for timelapse videos
tmpdir = '99_Temp/'               # Scratch directory
FPS = 24                          # Frames per second
## END CONFIG ##

t = datetime.datetime.now()
t_lastMth = t+datetime.timedelta(days=-1) # Its just the year and month we care for, nothing more. Minus one day is plenty
searchrange = t_lastMth.strftime('%Y-%m')
searchstring = "%s*%s*" % (tispic, searchrange)

print "Searchrange: %s" %searchrange
# Get the files into a list
File_List = sorted(glob.glob(searchstring))
File_Num = len(File_List)

# Create symbolic links into a temp directory in a sequential format
i=0
for file in File_List:
   os.system('ln %s %s%05d.jpg' % (file, tmpdir, i))
   i += 1

# Create Output File Name
OutputVideo = '%sTimeLapse_Stamped_FPS%s_%s.avi' %(tmpdir, FPS, searchrange)
print "OutputVideo: %s" %OutputVideo

t_start = datetime.datetime.now()
# Call G streamer & get a coffee. Can take a while!
# Source: gst-launch-1.0 multifilesrc location=timelapse%04d.jpeg index=1 caps="image/jpeg,framerate=24/1" ! jpegdec ! omxh264enc ! avimux ! filesink location=timelapse.avi
G= 'gst-launch-1.0 multifilesrc location=%s%s.jpg index=1 caps="image/jpeg,framerate=%s/1" ! jpegdec ! omxh264enc ! avimux ! filesink location=%s' %(tmpdir, '%05d', FPS, OutputVideo)
os.system(G)
t_taken = datetime.datetime.now() - t_start
print 'G Streamer Took: %s' % t_taken

# Clean up the temp files
#os.system('sudo rm ' + tmpdir + '*.jpg')
os.system('sync')

# Upload to youtube
#https://github.com/tokland/youtube-upload
YT_Title = 'Internet of Seeeds timelapse for ' + searchrange 
#YT_Date = 'something' #2011-03-10T15:32:17.0Z
YT_Desc = 'This is a timelapse for my internet of seeeds project. A Raspberry Pi Zero has taken a picture every 10 minutes during lit hours, and combined automagically into the timelapse you see above. This one is for the month of ' + t_lastMth.strftime('%B, %Y') + '. Build your own! Code is here:https://github.com/doigal/internet-of-seeds'
YT_Tags = 'timelapse, internetofseeeds, iot, raspberrypi, python'
YT_Play = 'Internet of Seeeds'

#Debug
#print "YT_Title: %s" %YT_Title
#print "YT_Date: %s" %YT_Date
#print "YT_Desc: %s" %YT_Desc
#print "YT_Tags: %s" %YT_Tags
#print "YT_Play: %s" %YT_Play

YT_Script = 'youtube-upload --title="' + YT_Title + \
            '" --description="'+YT_Desc + \
            '" --tags="'+ YT_Tags + \
            '" --recording-date="2011-03-10T15:32:17.0Z"' + \
            ' --default-language="en" --default-audio-language="en" ' + \
            ' --playlist "' + YT_Play + '" ' + \
            OutputVideo
#print "YT_Script: %s" %YT_Script

#upload the video. This should be by a python call rather than external shell command.
#system(YT_Script)
# need the output video URL
#YTout = subprocess.check_output(YT_Script, shell=True)
#print "YT reply: %s" % YTout

# Tweet the results
