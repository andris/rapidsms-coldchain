#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import httplib, urllib, urllib2
from threading import Thread

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseServerError
from django.template import RequestContext
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout as django_logout
from django.shortcuts import get_object_or_404
from django.db import transaction

from rapidsms.webui.utils import *
from smartconnect.models import *
from smartconnect.forms import *
from reporters.models import *
from reporters.utils import *

@login_required
def index(req):
    return render_to_response(req,
        "smartconnect/index.html", {
        "smartconnectclients": paginated(req, SmartConnectClient.objects.all(), prefix="sc")
    })

def message(req, msg, link=None):
    return render_to_response(req,
        "smartconnect/message.html", {
            "message": msg,
            "link": link
    })

#TODO: should move this to a utils class    
def to_celcius(kelvin_temp):
    return int( kelvin_temp - 273 )

def to_kelvin(celcius_temp):
    return int( celcius_temp + 273 )

@login_required
def display_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    reports = SmartConnectReport.objects.filter(reporting_device=device)
    
    return render_to_response(req,
        "smartconnect/device.html", {
            # The specific device we're working with
            "smartconnectdevice":   device,
            # The set of all reports we've received from this device
            "reports":              reports})

    
@login_required
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


@login_required
def edit_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)

    def get(req):
        form = SmartConnectDeviceForm(instance=device)
        
        #need a separate form to collect user input in celcius
        #we convert to kelvin before storing
        tempform = SmartConnectTempForm(initial={'low_thresh_c': to_celcius(device.low_thresh), 'high_thresh_c': to_celcius(device.high_thresh)})
  
        return render_to_response(req,'smartconnect/device_edit.html', {
            'form':     form,
            'tempform': tempform,
            "device":   device,
        })
        
    def post(req):
        form = SmartConnectDeviceForm(req.POST, instance=device)
        tempform = SmartConnectTempForm(req.POST)
        
        #Make sure they clicked submit
        if req.POST.get("submit", ""):
            if (form.is_valid() and tempform.is_valid()):
            
                form_low_thresh = to_kelvin(tempform.cleaned_data['low_thresh_c'])
                form_high_thresh = to_kelvin(tempform.cleaned_data['high_thresh_c'])
                
                #Test to see if we are going to need to send a CFG update
                #to the device or if we've just changed something internal
                send_message=True
                if( device.low_thresh == form_low_thresh and
                    device.high_thresh == form_high_thresh and
                    device.report_freq == form.cleaned_data['report_freq'] and
                    device.alert_freq == form.cleaned_data['alert_freq'] ):
                        send_message=False
                
                #Write changes to db
                form.save()
                device.low_thresh = form_low_thresh
                device.high_thresh = form_high_thresh
                device.save()
                
                #Only send an SMS to the device if the user changed something
                #that the device needs to know about
                if( send_message ):
                    #prepare the config string to send to device
                    config_string='@CFG SYS,1,%(low)d,%(high)d,%(rpt_freq)d,%(alt_freq)d,0!' % {
                        'low': device.low_thresh,
                        'high': device.high_thresh,
                        'rpt_freq': device.report_freq,
                        'alt_freq': device.alert_freq
                    }
                
                    #Set the device as unconfigured in our system 
                    #so when we see the configured flag go green we know
                    #it received the config from us
                    device.is_configured=False
                    device.save()
            
                    #Send the config message out to the device via a call to the ajax app
                    thread = Thread(target=_send_message,args=(req, pk, config_string))
                    thread.start()
                    
                    #If we changed the device, let the user know
                    return message(req,
                        "SmartConnect IMEI:  %s successfully edited, new config sent to device" % (device.alias),
                        link="/smartconnect")
                    
                #Otherwise tell the user everything's ok but we didn't need to send a CFG message
                return message(req,
                    "SmartConnect IMEI:  %s successfully edited." % (device.alias),
                    link="/smartconnect")
                
            #oops, user has errors in form input.  Ask them to correct and resubmit.
            else:
                return render_to_response(req,'smartconnect/device_edit.html', {
                    'form':         form,
                    'tempform':     tempform,
                    'device':       device,
                })
        
        #Must have clicked cancel.  Back to index
        else:        
            return index(req)
        
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)

