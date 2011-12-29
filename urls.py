from django.conf.urls.defaults import patterns, include, url
#from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('streamer.views',
    # Examples:
    url(r'^$', 'index', name='index'),
    url(r'^start/$', 'start', name='start'),
    url(r'^json/$', 'json', name='json'),
    url(r'^kill/(?P<stream_id>\d+)/$', 'kill', name='kill'),
    url(r'^stream/(?P<stream_id>\d+)/change/(?P<channelId>\d+)/$', 'change', name='change'),
    # url(r'^mms/', include('mms.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
#urlpatterns += staticfiles_urlpatterns()
