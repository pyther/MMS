#!/usr/bin/env python2

import subprocess
import sys
from time import sleep
import string, random
import os
from django.conf import settings

# Write commands to file instead of executing them
DEBUG_CMD = settings.DEBUG_CMD

vlcBin='/usr/bin/cvlc'

def generateDst(dst):
    port=''
    txt=''
    if dst.protocol == 'rtp':
        try:
            stream,port=str(dst.address).split(':')
        except ValueError:
               # Likely just the stream
               stream=dst.address

        txt='rtp{dst='+stream+','
        if port:
            txt+="port="+port+','
        txt+='mux=ts}'
    return txt

def vlcOpts(dstObjs, pidFile):
    # Sout Code
    sout='#duplicate{'+','.join(["dst="+generateDst(dst) for dst in dstObjs])+'}'

    opts=[]

    # File Logging
    opts+=['--file-logging', '--logfile=/home/g09/vlc.log']

    # Daemon
    opts+=['--daemon']

    # Pid File
    opts+=['--pidfile', pidFile]

    #Sout
    opts+=['--sout', sout]

    return opts


# for dvb devices
def startStream(device, dstObjs, frequency=None, program=None, modulation=None):
    vlcCmd=[vlcBin]

    opts=[]
    pidFile='/tmp/vlc-'+''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))+'.pid'
    opts+=vlcOpts(dstObjs, pidFile)

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
    if DEBUG_CMD:
        print(' '.join(vlcCmd))
    else:
        p = subprocess.Popen(vlcCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, close_fds=True)

    # Sleep 0.5 seconds so pid file can be created
    sleep(0.5)

    if DEBUG_CMD:
        pid=9999
    else:
        file=open(pidfile, 'r')
        pid=file.readline().strip('\n')
        file.close()

    return str(pid);

# We only have support for PVR devices
def v4l2ctl(cinput, device):
    cmd=['/usr/local/bin/v4l2-ctl', '-i', cinput, '-d', device]
    if DEBUG_CMD:
        print(' '.join(cmd))
    else:
        p = subprocess.Popen(cmd)

    return 0

def ivtvTune(device, channel, modulation):
    cmd=['/usr/local/bin/ivtv-tune', '-t', modulation, '-d', device, '-c', channel]
    if DEBUG_CMD:
        print(' '.join(cmd))
    else:
        p = subprocess.Popen(cmd)
        p.wait()
        if not p.returncode == 0:
            return 1
    return 0