@login_required
def message_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    
    def get(req):
        form = MessageForm()
        
        return render_to_response(req,'smartconnect/device_message.html', {
            'form':     form,
            'device':   device,
        })
    
    def post(req):
        form = MessageForm(req.POST)
        
        #Make sure they clicked submit
        if req.POST.get("submit", ""):
            #If it is, transmit the message
            if form.is_valid():
                modified_message="@MSG %s!" % form.cleaned_data['text']
                print("DEBUG trnamitting message: %s" % modified_message)

                #Send the manual message out to the device via a call to the ajax app
                thread = Thread(target=_send_message,args=(req, pk, modified_message))
                thread.start()
            
                return message(req,
                    "SmartConnect IMEI:  message sent",
                    link="/smartconnect")
                    
            #If form has errors, ask user to fix
            else:
                return render_to_response(req,'smartconnect/device_message.html', {
                    'form':         form,
                    'device':       device,
                })
                
        #Must have clicked cancel.  Back to index
        else:
            return index(req)

    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)


def _send_message(req, pk, text):
    # also send the message, by hitting the ajax url of the messaging app
    data = {"uid":  pk,
            "text": text
            }
    encoded = urllib.urlencode(data)
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    conn = httplib.HTTPConnection(req.META["HTTP_HOST"])
    conn.request("POST", "/ajax/messaging/send_message", encoded, headers)
    response = conn.getresponse()

def login(req):
    template_name="smartconnect/login.html"
    template_base=settings.BASE_TEMPLATE
    req.base_template=template_base
    return django_login(req, **{"template_name" : template_name})
    
def logout(req):
    template_name="smartconnect/loggedout.html"
    template_base=settings.BASE_TEMPLATE
    req.base_template=template_base
    return django_logout(req, **{"template_name" : template_name})



#Code for watchers begins here.  Borrowed heavily from reporters and groups
#but we tag our watchers with role = watcher so we can distinguish them from
#other reporter objects

def watcher_list(req):
    return render_to_response(req,
        "smartconnect/watchers.html", {
        "watchers": paginated(req, Reporter.objects.filter(role__name__exact='Watcher'), prefix="rep"),
        "groups":    paginated(req, ReporterGroup.objects.flatten(), prefix="grp"),
    })


def check_reporter_form(req):
    
    # verify that all non-blank
    # fields were provided
    missing = [
        field.verbose_name
        for field in Reporter._meta.fields
        if req.POST.get(field.name, "") == ""
           and field.blank == False]
    
    # TODO: add other validation checks,
    # or integrate proper django forms
    return {
        "missing": missing }


def update_reporter(req, rep):
    
    # as default, we will delete all of the connections
    # and groups from this reporter. the loops will drop
    # objects that we SHOULD NOT DELETE from these lists
    del_conns = list(rep.connections.values_list("pk", flat=True))
    del_grps = list(rep.groups.values_list("pk", flat=True))


    # iterate each of the connection widgets from the form,
    # to make sure each of them are linked to the reporter
    connections = field_bundles(req.POST, "conn-backend", "conn-identity")
    for be_id, identity in connections:
        
        # skip this pair if either are missing
        if not be_id or not identity:
            continue
        
        # create the new connection - this could still
        # raise a DoesNotExist (if the be_id is invalid),
        # or an IntegrityError or ValidationError (if the
        # identity or report is invalid)
        conn, created = PersistantConnection.objects.get_or_create(
            backend=PersistantBackend.objects.get(pk=be_id),
            identity=identity)
        
        # update the reporter separately, in case the connection
        # exists, and is already linked to another reporter
        conn.reporter = rep
        conn.save()
        
        # if this conn was already
        # linked, don't delete it!
        if conn.pk in del_conns:
            del_conns.remove(conn.pk)


    # likewise for the group objects
    groups = field_bundles(req.POST, "group")   
    for grp_id, in groups:
        
        # skip this group if it's empty
        # (an empty widget is displayed as
        # default, which may be ignored here)
        if not grp_id:
            continue
        
        # link this group to the reporter
        grp = ReporterGroup.objects.get(pk=grp_id)
        rep.groups.add(grp)
        
        # if this group was already
        # linked, don't delete it!
        if grp.pk in del_grps:
            del_grps.remove(grp.pk)
    
    #Must unlink all SmartConnectDevices and the
    #Global prefs prior to deleting, otherwise
    #the SQL CASCADE DELETE will wipe them
    to_delete = rep.groups.filter(pk__in=del_grps)
    for del_grp in to_delete:
        del_grp.smartconnectpreferences_set.clear()
        del_grp.smartconnectclient_set.clear()
        
    # delete all of the connections and groups 
    # which were NOT in the form we just received
    rep.connections.filter(pk__in=del_conns).delete()
    rep.groups.filter(pk__in=del_grps).delete()


