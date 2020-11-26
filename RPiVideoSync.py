#!/usr/bin/env python3

################################
#
# useful options (in the RPiVideoSync.json file):
#
# AudioOutput: ["local", "hdmi", or "both"] sets audio output to the headphone jack (local) or HDMI (hdmi) or (both)
#
# AspectMode: ["letterbox", "fill", "stretch"]. stretch looks horrible. set 'fill' to go fullscreen or 'letterbox' to add black bars
#
# to start: /path/to/RPiVideoSync [-m|-s] [--ip=x.x.x.x]
#
# where m / s is 'manager / subordinate' and the IP is the address of the other pi.
# run this script twice on two computers, one with -m and one with -s, in order to start the sync
#
################################

from omxplayer.player import OMXPlayer
import argparse
import sys
import subprocess
from pathlib import Path
from time import sleep
import time, datetime
import logging
import logging.handlers
import os
import glob
import signal
import socket
import traceback
import socketserver
import json
import threading
import random
from math import floor
from pythonosc import dispatcher
from pythonosc import osc_message_builder
from pythonosc import udp_client
from pythonosc import osc_server
# to install packages:
# pip3 install python-osc
# pip3 install omxplayer-wrapper 

audio_output = 'local' # holds the current audio output mode
aspect_mode = 'fill' # holds the current display mode
AUDIO_OUTPUT = 'AudioOutput'
ASPECT_MODE = 'AspectMode'

player = None # holds omxplayer-wrapper's player object
logger = None # logs stuff

LISTEN_PORT = 6666 

ready = 0
playing = 0
video_len = 0
syncnum = 1
run = 1

scriptname = os.path.basename(__file__)
SETTINGS_FILE = 'RPiVideoSync.json' # settings file in the current directory

# give a filename for the log file here
LOG_FILENAME = 'RPiVideoSync.out'
# give the size for each rolling log segment, in bytes
LOG_SIZE = 2000000 #2 MB, in bytes
# give the number of rolling log segments to record before the log rolls over
LOG_NUM_BACKUPS = 2 # two .out files before they roll over

####################
# EXIT HANDLER
####################
# this runs when omxplayer stops
def onOMXPlayerExit(code):
  pass

####################
# EXIT HANDLER
####################
# upon exit, save settings, kill the videos
def exit_func():
  try:
    write_json()
    sleep(.3)
    logger.info ("exiting")
    sys.exit(0)
  except Exception as e:
    logger.info ("Error in exit_func: %s" % e)

# exits the program cleanly
def signal_handler(signal, frame):
  print ("")
  exit_func()
    
signal.signal(signal.SIGINT, signal_handler)

####################
# validate_audio_output()
####################
# validates omxplayer's audio output options (as read from the JSON file)
def validate_audio_output():
  global audio_output
  if audio_output.lower() == "hdmi" or audio_output.lower() == "local" or audio_output.lower() == "both":
    audio_output = audio_output.lower()
  else:
    logger.info("audio output option %s not found. valid options are 'hdmi', 'local', or 'both'. defaulting to 'local'." % audio_output)
    audio_output = 'local'
  return

####################
# validate_aspect_mode()
####################
# validates omxplayer's aspect mode options (as read from the JSON file)
def validate_aspect_mode():
  global aspect_mode
  if aspect_mode.lower() == "letterbox" or aspect_mode.lower() == "fill" or aspect_mode.lower() == "stretch":
    aspect_mode = aspect_mode.lower()
  else:
    logger.info("aspect mode option %s not found. valid options are 'letterbox', 'fill', or 'stretch'. defaulting to 'fill'." % aspect_mode)
    aspect_mode = 'fill'
  return

####################
# read_json()
####################
# reads the settings file 
def read_json():
  global current_vol
  global audio_output
  global aspect_mode
  try:
    with open(SETTINGS_FILE) as json_file:
      data = json.load(json_file)
      audio_output = data[AUDIO_OUTPUT]
      aspect_mode = data[ASPECT_MODE]
      validate_audio_output()
      validate_aspect_mode()
  except Exception as e:
    logger.info ("Error in read_json! %s" % e)
    for frame in traceback.extract_tb(sys.exc_info()[2]):
      fname,lineno,fn,text = frame
      logger.info( "     in %s on line %d" % (fname, lineno))

