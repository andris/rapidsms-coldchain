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
from reporters.utils import *

def index(req):
    return render_to_response(req,
        "smartconnect/index.html", {
        "smartconnectclients": paginated(req, SmartConnectClient.objects.all(), prefix="sc")
    })



@require_http_methods(["GET", "POST"])  
def edit_device(req, pk):
    rep = get_object_or_404(SmartConnectClient, pk=pk)
    
    def get(req):
        return render_to_response(req,
            "smartconnect/device.html", {
                
                # display paginated reporters in the left panel
                "reporters": paginated(req, SmartConnectClient.objects.all()),
                "reporter":    rep })
    
    @transaction.commit_manually
    def post(req):
        
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            pk = rep.pk
            rep.delete()
            
            transaction.commit()
            return message(req,
                "SmartConnect Device %d deleted" % (pk),
                link="/smartconnect")
                
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
                    link="/reporters/%s" % (rep.pk))
            
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
                    "Reporter %d updated" % (rep.pk),
                    link="/reporters")
            
            except Exception, err:
                transaction.rollback()
                raise
        
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)
