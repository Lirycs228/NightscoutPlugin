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
    
    def extract_treatments(self, treatments, time_from, time_until):
        minutes = divmod((time_until - time_from).total_seconds(), 60)[0]

        data = np.zeros((200, 2))

        for treat in treatments:
            entry_time = parser.parse(treat["created_at"])
            minutes_since_beginn = divmod((entry_time - time_from).total_seconds(), 60)[0]
            data[int(minutes_since_beginn)][0] = treat["carbs"]
            data[int(minutes_since_beginn)][1] = treat["insulin"]

        return data
    
    def add_treatments(self, graph, values):
        draw = ImageDraw.Draw(graph)

        top_pad = 100
        height_range = 300 # 50 bottom, 150 top
        left_pad = 50
        point_spacing = 2# assumption: 200 minutes in 400 pixels
        radius = 8

        values[:, 0] = np.clip(values[:, 0], 0, 100)
        values[:, 1] = np.clip(values[:, 1], 0, 100)

        for count, value in enumerate(values):
            if value != None and value != 0:
                if value[0] > 0 and value[0] != None:
                    # carbs
                    draw.line((
                        left_pad+(point_spacing*count), 
                        top_pad, 
                        left_pad+(point_spacing*count), 
                        top_pad+value[0]
                        ), fill=(0, 0, 255), width=5)
                if value[1] > 0 and value[1] != None:
                    # insulin
                    draw.line((
                        left_pad+(point_spacing*count), 
                        top_pad+height_range, 
                        left_pad+(point_spacing*count), 
                        top_pad+height_range-value[1]
                        ), fill=(0, 0, 255), width=5)

        return graph
    
    def build_graph(self, values):
        canvas = Image.new("RGB", (500, 500), color="black")
        draw = ImageDraw.Draw(canvas)

        top_pad = 100
        height_range = 300 # 50 bottom, 150 top
        left_pad = 50
        point_spacing = 2# assumption: 200 minutes in 400 pixels
        radius = 8

        data = np.clip(values, 0, 300)

        draw.line((left_pad, top_pad, 500-left_pad, top_pad), fill=(150, 150, 150), width=3)
        draw.line((left_pad, top_pad+height_range, 500-left_pad, top_pad+height_range), fill=(150, 150, 150), width=3)
        draw.line((left_pad, top_pad+height_range-100, 500-left_pad, top_pad+height_range-100), fill=(0, 150, 0), width=3)
        #draw.line((500-left_pad, top_pad, 500-left_pad, top_pad+height_range), fill=(150, 150, 150), width=3)
        
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
                    graph = self.build_graph(self.extract_values(entries, time_from, current_time))
                    self.set_media(image=graph)

                    # TREATMENTS
                    treatments = self.plugin_base.NightscoutConnector.get_last_N_mins_treatments(
                        self.get_settings().get("nightscout_url"),
                        self.get_settings().get("nightscout_token"),
                        N=200
                    )
                    if treatments != None:
                        if len(treatments) > 0:
                            graph = self.add_treatments(graph, self.extract_treatments(treatments, time_from, current_time))
                else:
                    self.set_media(image=Image.new("RGB", (500, 500), color="black"))
            else:
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






