from requests.exceptions import ConnectionError
from pywemo import discover_devices
from pywemo.ouimeaux_device.insight import Insight
from nio import Block, Signal
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.command import command
from nio.properties import StringProperty, VersionProperty
from nio.util.threading import spawn


@command('rediscover')
class WeMoInsight(Block, EnrichSignals):

    device_mac = StringProperty(title='MAC Address of Target Device',
                                allow_none=True)
    version = VersionProperty('0.1.0')

    def __init__(self):
        super().__init__()
        self.device = None
        self._thread = None
        self._discovering = False
        self._updating = False

    def configure(self, context):
        super().configure(context)
        self._thread = spawn(self._discover)

    def process_signals(self, signals):
        if not self.device:
            self.logger.error('No WeMo device connected, dropping {} signals'\
                .format(len(signals)))
            if self._discovering:
                return
            else:
                self._thread = spawn(self._discover)
                return
        if not self._updating:
            self.logger.debug('Reading values from {} {}...'\
                .format(self.device.name, self.device.mac))
            self._updating = True
            try:
                self.device.update_insight_params()
                self._updating = False
            except AttributeError:
                # raised when update_insight_params has given up retrying
                self.logger.error(
                    'Unable to connect to WeMo, '\
                    'dropping {} signals'.format(len(signals)))
                self.device = None
                self._updating = False
                return
        else:
            # drop new signals while retrying
            self.logger.error(
                'Another thread is waiting for param update, '\
                'dropping {} signals'.format(len(signals)))
            return
        outgoing_signals = []
        for signal in signals:
            new_signal = self.get_output_signal(self.device.insight_params,
                                                signal)
            outgoing_signals.append(new_signal)
        self.notify_signals(outgoing_signals)

    def rediscover(self):
        self.logger.info('Rediscover command received!')
        status = 'OK'
        if self.device:
            status += ', dropped device \"{}\" with MAC {}'\
                .format(self.device.name, self.device.mac)
        self.device = None
        self._discover()
        return {'status': status}

    def _discover(self):
        self._discovering = True
        insight_devices = []
        while not insight_devices:
            self.logger.debug('Discovering WeMo devices on network...')
            try:
                devices = discover_devices()
            except ConnectionError:
                self.logger.error('Error discovering devices, aborting')
                self._discovering = False
                return
            for device in devices:
                if isinstance(device, Insight):
                    if self.device_mac():
                        if device.mac == self.device_mac():
                            insight_devices.append(device)
                    else:
                        insight_devices.append(device)
        self.logger.debug('Found {} WeMo Insight devices'\
            .format(len(insight_devices)))
        self.device = insight_devices[0]
        self.logger.debug('Selected device \"{}\" with MAC {}'\
            .format(self.device.name, self.device.mac))
        self._discovering = False
