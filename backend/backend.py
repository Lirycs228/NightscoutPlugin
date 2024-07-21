from streamcontroller_plugin_tools import BackendBase
import requests
from datetime import datetime, timedelta

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
            connection_response = requests.get(
                str(self.url) + "/api/v1/status",
                params={"token": self.token}
            )
            return "OK" in str(connection_response)
        else:
            return False

    def get_view(self):
        if not self.entries == None:
            return self.entries[0]["sgv"]
        else:
            return -1

    def _update_view(self):
        if not self.url == None and not self.token == None:
            self._fetch_data()


    def _fetch_data(self):
        time = datetime.now() - timedelta(minutes=30)
        timestring = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.entries = requests.get(
            str(self.url) + "/api/v1/entries/sgv.json",
            params={"find[dateString][$gte]": timestring,
                    "token": self.token}
        ).json()


backend = Backend()
