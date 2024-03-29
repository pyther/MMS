from streamer.models import ChannelList, Channel, Source, Destination, ActiveStream, Setting
from django.contrib import admin

class ChannelAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'frequency', 'program', 'modulation', 'channelList')
    ordering = ['number']

class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'device', 'input', 'channelList')

class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'protocol', 'address', 'default')

class ActiveStreamAdmin(admin.ModelAdmin):
    list_display = ('pid', 'sourceId', 'channelId', 'dstIds', 'time')

class SettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')

admin.site.register(ChannelList)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(Destination, DestinationAdmin)
admin.site.register(ActiveStream, ActiveStreamAdmin)
admin.site.register(Setting, SettingAdmin)
