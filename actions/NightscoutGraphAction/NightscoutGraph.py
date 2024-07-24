# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
from loguru import logger as log 
from datetime import datetime, timedelta, timezone
from dateutil import parser
from PIL import Image, ImageDraw
import numpy as np


# Import gtk
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw 


class NightscoutGraph(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_label = Gtk.Label(label="No Connection", css_classes=["bold", "red"])
        self.seconds_until_update = 30
        self.seconds_since_last_update = self.seconds_until_update

        self.last_graph = None
        self.last_worked = False
        self.last_treatments = None
    
    def update_status_label(self):
        if self.plugin_base.NightscoutConnector.has_connection(
            self.get_settings().get("nightscout_url"),
            self.get_settings().get("nightscout_token")
        ):
            self.status_label.set_label("Connected")
            self.status_label.remove_css_class("red")
            self.status_label.add_css_class("green")
        else:
            self.status_label.set_label("No Connection")
            self.status_label.remove_css_class("green")
            self.status_label.add_css_class("red")
    
    def get_custom_config_area(self):
        self.update_status_label()
        return self.status_label

    def on_ready(self):
        if not self.plugin_base.NightscoutConnector.has_connection(
            self.get_settings().get("nightscout_url"),
            self.get_settings().get("nightscout_token")
        ):
            self.update_status_label()
            self.seconds_since_last_update = 100

    def on_tick(self):
        self.seconds_since_last_update += 1

        if(self.seconds_since_last_update > self.seconds_until_update):
            self.seconds_since_last_update = 0
            entries = self.plugin_base.NightscoutConnector.get_last_N_mins_values(
                self.get_settings().get("nightscout_url"),
                self.get_settings().get("nightscout_token"),
                N=200
            )
            if entries != None:
                if len(entries) > 0:
                    current_time = datetime.now(timezone.utc)
                    current_time = current_time.replace(microsecond=0)
                    time_from = time_from = datetime.now(timezone.utc) - timedelta(minutes=200)
                    values = self.plugin_base.NightscoutConnector.extract_values(entries, time_from)
                    graph = self.plugin_base.NightscoutConnector.build_graph(values)

                    self.last_graph = graph
                    self.last_worked = True

                    if self.last_treatments != None:
                        if len(self.last_treatments) > 0:
                            treatments = self.plugin_base.NightscoutConnector.extract_treatments(self.last_treatments, time_from)
                            graph = self.plugin_base.NightscoutConnector.add_treatments(graph, treatments)
                            self.set_media(image=graph)
                        else:
                            self.set_media(image=graph)
                    else:
                        self.set_media(image=graph)
                else:
                    self.set_media(image=Image.new("RGB", (500, 500), color="black"))
                    self.last_worked = False
            else:
                self.set_media(image=Image.new("RGB", (500, 500), color="black"))
                self.last_worked = False
            
        # TREATMENTS
        if self.last_worked and self.seconds_since_last_update == 10:
            treatments = self.plugin_base.NightscoutConnector.get_last_N_mins_treatments(
                self.get_settings().get("nightscout_url"),
                self.get_settings().get("nightscout_token"),
                N=200
            )
            self.last_treatments = treatments

    def get_config_rows(self) -> list:
        self.nightscout_url = Adw.EntryRow()
        self.nightscout_url.set_title("URL of the Nightscout Instance with http(s)://")

        self.nightscout_token = Adw.PasswordEntryRow()
        self.nightscout_token.set_title("Access Token with 'readable' Role")

        self.load_config_values()

        self.nightscout_url.connect("changed", self.on_url_value_changed)
        self.nightscout_token.connect("changed", self.on_token_value_changed)

        return [self.nightscout_url, self.nightscout_token] #

    def load_config_values(self):
        settings = self.get_settings()

        settings.setdefault("nightscout_url", "http://localhost")
        settings.setdefault("nightscout_token", "")
        self.set_settings(settings)
        settings = self.get_settings()

        self.nightscout_url.set_text(settings.get("nightscout_url"))
        self.nightscout_token.set_text(settings.get("nightscout_token"))

    def on_url_value_changed(self, nightscout_url):
        settings = self.get_settings()
        settings["nightscout_url"] = str(nightscout_url.get_text())
        self.set_settings(settings)
        self.update_status_label()

    def on_token_value_changed(self, nightscout_token):
        settings = self.get_settings()
        settings["nightscout_token"] = str(nightscout_token.get_text())
        self.set_settings(settings)
        self.update_status_label()






