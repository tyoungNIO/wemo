from pywemo.ouimeaux_device.switch import Switch
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.properties import VersionProperty, Property
from .wemo_base import WeMoBase


class WeMoSwitch(WeMoBase, EnrichSignals):

    version = VersionProperty("0.1.0")
    switch_state = Property(title='Switch state', default='{{ True }}')

    def execute_wemo_command(self, signal):
        self.device.set_state(self.switch_state(signal))
        return {
            "state": self.device.get_state(),
        }

    def is_valid_device(self, device):
        return isinstance(device, Switch) and super().is_valid_device(device)