@require_http_methods(["GET", "POST"])
def add_watcher(req):
    def get(req):
        
        # maybe pre-populate the "connections" field
        # with a connection object to convert into a
        # reporter, if provided in the query string
        connections = []
        if "connection" in req.GET:
            connections.append(
                get_object_or_404(
                    PersistantConnection,
                    pk=req.GET["connection"]))
        
        return render_to_response(req,
            "smartconnect/watcher.html", {
                
                # There are lots of reporters...we only want the watchers
                "watchers": paginated(req, Reporter.objects.filter(role__name__exact='Watcher'), prefix="rep"),
                
                # maybe pre-populate connections
                "connections": connections,
                
                # list all groups + backends in the edit form
                "all_groups": ReporterGroup.objects.flatten(),
                "all_backends": PersistantBackend.objects.all() })

    @transaction.commit_manually
    def post(req):
        
        # check the form for errors
        errors = check_reporter_form(req)
        
        # if any fields were missing, abort. this is
        # the only server-side check we're doing, for
        # now, since we're not using django forms here
        if errors["missing"]:
            transaction.rollback()
            return message(req,
                "Missing Field(s): %s" %
                    ", ".join(missing),
                link="/smartconnect/watchers/add")
        
        try:
            # create the reporter object from the form
            rep = insert_via_querydict(Reporter, req.POST)
            
            # Added so we can keep our watchers separate from our 
            # Devices
            role, created = Role.objects.get_or_create(name='Watcher')
            rep.role=role
            
            rep.save()
            
            
            # every was created, so really
            # save the changes to the db
            update_reporter(req, rep)
            transaction.commit()

            # full-page notification
            return message(req,
                "Watcher %d added" % (rep.pk),
                link="/smartconnect/watchers")
        
        except Exception, err:
            transaction.rollback()
            raise
    
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)


@require_http_methods(["GET", "POST"])  
def edit_watcher(req, pk):
    rep = get_object_or_404(Reporter, pk=pk)
    
    def get(req):
        return render_to_response(req,
            "smartconnect/watcher.html", {
                
                # display paginated watchers in the left panel
                "watchers": paginated(req, Reporter.objects.filter(role__name__exact='Watcher'), prefix="rep"),
                
                # list all groups + backends in the edit form
                "all_groups": ReporterGroup.objects.flatten(),
                "all_backends": PersistantBackend.objects.all(),
                
                # split objects linked to the editing reporter into
                # their own vars, to avoid coding in the template
                "connections": rep.connections.all(),
                "groups":      rep.groups.all(),
                "watcher":    rep })
    
    @transaction.commit_manually
    def post(req):
        
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            pk = rep.pk
            rep.delete()
            
            transaction.commit()
            return message(req,
                "Watcher %d deleted" % (pk),
                link="/smartconnect/watchers")
                
        else:
            # check the form for errors (just
            # missing fields, for the time being)
            errors = check_reporter_form(req)
            
            # if any fields were missing, abort. this is
            # the only server-side check we're doing, for
            # now, since we're not using django forms here
            if errors["missing"]:
                transaction.rollback()
                return message(req,
                    "Missing Field(s): %s" %
                        ", ".join(errors["missing"]),
                    link="/smartconnect/watchers/%s" % (rep.pk))
            
            try:
                # automagically update the fields of the
                # reporter object, from the form
                update_via_querydict(rep, req.POST).save()
                update_reporter(req, rep)
                
                # no exceptions, so no problems
                # commit everything to the db
                transaction.commit()
                
                # full-page notification
                return message(req,
                    "Watcher %d updated" % (rep.pk),
                    link="/smartconnect/watchers")
            
            except Exception, err:
                transaction.rollback()
                raise
        
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)


