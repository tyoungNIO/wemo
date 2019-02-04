from requests.exceptions import ConnectionError
from pywemo import discover_devices
from time import sleep
from nio import Block
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.command import command
from nio.properties import StringProperty
from nio.util.threading import spawn
from nio.util.discovery import not_discoverable


@command('rediscover')
@not_discoverable
class WeMoBase(Block, EnrichSignals):

    device_mac = StringProperty(title='MAC Address of Target Device',
                                allow_none=True)

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
            self.logger.warning(
                'No WeMo device connected, dropping {} signals'.format(
                    len(signals)))
            if self._discovering:
                return
            else:
                self._thread = spawn(self._discover)
                return
        outgoing_signals = []
        for signal in signals:
            new_signal = self.get_output_signal(
                self.execute_wemo_command(signal), signal)
            outgoing_signals.append(new_signal)
        self.notify_signals(outgoing_signals)

    def execute_wemo_command(self, signal):
        """ Override this method - do something to the wemo device

        Return a result to be enriched on to the incoming signal
        """
        return {}

    def rediscover(self):
        self.logger.info('Rediscover command received!')
        if self._discovering:
            status = 'Discovery already in progress'
        else:
            status = 'OK'
            if self.device:
                status += ', dropped device \"{}\" with MAC {}'\
                    .format(self.device.name, self.device.mac)
            self.device = None
            self._thread = spawn(self._discover)
        self.logger.info(status)
        return {'status': status}

    def is_valid_device(self, device):
        """ Override to determine whether the device should be considered

        Can check device type, device MAC address, etc

        This parent function will check that the MAC address matches if it
        was specified in the block parameters

        Return a boolean for whether it is valid
        """
        if self.device_mac():
            return device.mac == self.device_mac()
        # If no MAC specified consider it valid
        return True

    def _discover(self):
        self._discovering = True
        self.device = None
        while not self.device:
            self.logger.debug('Discovering WeMo devices on network...')
            try:
                devices = discover_devices()
            except ConnectionError:
                self.logger.error('Error discovering devices, aborting')
                self._discovering = False
                return
            self.logger.debug('Found {} WeMo devices'.format(len(devices)))
            for device in devices:
                self.logger.debug('Checking device {}'.format(device))
                if self.is_valid_device(device):
                    self.device = device
                    break
            else:
                # If we didn't find a device wait a bit before trying again
                sleep(0.1)
        self.logger.info('Selected device \"{}\" with MAC {}'.format(
            self.device.name, self.device.mac))
        self._discovering = False

    def stop(self):
        # End the discovery thread if it's running
        if self._thread:
            self._thread.join(0.2)
        super().stop()
