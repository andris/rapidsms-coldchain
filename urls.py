#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import os
from django.conf.urls.defaults import *
import smartconnect.views as views

urlpatterns = patterns('',
    url(r'^smartconnect$',             views.index),
    url(r'^smartconnect/login',         views.login),
    url(r'^smartconnect/logout',         views.logout),
    url(r'^smartconnect/(?P<pk>\d+)$', views.display_device),
    url(r'^smartconnect/delete/(?P<pk>\d+)$', views.delete_device),
    url(r'^smartconnect/edit/(?P<pk>\d+)$', views.edit_device),
    url(r'^smartconnect/sendmessage/(?P<pk>\d+)$', views.message_device),
    url(r'^smartconnect/watchers$',         views.watcher_list),
    url(r'^smartconnect/watchers/add$',         views.add_watcher,  name="add-watcher"),
    url(r'^smartconnect/watchers/(?P<pk>\d+)$', views.edit_watcher, name="view-watcher"),
    url(r'^smartconnect/watchers/groups/add$',         views.add_group),
    url(r'^smartconnect/watchers/groups/(?P<pk>\d+)$', views.edit_group),
    url(r'^smartconnect/preferences$',         views.edit_preferences),
)
