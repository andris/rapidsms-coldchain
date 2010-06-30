import time
import pytz 
from datetime import datetime

from smartconnect.models import *
from rapidsms.utils import *

from django import template

register = template.Library()

@register.filter
def to_js_timestamp(value):
    try:
        return int(time.mktime(value.timetuple())*1000)
    except AttributeError:
        return ''

@register.filter
def to_local_time(value):
    try:
        #return pytz.utc.localize(value)
        aware_dt = to_aware_utc_dt(value)
        return aware_dt.astimezone(pytz.timezone(time.tzname))
    except AttributeError:
        return aware_dt
