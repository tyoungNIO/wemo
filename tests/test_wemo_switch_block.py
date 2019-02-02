from threading import Event
from unittest.mock import patch
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..wemo_base import WeMoBase
from ..wemo_switch_block import WeMoSwitch


class EventWeMoDiscovery(WeMoSwitch):

    def __init__(self, event, *args, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)

    def _discover(self):
        super()._discover()
        # Set the event after discovery happens
        self.event.set()


@patch(WeMoBase.__module__ + '.discover_devices')
class TestWeMoSwitch(NIOBlockTestCase):

    def setUp(self):
        super().setUp()
        with patch(
                'pywemo.ouimeaux_device.switch.Switch',
                autospec=True) as Switch:
            self.mock_switch = Switch('host', 'mac')
            self.mock_switch.mac = 'mac'

    def test_process_signals(self, mock_discover):
        """ Status is updated on incoming signals """
        self.mock_switch.get_state.return_value = True
        mock_discover.return_value = [self.mock_switch]
        discovery_event = Event()
        blk = EventWeMoDiscovery(discovery_event)
        self.configure_block(blk, {
            'enrich': {'exclude_existing': False},
            'switch_state': '{{ $switch_set }}',
        })
        blk.start()
        self.assertTrue(discovery_event.wait(1))
        self.assertEqual(mock_discover.call_count, 1)
        blk.process_signals([Signal({'switch_set': True})])
        self.assertEqual(self.mock_switch.set_state.call_count, 1)
        self.mock_switch.set_state.assert_called_once_with(True)
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'switch_set': True, 'state': True})
        blk.stop()
