# Import StreamController modules
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import actions
from .actions.NightscoutAction.Nightscout import Nightscout

import os

class PluginTemplate(PluginBase):
    def __init__(self):
        super().__init__()

        ## Launch backend
        backend_path = os.path.join(self.PATH, "backend", "backend.py") 
        self.launch_backend(backend_path=backend_path, open_in_terminal=True) 

        ## Register actions
        self.nightscout_action_holder = ActionHolder(
            plugin_base = self,
            action_base = Nightscout,
            action_id = "dev_lirycs_NightscoutViewer::Nightscout", # Change this to your own plugin id
            action_name = "Nightscout View",
        )
        self.add_action_holder(self.nightscout_action_holder)


        # Register plugin
        self.register(
            plugin_name = "Nightscout Viewer",
            github_repo = "https://github.com/Lirycs228/NightscoutPlugin",
            plugin_version = "0.0.1",
            app_version = "1.0.0-alpha"
        )