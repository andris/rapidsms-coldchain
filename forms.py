from django.forms import ModelForm
from smartconnect.models import *

class SmartConnectDeviceForm(ModelForm):
    class Meta:
        model = SmartConnectClient
        fields = (
            'first_name',
            'last_name',
            'low_thresh', 
            'high_thresh', 
            'report_freq', 
            'alert_freq')
