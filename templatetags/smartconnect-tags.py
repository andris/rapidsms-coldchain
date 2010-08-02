import os,time,calendar
import pytz 
from datetime import datetime

from smartconnect.models import *
from rapidsms.utils import *

from django import template
register = template.Library()

from django.utils.timesince import timesince
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.template.defaultfilters import date as filter_date, time as filter_time

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


@register.filter()
def sc_last_seen(value, autoescape=None):
    """Formats a datetime as an HTML string representing a
       short digest of the time since that date, contained
       by a <span>, with a title (tooltip) of the full date."""
    
    # if autoescaping is on, then we will
    # need to pass outgoing strings through
    # cond_esc, or django will escape the HTML
    if autoescape: esc = conditional_escape
    else:          esc = lambda x: x

    try:
        if value:
        
            #convert to time aware local time first
            localized_value = to_local_time(value)
            
            # looks like we have a valid date - return
            # a span containing the long and short version
            ts = timesince(localized_value)
            mag = magnitude_ago(localized_value)
            long = "on %s at %s" % (filter_date(localized_value), filter_time(localized_value))
            out = '<span class="last-seen %s" title="%s">%s ago</span>' % (esc(mag), esc(long), esc(ts))
        
        # abort if there is no date (it's
        # probably just a null model field)
        else:
            out = '<span class="last-seen n/a">Never</span>'
    
    # something went wrong! don't blow up
    # the entire template, just flag it
    except (ValueError, TypeError):
        out = '<span class="last-seen error">Error</span>'
    
    return mark_safe(out)
sc_last_seen.needs_autoescape = True

#Should import this from reporters, but needed it for the modified
#last_seen to support utc time storage
def magnitude_ago(value):
    """Given a datetime, returns a string containing the
       most appropriate unit to use when describing the
       time since that date, out of: minutes, hours, days,
       months, years."""
    
    # TODO: implement
    return "hours"
