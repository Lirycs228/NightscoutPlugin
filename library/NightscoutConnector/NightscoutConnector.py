import requests
from datetime import datetime, timedelta, timezone
from loguru import logger as log
from PIL import Image, ImageDraw
import numpy as np
from dateutil import parser

class NightscoutConnector:
    def __init__(self):
        super().__init__()
    
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
        
    def extract_treatments(self, treatments, time_from):
        data = np.zeros((200, 2))

        for treat in treatments:
            entry_time = parser.parse(treat["created_at"])
            minutes_since_beginn = divmod((entry_time - time_from).total_seconds(), 60)[0]
            data[int(minutes_since_beginn)][0] = treat["carbs"]
            data[int(minutes_since_beginn)][1] = treat["insulin"]

        return data
    
    def add_treatments(self, graph, values, top_pad=100, height_range=300):
        draw = ImageDraw.Draw(graph)

        left_pad = 50
        point_spacing = 2# assumption: 200 minutes in 400 pixels

        values[:, 0] = values[:, 0]/5 # normalize to KE units
        values[:, 0] = np.clip(values[:, 0], 0, 30)
        values[:, 1] = np.clip(values[:, 1], 0, 30)

        for count, value in enumerate(values):
            if value[0] != None and value[0] > 0:
                # carbs
                draw.line((
                    left_pad+(point_spacing*count), 
                    top_pad+height_range, 
                    left_pad+(point_spacing*count), 
                    top_pad+height_range-int(value[0]*3*(height_range/300)+10)
                    ), fill=(102, 178, 255), width=10)
            if value[1] != None and value[1] > 0:
                # insulin
                draw.line((
                    left_pad+(point_spacing*count), 
                    top_pad, 
                    left_pad+(point_spacing*count), 
                    top_pad+int(value[1]*3*(height_range/300)+10)
                    ), fill=(102, 178, 255), width=10)
                    
        return graph
        
    def extract_values(self, entries, time_from):
        data = np.zeros(200)

        for entry in entries:
            if entry["type"] == "sgv":
                entry_time = parser.parse(entry["dateString"])
                minutes_since_beginn = divmod((entry_time - time_from).total_seconds(), 60)[0]
                data[int(minutes_since_beginn)] = entry["sgv"]

        return data
    
    def build_graph(self, values, top_pad=100, height_range=300):
        canvas = Image.new("RGB", (500, 500), color="black")
        draw = ImageDraw.Draw(canvas)

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

    def has_connection(self, url="http://localhost", token="123"):
        if not url == None and not token == None:
            try:
                connection_response = requests.get(
                    str(url) + "/api/v1/status",
                    params={"token": token}
                ).content
                #log.debug("Connection Response: " + str(connection_response))
            except Exception as e:
                return False
            return "OK" in str(connection_response)
        else:
            return False
        
    def get_last_entry(self, url="http://localhost", token="123"):
        if not url == None and not token == None:
            entries = self._fetch_last_N_entries(url, token)
            if not entries == None:
                if len(entries) > 0:
                    return entries[0]
                else:
                    #log.debug("Entries list: " + str(self.entries))
                    return None
            else:
                return None

    def get_last_N_mins_values(self, url="http://localhost", token="123", N=200):
        if not url == None and not token == None:
            time_from = datetime.now(timezone.utc) - timedelta(minutes=N)
            time_until = datetime.now(timezone.utc)
            entries = self._fetch_after_datetime_values(url, token, time_from, time_until)
            if not entries == None:
                if len(entries) > 0:
                    return entries
                else:
                    #log.debug("Entries list: " + str(self.entries))
                    return None
            else:
                return None
    
    def get_last_N_mins_treatments(self, url="http://localhost", token="123", N=200):
        if not url == None and not token == None:
            time_from = datetime.now(timezone.utc) - timedelta(minutes=N)
            time_until = datetime.now(timezone.utc)
            entries = self._fetch_after_datetime_treatments(url, token, time_from, time_until)
            if not entries == None:
                if len(entries) > 0:
                    return entries
                else:
                    #log.debug("Entries list: " + str(self.entries))
                    return None
            else:
                return None


    def _fetch_after_datetime_values(self, url, token, datetime_from, datetime_until):
        timestring_from = datetime_from.strftime('%Y-%m-%dT%H:%M:%SZ')
        timestring_until = datetime_until.strftime('%Y-%m-%dT%H:%M:%SZ')
        #log.info("Getting data from time: " + str(timestring))
        try:
            entries = requests.get(
                str(url) + "/api/v1/entries/sgv.json",
                params={"find[dateString][$gte]": timestring_from,
                        "find[dateString][$lte]": timestring_until,
                        "count": 1000,
                        "token": token,}
            ).json()
            return entries
        except Exception as e:
            return None
    
    def _fetch_after_datetime_treatments(self, url, token, datetime_from, datetime_until):
        timestring_from = datetime_from.strftime('%Y-%m-%dT%H:%M:%SZ')
        timestring_until = datetime_until.strftime('%Y-%m-%dT%H:%M:%SZ')
        #log.info("Getting data from time: " + str(timestring))
        try:
            entries = requests.get(
                str(url) + "/api/v1/treatments.json",
                params={"find[created_at][$gte]": timestring_from,
                        "find[created_at][$lte]": timestring_until,
                        "count": 1000,
                        "token": token,}
            ).json()
            return entries
        except Exception as e:
            return None
    
    def _fetch_last_N_entries(self, url, token, N=1):
        try:
            entries = requests.get(
                str(url) + "/api/v1/entries/sgv.json",
                params={"count": N,
                        "token": token}
            ).json()
            return entries
        except Exception as e:
            return None
