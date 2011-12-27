#!/usr/bin/env python2

import subprocess
import sys
from time import sleep
import string, random
import os

def generateDst(stream):
    port=''
    dst=''
    if stream['proto']=='rtp':
        try:
            stream,port=stream['addr'].split(':')
        except ValueError:
               # Likely just the stream
               stream=stream['addr']

        dst='rtp{dst='+stream+','
        if port:
            dst+="port="+port+','
        dst+='mux=ts}'
    return dst



def startStream(device, streams):
    if len(streams) == 0:
        sout='#'+genaretDst(streams[0])
    else:
        sout='#duplicate{'
        for (counter, stream) in enumerate(streams):
            sout+="dst="+generateDst(stream)
            if (counter+1) != len(streams):
                sout+=','
        sout+='}'

    vlcCmd=['/usr/bin/cvlc']

    # File Logging
    vlcCmd+=['--file-logging', '--logfile=/home/g09/vlc.log']

    # Daemon
    vlcCmd+=['--daemon']

    # Pid File
    pidfile='/tmp/vlc-'+''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))+'.pid'
    vlcCmd+=['--pidfile', pidfile]

    if os.path.isfile(device):
        vlcCmd+=['--loop']

    #Sout
    vlcCmd+=['--sout', sout]

    # Device
    vlcCmd+=[device]

    p = subprocess.Popen(vlcCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, close_fds=True)

    # Sleep 0.5 seconds so pid file can be created
    sleep(0.5)

    file=open(pidfile, 'r')
    pid=file.readline().strip('\n')
    file.close()

    return str(pid);

# We only have support for PVR devices
def tune(input_type, input_source, channel, path):
    device=path.split(':/')

    if device[0]=="pvr":
        # Change Input Source
        p = subprocess.Popen(['/usr/local/bin/v4l2-ctl', '-i', input_source, '-d', device[1]])

        if input_type == "tv":
            tuneChannel(channel, path)
    else:
        return 1
    return 0

def tuneChannel(channel, path):
    device=path.split(':/')
    if device[0]=="pvr":
        p = subprocess.Popen(['/usr/local/bin/ivtv-tune', '-t', 'us-cable', '-d', device[1], '-c', channel])
        p.wait()
        if not p.returncode == 0:
            return 1
    else:
        return 1
    return 0
