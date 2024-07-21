# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
from loguru import logger as log 


# Import gtk
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw 


class Nightscout(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_label = Gtk.Label(label="No Connection", css_classes=["bold", "red"])
    
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
                url=self.plugin_base.get_settings().get("nightscout_url", "localhost"),
                token=self.plugin_base.get_settings().get("nightscout_token", "token")
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
        self.plugin_base._update_view()
    
    def on_tick(self):
        if self.plugin_base.backend is not None:
            self.set_center_label(str(self.plugin_base.backend.get_view()))
    
    def get_config_rows(self) -> list:
        self.nightscout_url = Adw.EntryRow()
        self.nightscout_url.set_title("URL of the Nightscout Instance")

        self.nightscout_token = Adw.PasswordEntryRow()
        self.nightscout_token.set_title("Access Token with 'readable' Role")

        self.load_config_values()

        self.nightscout_url.connect("changed", self.on_url_value_changed)
        self.nightscout_token.connect("changed", self.on_token_value_changed)

        return [self.nightscout_url, self.nightscout_token] #

    def load_config_values(self):
        settings = self.get_settings()
        self.nightscout_url.set_text(settings.get("nightscout_url", "http://localhost"))
        self.nightscout_token.set_text(settings.get("nightscout_token", "token"))

    def on_url_value_changed(self, nightscout_url):
        settings = self.get_settings()
        settings["nightscout_url"] = str(nightscout_url.get_text())
        self.set_settings(settings)
        self.try_connection()

    def on_token_value_changed(self, nightscout_token):
        settings = self.get_settings()
        settings["nightscout_token"] = str(nightscout_token.get_text())
        self.set_settings(settings)
        self.try_connection()






