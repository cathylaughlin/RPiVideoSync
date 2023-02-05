# RPiVideoSync
quick script to (semi-)sync two videos via wifi on two Raspberry Pis (via omxplayer-wrapper)  

to install: 
get the stock 'Raspbian / Raspberry Pi OS with desktop'. Note that for a Pi 4, you should get the 'legacy/Buster' image, since the current version of Raspberry Pi OS no longer supports OMXPlayer. Install your OS on two different Pis. After it booted I just skipped all the updates, ymmv...

use the desktop to connect to a wifi network (preferably the same network / router you'll be deploying with!) on both Pis. make sure the IP address stays the same for both Pis (either use a static IP by editing /etc/dhcpcd.conf, or set up DHCP reservations on your router)

all instructions that follow are for both Pis:

ensure python3 and omxplayer are installed (they come by default, so they should be)

pip3 install python-osc

pip3 install omxplayer-wrapper

( if the install fails for omxplayer-wrapper, you may need to install a few more packages before trying again: 

sudo apt-get install libglib2.0-dev

sudo apt-get install libdbus-1-dev )

run 'sudo raspi-config'. optionally set your Pi to boot to the command line (so the desktop won't show behind the videos). also optionally, set it to auto-login. I also set it to 'wait for network to boot', since the script needs the network to function. 

also, go to 'interfacing options' and turn on ssh (you probably also want to change the default password for the pi account!) this allows you to remote into your Pis while the videos are playing. otherwise (in a pinch!) you can try blind-typing 'killall omxplayer' or 'pkill omxplayer' into the console...

**Raspberry Pi 3 only: also in raspi-config but NOT optional: advanced settings->memory split, set your GPU memory to at least 128! otherwise omxplayer will be sad. the Pi 4 auto-allocates video memory, so there's no need to change this setting on a Pi 4.**

to run the sync (ensure both video files are the same duration):

make sure you have run 'chmod 755 ./RPiVideoSync.py' from the same directory. then run:

(the sync manager, on 192.168.y.y): ./RPiVideoSync.py -m --ip=192.168.x.x --filename=test.mp4

(the sync subordinate, on 192.168.x.x): ./RPiVideoSync.py -s --ip=192.168.y.y --filename=test.mp4

to set it up to run at reboot when you plug in the Pis, run 'crontab -e' on both machines. the line you'll type in is:

@reboot sleep 10;/full/path/to/RPiVideoSync.py -m --ip=192.168.x.x --filename=test.mp4

OR

@reboot sleep 10;/full/path/to/RPiVideoSync -s --ip=192.168.y.y --filename=test.mp4

(as above, all that changes are -m/-s and the IP address)

you can edit the json file (created in the same directory the first time you run it) to change settings / control how omxplayer starts, if you want to (options include aspect mode & audio outputs)

how it works: uses OSC to coordinate near-identical start times for two (near-identical-duration) videos. add to crontab as above and it'll work on powerup with no human interaction. for best results, put at least ~.5 seconds of black screen at the start and end of your video!