####################
# write_json()
####################
# writes the settings file
def write_json():
  try:
    new_json = {}
    new_json[AUDIO_OUTPUT] = audio_output
    new_json[ASPECT_MODE] = aspect_mode
    logger.info ("saving audio output %s aspect mode %s " % (audio_output, aspect_mode))
    with open(SETTINGS_FILE, 'w') as outfile:
      json.dump(new_json, outfile)
      
  except Exception as e:
    logger.info ("Error in write_json, can't save options! %s" % e)
    for frame in traceback.extract_tb(sys.exc_info()[2]):
      fname,lineno,fn,text = frame
      logger.info( "     in %s on line %d" % (fname, lineno))

######################
# send_to_osc
######################
# sends OSC messages
def send_to_osc(remote_ip, port, cmd, args):
    try:
      print("remote ip %s port %s cmd %s args %s" % (remote_ip, port, cmd, args))
      client = udp_client.SimpleUDPClient(remote_ip, port)
      client.send_message(cmd, args)
    except Exception as e:
        logger.info("Error in send_to_osc: %s" % e)
        for frame in traceback.extract_tb(sys.exc_info()[2]):
          fname,lineno,fn,text = frame
          logger.info( "     in %s on line %d" % (fname, lineno))

##############################
# quit_callback
##############################
# quits playing the video. should drop to a black screen
def quit_callback(path):
  logger.info ("/stop")
  player.stop()

##############################
# go_callback
##############################
# checks to see if we are ready, and if so, goes
def go_callback(path):
  global playing
  logger.info ("/go")  
  if (args.subordinate and ready):
    print("go!")
    player.play()
    playing = 1
    
##############################
# ready_callback
##############################
# checks to see if we are ready, and replies accordingly. or does nothing!
def ready_callback(path):
  global playing
  if (args.manager):
    if (ready):
      print("reply go")
      # sends the signal to go and then goes!
      send_to_osc(args.ip_address, LISTEN_PORT, "/go", [])
      playing = 1
      player.play()
  elif (args.subordinate):
    if (ready):
      print("reply ready")
      send_to_osc(args.ip_address, LISTEN_PORT, "/ready", [])
      # sends back 'ready' so the manager will send 'go'
  
##############################
# get_ready
##############################
# does our jump / pause so the videos can sync to the same spot, then sets 'ready'
def get_ready():
  global ready
  try:

    time.sleep(.5)
    player.set_position(0)
    time.sleep(.5)
    player.pause()
    time.sleep(.5)

    ready = 1
    
  except Exception as e:
    logger.info ("Error in get_ready: %s" % e)
    for frame in traceback.extract_tb(sys.exc_info()[2]):
      fname,lineno,fn,text = frame
      logger.info( "     in %s on line %d" % (fname, lineno))

##############################
# start_osc()
##############################
# register our callbacks and starts a threaded OSC server
def start_osc():
  #register the callbacks for OSC adresses
  dispatcher1 = dispatcher.Dispatcher()
  dispatcher1.map("/", got_callback)
  dispatcher1.map("/stop", quit_callback)
  dispatcher1.map("/ready", ready_callback)
  dispatcher1.map("/go", go_callback)
  
  socketserver.UDPServer.allow_reuse_address = True
  server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", LISTEN_PORT), dispatcher1)
  server_thread = threading.Thread(target=server.serve_forever)
  server_thread.daemon = True
  server_thread.start() # starts the OSC server in the background
    
##############################
# load_omxplayer
##############################
# initialize the player, load the video
def load_omxplayer():
  global player
  global ready
  try:
    player.quit() # in case it's already running
  except Exception as e:
    pass
  try:
      logger.info("playing %s" % args.filename)
      filepath = Path(args.filename)

      #creates OMXPlayer-wrapper with filename and options
      player = OMXPlayer(filepath, args=['--loop', '--no-osd', '--aspect-mode', aspect_mode, '-o',
                                         audio_output],
                         dbus_name='org.mpris.MediaPlayer2.omxplayer1')
      
      logger.info([filepath, '--loop', '--no-osd', '--aspect-mode', aspect_mode, '-o',
                                         audio_output])

      # exit handling
      player.exitEvent += lambda _, exit_code: onOMXPlayerExit(exit_code)
      time.sleep(.5)
      player.pause()

  except Exception as e:
    logger.info ("Error in load_omxplayer: %s." % e)
    for frame in traceback.extract_tb(sys.exc_info()[2]):
      fname,lineno,fn,text = frame
      logger.info( "     in %s on line %d" % (fname, lineno))

