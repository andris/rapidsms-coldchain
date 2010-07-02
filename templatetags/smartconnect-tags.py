import os,time,calendar
import pytz 
from datetime import datetime

from smartconnect.models import *
from rapidsms.utils import *

from django import template


register = template.Library()

@register.filter
def to_js_timestamp(value):
    try:
        return int(calendar.timegm(to_local_time(value).timetuple())*1000)
    except AttributeError:
        return ''

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
