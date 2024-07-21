from streamcontroller_plugin_tools import BackendBase
import requests
from datetime import datetime, timedelta
from loguru import logger as log

class Backend(BackendBase):
    def __init__(self):
        super().__init__()

        self.url = None
        self.token = None
        self.entries = None
    
    def try_connect(self, url=None, token=None):
        if not url == None and not token == None:
            self.url = url
            self.token = token

    def get_connected(self):
        if not self.url == None and not self.token == None:
            try:
                connection_response = requests.get(
                    str(self.url) + "/api/v1/status",
                    params={"token": self.token}
                ).content
                log.debug("Connection Response: " + str(connection_response))
            except Exception as e:
                return False
            return "OK" in str(connection_response)
        else:
            return False

    def get_view(self):
        if not self.entries == None:
            if len(self.entries) > 0:
                return self.entries[0]["sgv"]
            else:
                log.debug("Entries list: " + str(self.entries))
                return -1
        else:
            return -1
        
    def manual_update(self):
        self._update_view()

    def _update_view(self):
        if not self.url == None and not self.token == None:
            self._fetch_data()


    def _fetch_data(self):
        time = datetime.now() - timedelta(minutes=30)
        timestring = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        log.info("Getting data from time: " + str(timestring))
        try:
            self.entries = requests.get(
                str(self.url) + "/api/v1/entries/sgv.json",
                params={"find[dateString][$gte]": timestring,
                        "token": self.token}
            ).json()
        except Exception as e:
            pass


backend = Backend()
