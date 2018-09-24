import pywemo
from nio import Block, Signal
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.properties import VersionProperty
from nio.util.threading import spawn


class WeMoInsight(Block, EnrichSignals):

    version = VersionProperty('0.1.0')

    def __init__(self):
        super().__init__()
        self.device = None
        self._thread = None

    def configure(self, context):
        super().configure(context)
        self._thread = spawn(self._discover)

    def process_signals(self, signals):
        if not self.device:
            self.logger.error('No WeMo device connected, dropping {} signals'\
                .format(len(signals)))
            return
        try:
            self.logger.debug('Reading values from device...'.format(self.device))
            self.device.update_insight_params()
        except AttributeError:
            # raised when pywemo has given up retrying
            self.logger.error('Unable to connect to WeMo, dropping {} signals'\
                .format(len(signals)))
            return
        outgoing_signals = []
        for signal in signals:
            new_signal = self.get_output_signal(self.device.insight_params,
                                                signal)
            outgoing_signals.append(new_signal)
        self.notify_signals(outgoing_signals)

    def _discover(self):
        devices = []
        while not devices:
            self.logger.debug('Discovering WeMo devices on network...')
            devices = pywemo.discover_devices()
        self.logger.debug('Found {} WeMo devices'.format(len(devices)))
        self.device=devices[0]
        self.logger.debug('Selected device {} with MAC {}'.format(
            self.device.name, self.device.mac))
