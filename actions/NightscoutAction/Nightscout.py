# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
from loguru import logger as log 
from datetime import datetime, timedelta, timezone
from dateutil import parser


# Import gtk
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw 


class Nightscout(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_label = Gtk.Label(label="No Connection", css_classes=["bold", "red"])
        self.seconds_since_last_update = 0
    
    def update_status_label(self):
        if self.plugin_base.backend.get_connected():
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
    
    def try_connection(self):
        try:
            self.plugin_base.backend.try_connect(
                url=self.plugin_base.get_settings().get("nightscout_url"),
                token=self.plugin_base.get_settings().get("nightscout_token")
            )
            self.update_status_label()
        except Exception as e:
            log.error(e)
            self.show_error()
            self.update_status_label()
            return

    def on_ready(self):
        if self.plugin_base.backend is not None:
            if not self.plugin_base.backend.get_connected():
                self.try_connection()
    
    def on_key_down(self):
        self.plugin_base.backend.manual_update()
    
    def direction_to_arrow(self, direction):
        match direction:
            case "Flat":
                return "\u279E" # right
            case "FortyFiveUp":
                return "\u2B08" # up-right
            case "FortyFiveDown":
                return "\u2B0A" # down-right
            case "SingleUp":
                return "\u2191" # up
            case "DoubleUp":
                return "\u21D1" # doubble-up
            case "SingleDown":
                return "\u2193" # down
            case "DoubleDown":
                return "\u21D3" # doubble-down
    
    def on_tick(self):
        self.seconds_since_last_update += 1

        if(self.seconds_since_last_update > 60):
            self.plugin_base.backend.manual_update()

        if self.plugin_base.backend is not None:
            entries = self.plugin_base.backend.get_view()
            if entries != None and entries != -1:
                self.set_center_label(str(entries[0]["sgv"]) + " " + self.direction_to_arrow(entries[0]["direction"]), font_size=20)
                entry_time = parser.parse(entries[0]["dateString"])
                current_time = datetime.now(timezone.utc)
                current_time = current_time.replace(microsecond=0)
                #log.debug("Times: " + str(current_time) + " , " + str(entry_time))
                time_delta_minutes = divmod((current_time - entry_time).total_seconds(), 60)[0]
                self.set_top_label(str(int(time_delta_minutes)) + " m", font_size=16)
            else:
                self.set_center_label("no data", font_size=18)
                self.set_top_label("")
    
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
        settings = self.plugin_base.get_settings()

        settings.setdefault("nightscout_url", "http://localhost")
        settings.setdefault("nightscout_token", "")
        self.plugin_base.set_settings(settings)
        settings = self.plugin_base.get_settings()

        self.nightscout_url.set_text(settings.get("nightscout_url"))
        self.nightscout_token.set_text(settings.get("nightscout_token"))

    def on_url_value_changed(self, nightscout_url):
        settings = self.plugin_base.get_settings()
        settings["nightscout_url"] = str(nightscout_url.get_text())
        self.plugin_base.set_settings(settings)
        self.try_connection()

    def on_token_value_changed(self, nightscout_token):
        settings = self.plugin_base.get_settings()
        settings["nightscout_token"] = str(nightscout_token.get_text())
        self.plugin_base.set_settings(settings)
        self.try_connection()






