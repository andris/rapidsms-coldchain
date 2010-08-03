from django import forms
from django.forms import ModelForm
from smartconnect.models import *

class SmartConnectDeviceForm(ModelForm):
    class Meta:
        model = SmartConnectClient
        fields = (
            'first_name',
            'last_name',
            #'low_thresh', 
            #'high_thresh', 
            'report_freq', 
            'alert_freq',
            'watchers')
            
class SmartConnectTempForm(forms.Form):
    low_thresh_c = forms.IntegerField(required=True)
    high_thresh_c = forms.IntegerField(required=True)

class SmartConnectPreferencesForm(ModelForm):
    class Meta:
        model = SmartConnectPreferences
        fields = (
            'default_low_thresh',
            'default_high_thresh',
            'default_report_freq',
            'default_alert_freq',
            'default_watcher_group')

class MessageForm(forms.Form):
    text = forms.CharField(required=True, max_length=158)
