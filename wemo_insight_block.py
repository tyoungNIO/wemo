import pywemo
from nio import Block, Signal
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.properties import VersionProperty


class WeMoInsight(Block, EnrichSignals):

    version = VersionProperty('0.1.0')

    def __init__(self):
        super().__init__()
        self.device = None

    def configure(self, context):
        super().configure(context)
        devices = pywemo.discover_devices()
        self.logger.debug('Found {} WeMo devices'.format(len(devices)))
        self.device = devices[0]

    def start(self):
        super().start()

    def process_signals(self, signals):
        outgoing_signals = []
        for signal in signals:
            self.device.update_insight_params()
            new_signal = self.get_output_signal(self.device.insight_params,
                                                signal)
            outgoing_signals.append(new_signal)
        self.notify_signals(outgoing_signals)
