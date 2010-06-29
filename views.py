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

#If using matplotlib for graphing stuff
import random
import time
import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter

#if using cairoplot for graphing stuff
import os, tempfile, cairo
import cairoplot

def index(req):
    return render_to_response(req,
        "smartconnect/index.html", {
        "smartconnectclients": paginated(req, SmartConnectClient.objects.all(), prefix="sc")
    })



@require_http_methods(["GET", "POST"])  
def edit_device(req, pk):
    device = get_object_or_404(SmartConnectClient, pk=pk)
    
    def get(req):
        return render_to_response(req,
            "smartconnect/device.html", {
                
                # display paginated reporters in the left panel
                "smartconnectdevice":    device })
    
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)



def matplotlib_sample(request):

    fig=Figure()
    ax=fig.add_subplot(111)
    x=[]
    y=[]
    now=datetime.datetime.now()
    delta=datetime.timedelta(days=1)
    for i in range(10):
        x.append(now)
        now+=delta
        y.append(random.randint(0, 1000))
    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    canvas=FigureCanvas(fig)
    response=HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response

def cairoplot_sample(request):
    filename = tempfile.mkstemp(suffix='.png')[1]
    data = [[1,2,3],[4,5,6],[7,8,9]]
    test = cairoplot.HorizontalBarPlot(filename, data, 640, 480)
    test.render()
    test.commit()
    fo = open(filename)
    data = fo.read()
    fo.close()
    os.unlink(filename)
    return HttpResponse(data, mimetype="image/png")

def render_image(drawer, width, height):
    # We render to a temporary file, since Cairo can't stream nicely
    filename = tempfile.mkstemp()[1]
    # We render to a generic Image, being careful not to use colour hinting
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
    font_options = surface.get_font_options()
    font_options.set_antialias(cairo.ANTIALIAS_GRAY)
    context = cairo.Context(surface)
    # Call our drawing function on that context, now.
    drawer(context)
    # Write the PNG data to our tempfile
    surface.write_to_png(filename)
    surface.finish()
    # Now stream that file's content back to the client
    fo = open(filename)
    data = fo.read()
    fo.close()
    os.unlink(filename)
    return HttpResponse(data, mimetype="image/png")

