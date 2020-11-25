# RPiVideoSync
quick scripts to (semi-)sync two videos via wifi on two Raspberry Pis (omxplayer)  

to install: 
get the stock 'Raspbian / Raspberry Pi OS with desktop'

use the desktop to set up wifi for both Pis. make sure the IP address stays the same for both (either use a static IP by editing /etc/dhcpcd.conf, or DHCP reservations)

ensure python3 and omxplayer are installed (they come by default, so they should be)

pip3 install python-osc

pip3 install omxplayer-wrapper

sudo raspi-config, set your Pi to boot to the command line (so the desktop won't show behind the videos) and, optionally, set it to auto-login

**also in raspi-config: advanced settings->memory split, set your GPU memory to at least 128! otherwise omxplayer will be sad**

to run (ensure both video files are exactly the same):

(the manager, on 192.168.y.y): ./RPiVideoSync -m --ip=192.168.x.x --filename=test.mp4

(the subordinate, on 192.168.x.x): ./RPiVideoSync -s --ip=192.168.y.y --filename=test.mp4

to run forever:

sudo crontab -e

@reboot full/path/to/RPiVideoSync -m --ip=192.168.x.x --filename=test.mp4

OR

@reboot full/path/to/RPiVideoSync -s --ip=192.168.y.y --filename=test.mp4

edit the json file (created in the same directory the first time you run it) to change settings / control how omxplayer starts, if you want (aspect mode, audio outputs, etc)

how it works: uses OSC to coordinate near-identical start times for two (identical) videos. re-syncs after every N playthroughs (you can set N to your desired number of playthroughs using the JSON file). for best results, put at least ~.5 seconds of black screen at the start and end of your video. 
