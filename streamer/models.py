from django.db import models

# Create your models here.
make_choice = lambda c: [(i, i) for i in c]

class ChannelList(models.Model):
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return str(self.name)

class Channel(models.Model):
    MODULATION_CHOICES = (
        ('us-cable', 'us-cable'),
        ('256', 'QAM-256'),
    )

    number = models.CharField(max_length=6)
    name = models.CharField(max_length=200, blank=True)
    frequency = models.CharField(max_length=10, blank=True)
    program = models.CharField(max_length=2, blank=True)
    modulation = models.CharField(max_length=10, choices = MODULATION_CHOICES)
    channelList = models.ForeignKey('channelList', blank=True)

    def __unicode__(self):
        return str(self.number) + " - " + self.name

class Source(models.Model):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices = make_choice(["ivtv", "dvb", "file"]))
    device = models.CharField(max_length=200)
    input = models.CharField(max_length=20, blank=True)
    channelList = models.ForeignKey('ChannelList', null=True, blank=True)

    def __unicode__(self):
        return self.name;

class Destination(models.Model):
    name = models.CharField(max_length=200)
    protocol = models.CharField(max_length=16, choices = make_choice(["rtp"]))
    address = models.CharField(max_length=200)
    default = models.BooleanField()

    def __unicode__(self):
        return self.name

# Current Running Streams
class ActiveStream(models.Model):
    pid = models.IntegerField()
    sourceId = models.IntegerField()
    channelId = models.CharField(max_length=5,blank=True)
    dstIds = models.CharField(max_length=200)
    time = models.DateTimeField()

    # Source in Use
    def sourceInUse(self, x):
        if x == self.sourceId:
            return True
        return False

    # Desintation in Use? - Return True or False
    def dstInUse(self, x):
        ids=self.dstIds.split(',')
        for id in ids:
            if x == id: return True
        return False

class Setting(models.Model):
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)