@require_http_methods(["GET", "POST"])
def add_group(req):
    if req.method == "GET":
        return render_to_response(req,
            "smartconnect/watcher_group.html", {
                "all_groups": ReporterGroup.objects.flatten(),
                "groups": paginated(req, ReporterGroup.objects.flatten()) })
        
    elif req.method == "POST":
        
        # create a new group using the flat fields,
        # then resolve and update the parent group
        # TODO: resolve foreign keys in i_via_q
        grp = insert_via_querydict(ReporterGroup, req.POST)
        parent_id = req.POST.get("parent_id", "")
        if parent_id:
            grp.parent = get_object_or_404(
                ReporterGroup, pk=parent_id)
        
        grp.save()
        
        return message(req,
            "Watcher Group %d added" % (grp.pk),
            link="/smartconnect/watchers")


@require_http_methods(["GET", "POST"])
def edit_group(req, pk):
    grp = get_object_or_404(ReporterGroup, pk=pk)
    
    if req.method == "GET":
        
        # fetch all groups, to be displayed
        # flat in the "parent group" field
        all_groups = ReporterGroup.objects.flatten()
        
        # iterate the groups, to mark one of them
        # as selected (the editing group's parent)
        for this_group in all_groups:
            if grp.parent == this_group:
                this_group.selected = True
        
        return render_to_response(req,
            "smartconnect/watcher_group.html", {
                "groups": paginated(req, ReporterGroup.objects.flatten()),
                "all_groups": all_groups,
                "group": grp })
    
    elif req.method == "POST":
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            pk = grp.pk
            
            #Must unlink global prefs and smartconnect devices first
            #if we don't do this, Django will do a SQL DELETE CASCADE
            #and wipe everything.
            grp.smartconnectpreferences_set.clear()
            grp.smartconnectclient_set.clear()
            grp.delete()
            
            
            return message(req,
                "Group %d deleted" % (pk),
                link="/smartconnect/watchers")

        # otherwise, update the flat fields of the group
        # object, then resolve and update the parent group
        # TODO: resolve foreign keys in u_via_q
        else:
            update_via_querydict(grp, req.POST)
            parent_id = req.POST.get("parent_id", "")
            if parent_id:
                grp.parent = get_object_or_404(
                    ReporterGroup, pk=parent_id)
            
            # if no parent_id was passed, we can assume
            # that the field was cleared, and remove it
            else: grp.parent = None
            grp.save()
            
            return message(req,
                "Group %d saved" % (grp.pk),
                link="/smartconnect/watchers")



#Begin preference editing code.  Here we let the
#user set global prefs like default device configuration

def get_preferences():
    #Note that there are some hardcoded defaults here, just
    #until the user manually sets their defaults
    prefs, created = SmartConnectPreferences.objects.get_or_create(
        name='GlobalPrefs', 
        defaults={
            'name': 'GlobalPrefs',
            'default_low_thresh': 300,
            'default_high_thresh': 330,
            'default_alert_freq': 5,
            'default_report_freq': 30,
        })
    
    return prefs


@login_required
def edit_preferences(req):

    prefs = get_preferences()

    def get(req):
        form = SmartConnectPreferencesForm(instance=prefs)
        tempform = SmartConnectTempForm(initial={
            'low_thresh_c': to_celcius(prefs.default_low_thresh), 
            'high_thresh_c': to_celcius(prefs.default_high_thresh)})
        
  
        return render_to_response(req,'smartconnect/preferences.html', {
            'form':     form,
            'tempform': tempform,
            "prefs":    prefs,
        })
        
    def post(req):
        form = SmartConnectPreferencesForm(req.POST, instance=prefs)
        tempform = SmartConnectTempForm(req.POST)
        
        #Make sure they clicked submit
        if req.POST.get("submit", ""):
            if ( form.is_valid() and tempform.is_valid() ):

                form_low_thresh = to_kelvin(tempform.cleaned_data['low_thresh_c'])
                form_high_thresh = to_kelvin(tempform.cleaned_data['high_thresh_c'])

                form.save()
                
                #get the user's celcius input and save to
                #prefs as Kelvin.
                prefs.default_low_thresh = form_low_thresh
                prefs.default_high_thresh = form_high_thresh
                prefs.save()
                
                return message(req,
                    "SmartConnect:  Preferences successfully edited",
                    link="/smartconnect")
            
            #oops, they must have errors in form input    
            else:
                return render_to_response(req,'smartconnect/preferences.html', {
                    'form':         form,
                    'tempform':     tempform,
                })
        
        #Must have clicked cancel.  Back to index
        else:        
            return index(req)
        
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)