##############################
# wipe_tmp()
##############################
# deletes /tmp/omxplayer* files before starting, to prevent DBUS hangups.
def wipe_tmp():
  import glob
  try:
    filelist = glob.glob('/tmp/omxplayer*')
    print("delete %s? ctrl-c to stop." % filelist)
    time.sleep(2)
    for item in filelist:
      os.remove(item)
  except Exception as e:
    logger.info ("Error in wipe_tmp: %s." % e)
    for frame in traceback.extract_tb(sys.exc_info()[2]):
      fname,lineno,fn,text = frame
      logger.info( "     in %s on line %d" % (fname, lineno))

####################
# setup_logger()
####################
# sets up error logging
def setup_logger():
    global logger
    LEVELS = { 'debug':logging.DEBUG,
               'info':logging.INFO,
               'warning':logging.WARNING,
               'error':logging.ERROR,
               'critical':logging.CRITICAL,
               }

    # default log level is info (prints info, warning, error, etc).
    # run with "RPiVideoSync debug" to print/log debug messages

    if len(sys.argv) > 1:
        level_name = sys.argv[1]
        level = LEVELS.get(level_name, logging.NOTSET)
        logging.basicConfig(level=level)
    else:
        level = LEVELS.get('info', logging.NOTSET)
        logging.basicConfig(level=level)
    
    # creates our logger with the settings above/below
    logger = logging.getLogger('RPiVideoSyncLog')

    try:
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                                   maxBytes=LOG_SIZE,
                                                   backupCount=LOG_NUM_BACKUPS)
    except:
        handler = logging.handlers.RotatingFileHandler(LOCAL_LOG_FILENAME,
                                                       maxBytes=LOG_SIZE,
                                                       backupCount=LOG_NUM_BACKUPS)
        # also set this on error
        frmt = logging.Formatter('%(asctime)s - %(message)s',"%d/%m/%Y %H:%M:%S")
        handler.setFormatter(frmt)
        logger.addHandler(handler)

    frmt = logging.Formatter('%(asctime)s - %(message)s',"%d/%m/%Y %H:%M:%S")
    handler.setFormatter(frmt)
    logger.addHandler(handler)

##############################
# got_callback
##############################    
def got_callback(path, args=None):
  logger.info ("got message %s" % path) # log any message that isn't matched. for debugging
    
##############################
# MAIN
##############################
if __name__ == "__main__":
  try:
    setup_logger() # set up the log file

    # grab our arguments
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--manager',dest='manager',
                       action='store_true',
                       help='starts as the manager (coordinates the sync)' )
    
    group.add_argument('-s', '--subordinate',dest='subordinate',
                       action='store_true',
                       help='starts as the subordinate (receives sync commands)')
    
    parser.add_argument('--ip', '--IP',dest='ip_address',required=True,
                        type=str,
                        help='sets the IP address of the other Pi')
    
    parser.add_argument('-f', '--filename',dest='filename',required=True,
                        type=str,
                        help='sets the video file to play. make sure both computers have the SAME file')
    args = parser.parse_args()
    
    if (not args.manager and not args.subordinate):
      logger.info("one of -m / --manager or -s / --subordinate is required!")
    
    wipe_tmp() # this deletes existing /tmp/omxplayer* files so DBUS can start fresh
    read_json() # this gets settings from our settings file
    start_osc() # starts OSC server in the background
    
    load_omxplayer() # creates the player and starts the first video, then pauses it
    sleep(.2)
    get_ready() # jumps to 0 and pauses again. this is here mostly to give omxplayer time to start up before we jump...
    sleep(.2)
    
    logger.info("RPiVideoSync: port %s" % LISTEN_PORT)

    # this loop manages the sync. the manager sends /ready every 3 seconds or so. if the subordinate is ready
    # (i.e. the video is loaded and paused at 0), then the subordinate sends /ready back.
    # when the manager gets /ready back, it sends /go and then starts the video.
    # when the subordinate gets /go, it starts the video!
    # OSC is fast enough that this provides a decent sync between the two videos...
    
    while run:   # endless loop while the video and OSC run
      if (args.manager):
        #print("ready %s playing %s" % (ready, playing))
        if (ready and not playing):
          # attempt to sync
          print("sync attempt %s" % syncnum)
          syncnum = syncnum + 1
          send_to_osc(args.ip_address, LISTEN_PORT, "/ready", [])        
          time.sleep(3)
        else:
          time.sleep(0.1)

  except Exception as e:
    logger.info ("Error in main: %s" % e)
