# RPiVideoSync
quick script to (semi-)sync two videos via wifi on two Raspberry Pis (via omxplayer-wrapper)  

to install: 
get the stock 'Raspbian / Raspberry Pi OS with desktop'

use the desktop to set up wifi for both Pis. make sure the IP address stays the same for both (either use a static IP by editing /etc/dhcpcd.conf, or DHCP reservations)

ensure python3 and omxplayer are installed (they come by default, so they should be)

pip3 install python-osc

pip3 install omxplayer-wrapper

sudo raspi-config, set your Pi to boot to the command line (so the desktop won't show behind the videos) and, optionally, set it to auto-login. I also set it to 'wait for network to boot', since the script needs the network to function

**also in raspi-config: advanced settings->memory split, set your GPU memory to at least 128! otherwise omxplayer will be sad**

to run the sync (ensure both video files are exactly the same):

(the sync manager, on 192.168.y.y): ./RPiVideoSync -m --ip=192.168.x.x --filename=test.mp4

(the sync subordinate, on 192.168.x.x): ./RPiVideoSync -s --ip=192.168.y.y --filename=test.mp4

to set it up to run at reboot forever:

'sudo crontab -e' on both machines. the line you'll type in is:

@reboot sleep 10;/full/path/to/RPiVideoSync -m --ip=192.168.x.x --filename=test.mp4

OR

@reboot sleep 10;/full/path/to/RPiVideoSync -s --ip=192.168.y.y --filename=test.mp4

you can edit the json file (created in the same directory the first time you run it) to change settings / control how omxplayer starts, if you want (options include aspect mode & audio outputs)

how it works: uses OSC to coordinate near-identical start times for two (identical) videos. add to crontab as above and it'll work on powerup with no human interaction. for best results, put at least ~.5 seconds of black screen at the start and end of your video!
