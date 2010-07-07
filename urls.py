#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import os
from django.conf.urls.defaults import *
import smartconnect.views as views

urlpatterns = patterns('',
    url(r'^smartconnect$',             views.index),
    url(r'^smartconnect/(?P<pk>\d+)$', views.display_device),
    url(r'^smartconnect/delete/(?P<pk>\d+)$', views.delete_device),
    url(r'^smartconnect/edit/(?P<pk>\d+)$', views.edit_device),
)
