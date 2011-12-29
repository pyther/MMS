#!/usr/bin/env python2

import subprocess
import sys
from time import sleep
import string, random
import os

# Write commands to file instead of executing them
debug=True

vlcBin='/usr/bin/cvlc'

def generateDst(dest):
    port=''
    dst=''
    if dest['protocol']=='rtp':
        try:
            stream,port=dest['address'].split(':')
        except ValueError:
               # Likely just the stream
               stream=dest['address']

        dst='rtp{dst='+stream+','
        if port:
            dst+="port="+port+','
        dst+='mux=ts}'
    return dst

def vlcOpts(destinations):
    # Sout Code
    sout='#duplicate{'
    for (counter, dest) in enumerate(destinations):
        sout+="dst="+generateDst(dest)
        if (counter+1) != len(dest):
            sout+=','
    sout+='}'

    opts=[]

    # File Logging
    opts+=['--file-logging', '--logfile=/home/g09/vlc.log']

    # Daemon
    opts+=['--daemon']

    # Pid File
    pidfile='/tmp/vlc-'+''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))+'.pid'
    opts+=['--pidfile', pidfile]

    #Sout
    opts+=['--sout', sout]

    return opts

# v4l2, ivtv, and other devices that don't require addition vlc opts
def startStream(device, destinations):
    opts=[]


    return startVLC(opts, destinations) # startVLC returns PID


# for dvb devices
def startStream(device, destinations, frequency=None, program=None, modulation=None):
    vlcCmd=[vlcBin]

    opts=[]
    opts+=vlcOpts(destinations)

    # DVB Device
    if frequency and program and modulation:
        # DVB Settings ( adapter, channel, frequency, modulation, program)
        opts+=['--dvb-adapter',device,'--dvb-frequency', frequency, '--dvb-modulation', modulation, '--program', program]
        device='dvb://' # DVB device
    else:
        if os.path.isfile(device):
            opts+=['--loop']

    # Generate VLC Command
    vlcCmd=[vlcBin] + opts + [device]

    # Execute Command and Fork in background
    if debug:
        print(' '.join(vlcCmd))
    else:
        p = subprocess.Popen(vlcCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, close_fds=True)

    # Sleep 0.5 seconds so pid file can be created
    sleep(0.5)

    if debug:
        pid=9999
    else:
        file=open(pidfile, 'r')
        pid=file.readline().strip('\n')
        file.close()

    return str(pid);

# We only have support for PVR devices
def v4l2(cinput, device):
    cmd=['/usr/local/bin/v4l2-ctl', '-i', cinput, '-d', device]
    if debug:
        print(' '.join(cmd))
    else:
        p = subprocess.Popen(cmd)

    return 0

def ivtvTune(device, channel, modulation):
    cmd=['/usr/local/bin/ivtv-tune', '-t', modulation, '-d', device, '-c', channel]
    if debug:
        print(' '.join(cmd))
    else:
        p = subprocess.Popen(cmd)
        p.wait()
        if not p.returncode == 0:
            return 1
    return 0
