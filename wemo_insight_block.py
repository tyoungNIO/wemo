<<<<<<< HEAD
from pywemo import discover_devices
=======
>>>>>>> origin/switch_support
from pywemo.ouimeaux_device.insight import Insight
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.properties import VersionProperty
from .wemo_base import WeMoBase


class WeMoInsight(WeMoBase, EnrichSignals):

    version = VersionProperty("0.1.1")

    def execute_wemo_command(self, signal):
        if not self._updating:
            self.logger.debug('Reading values from {} {}...'.format(
                self.device.name, self.device.mac))
            self._updating = True
            try:
                self.device.update_insight_params()
                self._updating = False
            except:
                # raises when update_insight_params has given up retrying
                self.logger.error(
                    'Unable to connect to WeMo, dropping signal {}'.format(
                        signal))
                self.device = None
                self._updating = False
                return
        else:
            # drop new signals while retrying
            self.logger.error(
                'Another thread is waiting for param update, '
                'dropping signal {}'.format(signal))
            return

        return self.device.insight_params

    def is_valid_device(self, device):
        return isinstance(device, Insight) and super().is_valid_device(device)
