# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from streamer.models import Channel, Source, Destination, ActiveStream
from django.utils import simplejson
from django import forms
import vlc
import datetime
import os

class ChoiceFieldNoValidation(forms.ChoiceField):
    # Remove Validation Checks in ChoiceField
    def validate(self, value):
        pass

class SimpleStreamForm(forms.Form):
    sources = forms.ModelChoiceField(queryset=Source.objects.all())
    channels = ChoiceFieldNoValidation(required=False)
    files = ChoiceFieldNoValidation(required=False)
    destinations = forms.ModelMultipleChoiceField(queryset=Destination.objects.all(),widget=forms.widgets.CheckboxSelectMultiple,initial=Destination.objects.filter(default=True))

class StreamInfo:
    def __init__(self, sourceName, channelID, dstNames, time, id, channels):
        self.sourceName = sourceName
        self.channelID = channelID
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
        source_obj=Source.objects.get(id=stream.sourceId)
        sourceID=source_obj.id
        sourceName=source_obj.name

        # Get the source Channels
        cobj=Channel.objects.filter(channelList=source_obj.channelList)
        channels=cobj.extra(select={"decimal": "CAST(number as DECIMAL)"}).order_by("decimal")

        # Store channelID if set
        try:
            channelID=int(stream.channel)
        except:
            channelID=''

        # Multiple Destination IDs are stored in the DstIds streams (as a string)
        # Split, so we can look up individual destinations 
        dstIds=stream.dstIds.split(',')
        dstNames=[ Destination.objects.get(id=id).name for id in dstIds ]

        starttime=stream.time
        id=stream.id

        streams.append(StreamInfo(sourceName, channelID, dstNames, starttime, id, channels))
    return render_to_response('streamer/index.html', {'streams':streams})

# Allows user to start the stream
def start(request):
    if request.method == 'POST':
        form = SimpleStreamForm(request.POST)
        if form.is_valid():
            # Source Info
            source_obj = form.cleaned_data['sources']
            sId = source_obj.id
            sType = source_obj.type.name
            sDevice = source_obj.device
            sInput = source_obj.input
            sChannelList = source_obj.channelList

            # File Info
            file = form.cleaned_data['files']
            channelID = form.cleaned_data['channels']

            c=Channel.objects.get(id=channelID)

            # Stream Info
            destination_objs = form.cleaned_data['destinations']
            destinations=[]
            for obj in destination_objs:
                info={}
                info['id'] = obj.id
                info['protocol'] = obj.protocol.name
                info['address'] = obj.address
                destinations.append(info)

            # Sanity Checks - Make sure there isn't another stream going that uses the same resources
            if sType != "file":
                try:
                    ActiveStream.objects.get(sourceId=sId)
                except ActiveStream.DoesNotExist:
                    pass
                else:
                    msg="This Source is currently being USED!"
                    return render_to_response('streamer/start.html', {'form':form,'error_msg':msg}, context_instance=RequestContext(request))


            for dst in destinations:
                for obj in ActiveStream.objects.all():
                    if obj.hasOutput(str(dst['id'])):
                        msg="Stream is in USE!"
                        return render_to_response('streamer/start.html', {'form':form,'error_msg':msg}, context_instance=RequestContext(request))

            # Tune Capture Card and Start Stream
            # Handle Different Source Types
            if sType == "file":
                mediafile=os.path.join(sDevice, file)
                #pid=9999
                pid=vlc.startStream(mediafile, destinations)
            elif sType == "ivtv":
                vlc.v4l2(sInput, sDevice)
                vlc.ivtvTune(sDevice, c.number, c.modulation)
                pid=vlc.startStream(sDevice, destinations)
            elif sType == "v4l2":
                vlc.v4l2(sInput, sDevice)
                pid=vlc.startStream(sDevice, destinations)
            elif sType == "dvb":
                pid=vlc.startStream(sDevice, c.frequency, c.program, c.modulation, destinations)

            # Build and store info to store into DB
            destination_ids=''
            for (counter, dest) in enumerate(destinations):
                destination_ids+=str(dest['id'])
                if len(destinations) != (counter+1):
                    destination_ids+=','

            # Temporary PID
            s = ActiveStream(pid=pid, sourceId=sId, channelId=c.number, dstIds=destination_ids, time=datetime.datetime.now())
            s.save()
            #return HttpResponse(str(pid))
            return HttpResponseRedirect(reverse('streamer.views.index'))
    else:
        form = SimpleStreamForm()

    return render_to_response('streamer/start.html', {'form':form,}, context_instance=RequestContext(request))

def json(request):
    if request.method == "GET" and request.GET.has_key('source') and request.GET.get(u'source'):
        id_source = request.GET.get(u'source')
        source_obj = get_object_or_404(Source, id=id_source)
        source_type = str(source_obj.type).lower()

        # If we have a file source type - get list of files
        # If a channel list is defined - get list of channels
        files=[]
        channels=[]
        if source_type == "file":
            path = os.path.normpath(source_obj.path)

            if os.path.isdir(path):
                for file in os.listdir(path):
                    try:
                        name,ext=file.rsplit('.',1)
                        if ext in ("mpg", "mpeg"):
                            files.append(file)
                    except:
                        pass
        # If source has a channelList associated with it
        elif source_obj.channelList:
            # Select channels in Channel List
            # Order channels by number
            cobj=Channel.objects.filter(channelList=source_obj.channelList)
            # Sort by Decimal Order
            cobj=cobj.extra(select={"decimal": "CAST(number as DECIMAL)"}).order_by("decimal")
            #for c in .order_by('number'):
            for c in cobj:
                channels.append({'id':c.id,'name':str(c)})

    else:
        return HttpResponseBadRequest('No Data Found')

    # Sort Files
    files=sorted(files)
    #return HttpResponse(source_input)
    # "channels": [{ "number": 1, "name": "3 - WKYC"}, {}, {}]
    # $.each(channels, function(i, channel){});
    # $('<option>').attr('value', channel.number).html(channel.text).appendTo('.YourSelectBoxHere'); 
    json = simplejson.dumps({'type':source_type,'files':files,'channels':channels})
    return HttpResponse(json, mimetype='application/json')

def change(request, stream_id, channel):
    '''Change the TV Channel'''
    stream_obj=get_object_or_404(ActiveStream,id=stream_id)
    input_obj=get_object_or_404(Source,id=stream_obj.sourceId)
    input_type=input_obj.type.name
    input_path=input_obj.path

    if input_type=='ivtv':
        vlc.tuneChannel(channel, input_path)
        stream_obj.channel=channel
        stream_obj.save()
    else:
        return HttpResponseBadRequest('Can\'t change channel for source: ' + input_type)
    return HttpResponse('Channel Changed')

def kill(request, stream_id):
    '''Removes a stream'''
    s=get_object_or_404(ActiveStream,id=stream_id)

    # GET PID
    os.kill(s.pid, 15)
    s.delete()
    return HttpResponseRedirect(reverse('streamer.views.index'))
