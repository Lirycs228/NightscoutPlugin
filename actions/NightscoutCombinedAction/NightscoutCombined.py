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


class NightscoutCombined(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_label = Gtk.Label(label="No Connection", css_classes=["bold", "red"])
        self.seconds_until_update = 30
        self.seconds_since_last_update = self.seconds_until_update
    
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
    
    def get_color(self, value):
        if value < 65:
            return "red"
        elif value < 80:
            return "yellow"
        elif value < 180:
            return "green"
        elif value < 250:
            return "yellow"
        else:
            return "red"
        
    def extract_values(self, entries, time_from, time_until):
        minutes = divmod((time_until - time_from).total_seconds(), 60)[0]

        data = np.zeros(200)

        for entry in entries:
            if entry["type"] == "sgv":
                entry_time = parser.parse(entry["dateString"])
                minutes_since_beginn = divmod((entry_time - time_from).total_seconds(), 60)[0]
                data[int(minutes_since_beginn)] = entry["sgv"]

        return data
    
    def build_graph(self, values):
        canvas = Image.new("RGB", (500, 500), color="black")
        draw = ImageDraw.Draw(canvas)

        top_pad = 160
        height_range = 200 # 50 bottom, 150 top
        left_pad = 50
        point_spacing = 2# assumption: 200 minutes in 400 pixels
        radius = 8

        data = np.clip(values, 0, 300)
        data = data * (height_range/300)

        draw.line((left_pad, top_pad, 500-left_pad, top_pad), fill=(150, 150, 150), width=3)
        draw.line((left_pad, top_pad+height_range, 500-left_pad, top_pad+height_range), fill=(150, 150, 150), width=3)
        draw.line((left_pad, top_pad+height_range - 100*(height_range/300), 500-left_pad, top_pad+height_range - 100*(height_range/300)), fill=(150, 150, 150), width=3)
        
        for count, (value, datum) in enumerate(zip(values, data)):
            if value != None and value != 0:
                position = (   left_pad+(point_spacing*count)-radius, 
                        top_pad+(height_range-int(datum))-radius, 
                        left_pad+(point_spacing*count)+radius, 
                        top_pad+(height_range-int(datum))+radius  )
                draw.ellipse(
                    position, 
                    fill=self.get_color(value))

        return canvas

    def on_tick(self):
        self.seconds_since_last_update += 1

        if(self.seconds_since_last_update > self.seconds_until_update):
            self.seconds_since_last_update = 0
            entries = self.plugin_base.NightscoutConnector.get_last_N_mins(
                self.get_settings().get("nightscout_url"),
                self.get_settings().get("nightscout_token"),
                N=200
            )
            if entries != None:
                if len(entries) > 0:
                    if entries[0]["type"] == "sgv":
                        self.set_top_label(str(entries[0]["sgv"]) + " " + self.direction_to_arrow(entries[0]["direction"]), font_size=18)
                        entry_time = parser.parse(entries[0]["dateString"])

                        current_time = datetime.now(timezone.utc)
                        current_time = current_time.replace(microsecond=0)
                        time_delta_minutes = divmod((current_time - entry_time).total_seconds(), 60)[0]
                        self.set_bottom_label(str(int(time_delta_minutes)) + " m", font_size=16)

                        time_from = time_from = datetime.now(timezone.utc) - timedelta(minutes=200)
                        graph = self.build_graph(self.extract_values(entries, time_from, current_time))
                        self.set_media(image=graph)
                else:
                    self.set_top_label("no data", font_size=18)
                    self.set_bottom_label("")
                    self.set_media(image=Image.new("RGB", (500, 500), color="black"))
            else:
                self.set_top_label("no data", font_size=18)
                self.set_bottom_label("")
                self.set_media(image=Image.new("RGB", (500, 500), color="black"))
    
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






