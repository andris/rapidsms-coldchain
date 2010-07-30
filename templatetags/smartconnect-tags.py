import os,time,calendar
import pytz 
from datetime import datetime

from smartconnect.models import *
from rapidsms.utils import *

from django import template


register = template.Library()

@register.inclusion_tag("smartconnect/partials/device_details.html")
def device_details(smartconnectdevice):
    return { "smartconnectdevice": smartconnectdevice }

@register.filter
def to_js_timestamp(value):
    try:
        #Use this conversion if using the google graphs. 
        #Google graphs expects milliseconds since the epoch in GMT
        return int(calendar.timegm(value.timetuple())*1000)
    except AttributeError:
        return ''

@register.filter
def to_local_js_timestamp(value):
    try:
        #Use this conversion if using the flot graphs.  It needs the 
        #Flot graphs expect milliseconds since the epoch in local.
        return int(calendar.timegm(to_local_time(value).timetuple())*1000)

    except AttributeError:
        return ''
        
#Fot annotating google charts
@register.filter
def get_annotation(report):
    if( report.is_alert ):
        label='Alert'
        text="<br>Actual: %(temp)s\u00B0C <br>Max: %(max)s\u00B0C <br>Min: %(min)s\u00B0C" % {'temp': to_celcius(report.value), 'max': to_celcius(report.ceiling), 'min': to_celcius(report.floor)}
        return '\'%(label)s\',\'%(text)s\'' % {'label': label, 'text': text}
        
    return "undefined,undefined"

@register.filter
def to_celcius(kelvin_temp):
    return int( kelvin_temp - 273 )

@register.filter
def to_kelvin(celcius_temp):
    return int( celcius_temp + 273 )

@register.filter
def to_local_time(value):
    try:
        aware_dt = to_aware_utc_dt(value)
        zone=pytz.timezone(os.getenv('TZ'))
        return aware_dt.astimezone(zone)
    except AttributeError:
        return ''
