#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseServerError
from django.template import RequestContext
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.db import transaction

from rapidsms.webui.utils import *
from smartconnect.models import *
from smartconnect.forms import *
from reporters.utils import *

def index(req):
    return render_to_response(req,
        "smartconnect/index.html", {
        "smartconnectclients": paginated(req, SmartConnectClient.objects.all(), prefix="sc")
    })

def message(req, msg, link=None):
    return render_to_response(req,
        "message.html", {
            "message": msg,
            "link": link
    })

def display_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    reports = SmartConnectReport.objects.filter(reporting_device=device)
    
    return render_to_response(req,
        "smartconnect/device.html", {
            # The specific device we're working with
            "smartconnectdevice":   device,
            # The set of all reports we've received from this device
            "reports":              reports})

    
@require_http_methods(["GET", "POST"])
def delete_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    reports = SmartConnectReport.objects.filter(reporting_device=device)
    
    def get(req):
        return render_to_response(req,
            "smartconnect/device_delete.html", {
            "smartconnectdevice":   device,
            "reports":              reports
        })
        
    def post(req):
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            alias = device.alias
            
            #delete the device...
            device.delete()
            
            #and all the reports it created
            reports.delete()
            
            return message(req,
                "SmartConnect IMEI:  %s deleted" % (alias),
                link="/smartconnect")
                
        else:
            return index(req)        

    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)



def edit_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    reports = SmartConnectReport.objects.filter(reporting_device=device)

    def get(req):
        return render_to_response(req,
            "smartconnect/device_edit.html", {
            "smartconnectdevice":   device,
            "reports":              reports
        })

    def post(req):
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            alias = device.alias

            return message(req,
                "SmartConnect IMEI:  %s deleted" % (alias),
                link="/smartconnect")

        else:
            return index(req)

    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)

def django_form(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    reports = SmartConnectReport.objects.filter(reporting_device=device)
    form = SmartConnectDeviceForm(instance = device)

    def get(req):
        
        return render_to_response(req,'smartconnect/testform.html', {
            'form': form,
            "device":   device,
            "reports":              reports
        })
        
    def post(req):
        return render_to_response(req,'smartconnect/testform.html', {
            'form': form,
            "device":   device,
            "reports":              reports
        }) 


    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)
