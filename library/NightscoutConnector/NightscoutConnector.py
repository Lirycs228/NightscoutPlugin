import requests
from datetime import datetime, timedelta, timezone
from loguru import logger as log

class NightscoutConnector(Object):
    def __init__(self):
        super().__init__()

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

    def get_last_N_mins(self, url="http://localhost", token="123", N=30):
        if not url == None and not token == None:
            time_from = datetime.now(timezone.utc) - timedelta(minutes=N)
            time_until = datetime.now(timezone.utc)
            entries = self._fetch_after_datetime(url, token, time_from, time_until)
            if not entries == None:
                if len(entries) > 0:
                    return entries
                else:
                    #log.debug("Entries list: " + str(self.entries))
                    return None
            else:
                return None


    def _fetch_after_datetime(self, url, token, datetime_from, datetime_until):
        timestring_from = datetime_from.strftime('%Y-%m-%dT%H:%M:%SZ')
        timestring_until = datetime_until.strftime('%Y-%m-%dT%H:%M:%SZ')
        #log.info("Getting data from time: " + str(timestring))
        try:
            entries = requests.get(
                str(url) + "/api/v1/entries/sgv.json",
                params={"find[dateString][$gte]": timestring_from,
                        "find[dateString][$lte]": timestring_until,
                        "token": token}
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
