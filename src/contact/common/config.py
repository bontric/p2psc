import json
import logging
import os.path
import random
import string

# this only workson NIX.. fix it
DEFAULT_PATH = os.path.expanduser('~') + "/.osccontact.conf"

class ContactConfig():
    def __init__(self, path=None):
        self.__configDict = None
        if path is None:
            self.__loadConfig(DEFAULT_PATH)
        else:
            self.__loadConfig(path)

    def __makeDefault(self):
        self.__configDict = {
            "name": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)),
            "zeroconf": True,
            "timeout": 20,
            "update_interval": 3,
            "local_ip": None,
            "clients": {
                "enabled" : True,
                "port": 3760,
            },
            "local_nodes": {
                "enabled" : True,
                "port": 3761,
            },
            "remote_host": {
                "enabled" : False,
                "ip": None,
                "port": 3762,
            },
            "remote_nodes": {
                "sessions": []
            }
        }
    
    def __loadConfig(self, path):
        if os.path.exists(path):
            with open(path, 'r') as jsonFile:
                js = jsonFile.read()
            self.__configDict = json.loads(js)
        else:
            self.__makeDefault()
            self.save(path)
            logging.info(f"Created default config file at {path}")

    def __getitem__(self, key):
        return self.__configDict[key]
    
    def __setitem__(self, key, value):
        self.__configDict[key] = value


    def get(self):
        return self.__configDict

    def save(self, path):
        js = json.dumps(self.__configDict, indent=2)
        with open(path, 'w') as jsonFile:
           jsonFile.write(js)

    def __str__(self):
        return json.dumps(self.__configDict, indent=2)
