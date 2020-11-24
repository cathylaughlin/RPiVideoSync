# RPiVideoSync
quick scripts to (semi-)sync two videos via wifi on two Raspberry Pis (omxplayer)  

to install: 
get the stock 'Raspbian / Raspberry Pi OS with desktop'

use the desktop to set up wifi for both Pis. make sure the IP address stays the same for both (either use a static IP or DHCP reservations)
ensure python3 is installed
pip install python-osc
pip install omxplayer
sudo raspi-config, set your Pi to boot to the command line (so the desktop won't show behind the videos) and, optionally, auto-login

to run:
(the manager, on 192.168.y.y): ./RPiVideoSync -m --ip=192.168.x.x 
(the subordinate, on 192.168.x.x): ./RPiVideoSync -s --ip=192.168.y.y 

to run forever:
sudo crontab -e
@reboot full/path/to/RPiVideoSync -m --ip=192.168.x.x
OR 
@reboot full/path/to/RPiVideoSync -s --ip=192.168.y.y 

use the json file created the first time you run it to change settings / control how omxplayer starts (aspect mode, audio outputs, etc)
