# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from streamer.models import Channel, Source, Destination, ActiveStream
from django.utils import simplejson
from django import forms
from django.conf import settings
import vlc
import datetime
import os
import time

DEBUG_CMD = settings.DEBUG_CMD

class ChoiceFieldNoValidation(forms.ChoiceField):
    # Remove Validation Checks in ChoiceField
    def validate(self, value):
        pass

class StreamForm(forms.Form):
    sources = forms.ModelChoiceField(queryset=Source.objects.all().order_by('name'))
    channels = ChoiceFieldNoValidation(required=False)
    files = ChoiceFieldNoValidation(required=False)
    destinations = forms.ModelMultipleChoiceField(
        queryset=Destination.objects.all(),
        widget=forms.widgets.CheckboxSelectMultiple,
        initial=Destination.objects.filter(default=True),
        error_messages={'required': 'At least one destination must be selected'}
    )

    # Ensures source isn't already in use
    def clean_sources(self):
        s = self.cleaned_data['sources']

        if not s.type == 'file':
            for obj in ActiveStream.objects.all():
                if obj.sourceInUse(s.id):
                    raise ValidationError("%s is in USE!" % s.name)

        return s

    # Makes sure destinations selected aren't being used
    def clean_destinations(self):
        dstObjs = self.cleaned_data['destinations']

        for dst in dstObjs:
            for obj in ActiveStream.objects.all():
                if obj.dstInUse(str(dst.id)):
                    raise ValidationError("%s is in USE!" % dst.name)
        return dstObjs

class StreamInfo:
    def __init__(self, sourceName, channelId, fileName, dstNames, time, id, channels):
        self.sourceName = sourceName
        self.channelId = channelId
        self.fileName = fileName
        self.dstNames = dstNames
        self.time = time
        self.id = id
        self.channels = channels
        # Running (Is the PID Alive)

def index(request):
    # Orders channels by channels, allows user to change channel for a given stream
    channel_objects=Channel.objects.order_by('number')

    # Go through each Stream and get some information about it
    streams=[]
    for stream in ActiveStream.objects.all():
        sObj=Source.objects.get(id=stream.sourceId)
        sourceID=sObj.id
        sourceName=sObj.name
        fileName=stream.fileName

        # Get the source Channels
        cobj=Channel.objects.filter(channelList=sObj.channelList)
        channels=cobj.extra(select={"decimal": "CAST(number as DECIMAL)"}).order_by("decimal")

        # Store channelID if set
        try:
            channelID=int(stream.channelId)
        except:
            channelID=''

        # Multiple Destination IDs are stored in the DstIds streams (as a string)
        # Split, so we can look up individual destinations
        dstIds=stream.dstIds.split(',')
        dstNames=[ Destination.objects.get(id=id).name for id in dstIds ]

        starttime=stream.time
        id=stream.id

        streams.append(StreamInfo(sourceName, channelID, fileName, dstNames, starttime, id, channels))
    return render_to_response('streamer/index.html', {'streams':streams})

# Allows user to start the stream
def start(request):
    if request.method == 'POST':
        form = StreamForm(request.POST)
        if form.is_valid():
            # Source Info
            source_obj = form.cleaned_data['sources']
            sId = source_obj.id
            sType = source_obj.type
            sDevice = source_obj.device
            sInput = source_obj.input
            sChannelList = source_obj.channelList

            # File Info
            file = form.cleaned_data['files']

            if file:
                fileName=os.path.split(file)[-1]
            else:
                fileName=''

            if source_obj.channelList:
                channelId = form.cleaned_data['channels']
                c=Channel.objects.get(id=channelId)
            else:
                channelId = ''

            # Stream Info
            dstObjs = form.cleaned_data['destinations']

            # Tune Capture Card and Start Stream
            # Handle Different Source Types
            if sType == "file":
                mediafile=os.path.join(sDevice, file)
                #pid=9999
                pid=vlc.startStream(mediafile, dstObjs)
            elif sType == "ivtv":
                vlc.v4l2ctl(sInput, sDevice)
                if channelId:
                    vlc.ivtvTune(sDevice, c.number, c.modulation)
                pvrDevice="pvr:/"+sDevice
                pid=vlc.startStream(pvrDevice, dstObjs)
            elif sType == "dvb":
                pid=vlc.startStream(sDevice, dstObjs, c.frequency, c.program, c.modulation)

            # Get destination IDs to store into DB
            dstIds=','.join([ str(dst.id) for dst in dstObjs ])

            # Temporary PID
            s = ActiveStream(pid=pid, sourceId=sId, channelId=channelId, fileName=fileName, dstIds=dstIds, time=datetime.datetime.now())
            s.save()
            #return HttpResponse(str(pid))
            return HttpResponseRedirect(reverse('streamer.views.index'))
    else:
        form = StreamForm()

    return render_to_response('streamer/start.html', {'form':form,}, context_instance=RequestContext(request))

