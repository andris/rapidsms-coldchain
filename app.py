import rapidsms
from rapidsms.parsers.keyworder import *
from rapidsms.utils import *

import re
from models import *
from datetime import datetime
import os

class App (rapidsms.app.App):

    #Using the keyworder parser
    kw = Keyworder()

    #SmartConnect devices start messages with @ and end with !
    sc_pat = re.compile(r'@(.*)!', re.IGNORECASE)

    #compiled regex for reports
    rpt_pat = re.compile(r'([A-Z]{3}),(\d+)', re.IGNORECASE)
    
    #compiled regex for alerts
    alt_pat = re.compile(r'([A-Z]{3}),(0|1),(\d+),(\d+),(\d+)', re.IGNORECASE)

    #compiled regex for config strings
    cfg_pat = re.compile(r'[A-Z]{3},(0|1),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', re.IGNORECASE)
    
    def start (self):
        """Configure your app in the start phase."""
        pass

    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
        pass

    def handle (self, message):
        self.handled = False
        try:
            #Search for the @xxxx! SmartConnect syntax
            sc_text = self.sc_pat.match(message.text)
            if(sc_text):
                #If we matched @xxxx! strip off @ and !
                sc_command = sc_text.group(1)
                if hasattr(self, "kw"):
                    self.debug("HANDLE")
                    
                    # attempt to match tokens in the SC command
                    # using the keyworder parser
                    results = self.kw.match(self, sc_command)
                    if results:
                        func, captures = results
                        # if a function was returned, then a this message
                        # matches the handler _func_. call it, and short-
                        # circuit further handler calls
                        func(self, message, *captures)
                        return self.handled
                    else:
                        self.debug("No SmartConnect keyword in %s" % message.text)
                else:
                    self.debug("App does not instantiate Keyworder as 'kw'")
            else:
                self.debug("No SmartConnect command in %s" % message.text)
                
        except Exception, e:
            self.log_last_exception()

    def cleanup (self, message):
        """Perform any clean up after all handlers have run in the
           cleanup phase."""
        pass

    def outgoing (self, message):
        """Handle outgoing message notifications."""
        pass

    def stop (self):
        """Perform global app cleanup when the application is stopped."""
        pass

    kw.prefix = "CFG"
    @kw("(whatever)")
    def receive_config(self, message, contents):
        response = self.cfg_pat.match(contents)
        if response:
            report_is_configured = bool(int(response.group(1))==1)
            report_low_thresh = int(response.group(2))
            report_high_thresh = int(response.group(3))
            report_rpt_freq = int(response.group(4))
            report_alt_freq = int(response.group(5))
            report_timeout = int(response.group(6))
            report_imei = int(response.group(7))
            report_fw = response.group(8)

            self.debug("CFG string recieved,"
                + " is_configured " + str(report_is_configured)
                + " low thresh " + str(report_low_thresh)
                + " high thresh " + str(report_high_thresh)
                + " rpt freq " + str(report_rpt_freq)
                + " alt freq " + str(report_alt_freq)
                + " timeout " + str(report_timeout)
                + " IMEI " + str(report_imei)
                + " FW Ver " + report_fw)
                
            
            #Check if this SmartConnect device exists
            matching_devices=SmartConnectClient.objects.filter(alias=report_imei)

            if((len(matching_devices)) > 0):
                self.debug("CFG: Received CFG for existing client")
                matched_device=matching_devices[0]
                matched_device.is_configured=report_is_configured
                matched_device.low_thresh=report_low_thresh
                matched_device.high_thresh=report_high_thresh
                matched_device.report_freq=report_rpt_freq
                matched_device.alert_freq=report_alt_freq
                matched_device.timeout=report_timeout
                matched_device.fw_version=report_fw
                matched_device.save()
            
            #We've never seen this IMEI, register the
            #new device    
            else:
                reporter = SmartConnectClient(
                    first_name="SmartConnect",
                    last_name=("IMEI:" + str(report_imei)),
                    alias=report_imei,
                    is_configured=report_is_configured,
                    low_thresh=report_low_thresh,
                    high_thresh=report_high_thresh,
                    report_freq=report_rpt_freq,
                    alert_freq=report_alt_freq,
                    timeout=report_timeout,
                    fw_version=report_fw)
                    
                reporter.save()
                
                #attach our new SmartConnect Device
                #to the persistant connection
                message.persistant_connection.reporter=reporter
                message.persistant_connection.save()
                
                self.debug("Successfully registered new SmartConnect Device")

        else:
            self.debug("NO MATCHES IN CFG STRING")

        self.handled = True

    #Really need to merge processing of ALTs and RPTs
    #logic is almost exactly the same
    kw.prefix = "RPT"
    @kw("(whatever)")
    def receive_report(self, message, contents):
        response = self.rpt_pat.match(contents)
        if response:
            report_type = response.group(1)
            report_value = int(response.group(2))
            report_time = message.date
            report_is_acknowledged = False

            if message.reporter:
                smart_connect_device = SmartConnectClient.objects.get(alias=message.reporter.alias)
            
            else:
                self.debug("RECEIVED REPORT FROM UNREGISTERED DEVICE")
                self.handled = False
                return self.handled

            report = SmartConnectReport(
                reporting_device=smart_connect_device,
                connection=message.persistant_connection,
                type=report_type,
                value=report_value,
                time=report_time,
                is_alert=False,
                is_acknowledged=report_is_acknowledged,
                floor=report_value,
                ceiling=report_value)
                
            report.save()
            self.debug("RPT received--" + str(report))
            
            #Store the most recent values in the device
            #itself.  Would be good to have a table for this
            #to accept arbitrary alert/event types
            smart_connect_device.alert_status = report.is_alert
            if ( report.type == "tmp" ):
                smart_connect_device.current_temp=report.value
                #also, stop alerting since this is a non alert report
                smart_connect_device.is_alert=False
            smart_connect_device.save()
            
        else:
            self.debug("NO MATCHES IN RPT STRING")

        self.handled = True

    kw.prefix = "ALT"
    @kw("(whatever)")
    def receive_alert(self, message, contents):
        response = self.alt_pat.match(contents)
        if response:
            alert_type = response.group(1)
            alert_is_acknowledged = bool(int(response.group(2))==1)
            alert_ceiling = int(response.group(3))
            alert_floor = int(response.group(4))
            alert_value = int(response.group(5))
            alert_time = message.date

            if message.reporter:
                smart_connect_device = SmartConnectClient.objects.get(alias=message.reporter.alias)

            else:
                self.debug("RECEIVED ALERT FROM UNREGISTERED DEVICE")
                self.handled = False
                return self.handled

            report = SmartConnectReport(
                reporting_device=smart_connect_device,
                connection=message.persistant_connection,
                type=alert_type,
                value=alert_value,
                time=alert_time,
                is_alert=True,
                is_acknowledged=alert_is_acknowledged,
                floor=alert_floor,
                ceiling=alert_ceiling)
                
            report.save()
            self.debug("ALT received--" + str(report))
            
            #update the SmartConnect device
            smart_connect_device.alert_status = report.is_alert
            
            if ( report.type == "tmp" ):
                smart_connect_device.current_temp=report.value
            
            smart_connect_device.save()
            
            #if this is an unacknowledged alert, ACK it
            if ( report.is_acknowledged == False ):
                message.respond("@ACK ALT!")

        else:
            self.debug("NO MATCHES IN ALT STRING")
            
        self.handled = True
        
    kw.prefix = "ACK"
    @kw("(whatever)")
    def receive_ack(self, message, contents):
        self.debug("Got ACK with contents %s" % contents)
        self.handled = True

    kw.prefix = "ERR"
    @kw("(whatever)")
    def receive_error(self, message, contents):
        self.debug("Got ERR with contents %s" % contents)
        self.handled = True

    kw.prefix = "VER"
    @kw("(whatever)")
    def receive_version(self, message, contents):
        self.debug("Got VER with contents %s" % contents)
        self.handled = True

    kw.prefix = "MSG"
    @kw("(whatever)")
    def receive_version(self, message, contents):
        self.debug("Got MSG with contents %s" % contents)
        
        if message.reporter:
            device = SmartConnectClient.objects.get(alias=message.reporter.alias)
            device.last_text = contents
            device.save()
            self.handled = True

        else:
            self.debug("RECEIVED MSG FROM UNREGISTERED DEVICE")
            self.handled = False
            
        return self.handled
            
        
        self.handled = True
