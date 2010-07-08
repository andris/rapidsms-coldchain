from django.db import models
from reporters.models import Location, Reporter, PersistantConnection

#Representation of a SmartConnect sensor (extends reporter)
class SmartConnectClient(Reporter):
    #The sensor reports if it has ever been configured by us
    is_configured = models.BooleanField(default=False)

    #lowest temperature can drop before alert (in K)
    low_thresh = models.PositiveIntegerField(null=False, default=0)
	
    #highest temperature can go before alert (in K)
    high_thresh = models.PositiveIntegerField(null=False, default=0)
	
    #how often to send standard temperature updates (in minutes)
    report_freq = models.PositiveIntegerField(null=False, default=0)
	
    #how often to send updates when in alert state (in minutes)
    alert_freq = models.PositiveIntegerField(null=False, default=0)
	
    #timeout.  Unused.  (in milleseconds)
    timeout = models.PositiveIntegerField(null=False, default=0)
	
    #firmware version of smart connect device
    fw_version = models.CharField(null=False, max_length=20)
    
    #is this device currently alerting?
    alert_status = models.BooleanField(default=False)
    
    #Current temperature (in K)
    current_temp = models.PositiveIntegerField(null=False, default=273)
    
    #Last Received Text MSG
    last_text = models.CharField(null=False, max_length=158)
	
    def __unicode__(self):
        if self.connection():
            return self.connection().identity
        return self.alias

class SmartConnectReport(models.Model):
    #The SC device that sent this report
    reporting_device = models.ForeignKey(SmartConnectClient, null=True, blank=True)
	
    #The Connection this report came in on
    connection = models.ForeignKey(PersistantConnection, null=True, blank=True)
	
    #Three letter code for report type...currently using TMP for temperature
    type = models.CharField(max_length=3)
	
    #The reported temperature (in K)
    value = models.PositiveIntegerField(null=False, default=0)
    
    #The time of report (this should eventually be the message _sent_ time)
    time = models.DateTimeField()
    
    #Was this flagged as an alert by the reporting device?
    is_alert = models.BooleanField(default=False)

    #Have we acknowledged this event / alert yet?
    is_acknowledged = models.BooleanField(default=False)
    
    #These only apply for alerts not regular reports
    ceiling = models.PositiveIntegerField(null=False, default=0)
    floor = models.PositiveIntegerField(null=False, default=0)

    def __unicode__(self):
        string = ("SmartConnect Event,"
            + " time: " + self.time.ctime()
            + " type: " + str(self.type)
            + " value: " + str(self.value)
            + " is_alert " + str(self.is_alert)
            + " is_acknowledged " + str(self.is_acknowledged)
            + " floor " + str(self.floor)
            + " ceiling " + str(self.ceiling))
            
        return string