def json(request):
    if request.method == "GET" and request.GET.has_key('source') and request.GET.get(u'source'):
        id_source = request.GET.get(u'source')
        sObj = get_object_or_404(Source, id=id_source)
        sType = str(sObj.type).lower()

        # If we have a file source type - get list of files
        # If a channel list is defined - get list of channels
        files=[]
        channels=[]
        if sType == "file":
            path = os.path.normpath(sObj.device)

            if os.path.isdir(path):
                for file in os.listdir(path):
                    try:
                        name,ext=file.rsplit('.',1)
                        if ext in ("mpg", "mpeg"):
                            files.append(file)
                    except:
                        pass
        # If source has a channelList associated with it
        elif sObj.channelList:
            # Select channels in Channel List
            # Order channels by number
            cobj=Channel.objects.filter(channelList=sObj.channelList)
            # Sort by Decimal Order
            cobj=cobj.extra(select={"decimal": "CAST(number as DECIMAL)"}).order_by("decimal")
            #for c in .order_by('number'):
            for c in cobj:
                channels.append({'id':c.id,'name':str(c)})

    else:
        return HttpResponseBadRequest('No Data Found')

    # Sort Files
    files=sorted(files)

    json = simplejson.dumps({'files':files,'channels':channels})
    return HttpResponse(json, mimetype='application/json')

def change(request, stream_id, channelId):
    '''Change the TV Channel'''
    streamObj=get_object_or_404(ActiveStream,id=stream_id)
    sourceObj=get_object_or_404(Source,id=streamObj.sourceId)
    sType=sourceObj.type
    sDevice=sourceObj.device
    c=get_object_or_404(Channel,id=channelId)

    if sType == 'ivtv':
        vlc.ivtvTune(sDevice, c.number, c.modulation)
        streamObj.channelId=channelId
        streamObj.save()
    # Restart VLC, yuck
    elif sType == 'dvb':
        # Get Active Stream destinations
        dstIds=str(streamObj.dstIds).split(',')
        # Get  all active stream dst objects
        dstObjs=[ Destination.objects.get(id=dstId) for dstId in dstIds ]

        # Kill Stream
        if DEBUG_CMD:
            print "Kill " + str(streamObj.pid)
        else:
            # Issue Kill Command
            # Wait 10 seconds for VLC to close
            os.kill(streamObj.pid, 15)
            fin_time = time.time() + 10 # wait a max of 10 seconds
            while time.time() < fin_time:
                try:
                    os.kill(streamObj.pid,0)
                except OSError:
                    break
                time.sleep(0.1)

        # Start Stream
        pid=vlc.startStream(sDevice, dstObjs, c.frequency, c.program, c.modulation)

        # Update Channel ID & PID
        streamObj.channelId=channelId
        streamObj.pid=pid
        streamObj.save()
    else:
        return HttpResponseBadRequest('Can\'t change channel for source: ' + input_type)
    return HttpResponse('Channel Changed')

def kill(request, stream_id):
    '''Removes a stream'''
    s=get_object_or_404(ActiveStream,id=stream_id)

    # GET PID
    if DEBUG_CMD:
        print "Kill " + str(s.pid)
    else:
        os.kill(s.pid, 15)
    s.delete()
    return HttpResponseRedirect(reverse('streamer.views.index'))
