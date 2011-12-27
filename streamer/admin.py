from streamer.models import channelList, Channel, Source, Destination, Stream, Setting, Protocol, SourceType
from django.contrib import admin

class channelAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'frequency', 'program', 'modulation', 'channelList')
    ordering = ['number']

class sourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'device', 'input', 'channelList')

class destinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'protocol', 'address', 'default')

class streamAdmin(admin.ModelAdmin):
    list_display = ('pid', 'input_id', 'channel', 'outputs', 'time')

class settingAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')

admin.site.register(channelList)
admin.site.register(Channel, channelAdmin)
admin.site.register(Source, sourceAdmin)
admin.site.register(Destination, destinationAdmin)
admin.site.register(Stream, streamAdmin)
admin.site.register(Setting, settingAdmin)
admin.site.register(Protocol)
admin.site.register(SourceType)
