from threading import Event
from requests.exceptions import ConnectionError
from unittest.mock import patch, MagicMock
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..wemo_base import WeMoBase
from ..wemo_insight_block import WeMoInsight


class EventWeMoDiscovery(WeMoInsight):

    def __init__(self, event, *args, **kwargs):
        self.event = event
        super().__init__(*args, **kwargs)

    def _discover(self):
        super()._discover()
        # Set the event after discovery happens
        self.event.set()


@patch(WeMoBase.__module__ + '.discover_devices')
class TestWeMoInsight(NIOBlockTestCase):

    def setUp(self):
        super().setUp()
        with patch(
                'pywemo.ouimeaux_device.insight.Insight',
                autospec=True) as Insight:
            self.mock_insight = Insight('host', 'mac')
            self.mock_insight.mac = 'mac'
        # Patch twice so we get different mock instances for our two devices
        with patch(
                'pywemo.ouimeaux_device.insight.Insight',
                autospec=True) as Insight:
            self.mock_insight_2 = Insight('host', 'mac2')
            self.mock_insight_2.mac = 'mac2'

    def test_process_signals(self, mock_discover):
        """ Params are read from an Insight device for every signal list
        processed and each signal is enriched with the contents."""
        self.mock_insight.insight_params = {'pi': 3.14}
        mock_discover.return_value = [self.mock_insight]
        discover_event = Event()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {'enrich': {'exclude_existing': False}})
        blk.start()
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(mock_discover.call_count, 1)
        blk.process_signals([Signal({'foo': 'bar'}), Signal({'foo': 'baz'})])
        self.assertEqual(self.mock_insight.update_insight_params.call_count, 2)
        self.assert_num_signals_notified(2)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'pi': 3.14, 'foo': 'bar'})
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][1].to_dict(),
            {'pi': 3.14, 'foo': 'baz'})
        blk.stop()

    def test_rediscovery(self, mock_discover, *args):
        """ Retry discovery if it has failed."""
        self.mock_insight.insight_params = {'pi': 3.14}
        mock_discover.side_effect = [ConnectionError, [self.mock_insight]]
        discover_event = Event()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {})
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(mock_discover.call_count, 1)
        self.assertFalse(blk._discovering)
        self.assertIsNone(blk.device)
        discover_event.clear()
        blk.start()
        # ConnectionError raised, discovery aborted

        blk.process_signals([Signal()])
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(mock_discover.call_count, 2)
        # device discovered
        self.assertEqual(blk.device, self.mock_insight)
        # signal was dropped, so no params retrieved from device
        self.assertEqual(self.mock_insight.update_insight_params.call_count, 0)
        # and nothing notified
        self.assert_num_signals_notified(0)

        # now we have a device
        blk.process_signals([Signal()])
        self.assertEqual(mock_discover.call_count, 2)
        self.assertEqual(self.mock_insight.update_insight_params.call_count, 1)
        self.assert_num_signals_notified(1)
        blk.stop()

    def test_single_update_caller(self, mock_discover, *args):
        """ Only one thread should have an active/retrying call to update."""
        self.mock_insight.insight_params = {'pi': 3.14}
        mock_discover.return_value = [self.mock_insight]
        discover_event = Event()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {})
        blk.start()
        self.assertTrue(discover_event.wait(1))
        # another call to process_signals is still waiting for params
        blk._updating = True
        blk.process_signals([Signal()])
        # these signals are dropped
        self.assertEqual(self.mock_insight.update_insight_params.call_count, 0)
        blk.stop()

    def test_insight_devices_only(self, mock_discover, *args):
        """ WeMo devices other than Insight are ignored"""
        discover_event = Event()
        mock_discover.return_value = [MagicMock(), self.mock_insight]
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {})
        blk.start()
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(blk.device, self.mock_insight)
        blk.stop()

        # if no insight devices are found discovery continues
        mock_discover.return_value = [MagicMock()]
        discover_event.clear()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {})
        blk.start()
        # Wait some time but don't expect discover to actually finish
        self.assertFalse(discover_event.wait(0.2))
        self.assertIsNone(blk.device)
        self.assertTrue(blk._discovering)
        blk.stop()

    def test_configured_mac(self, mock_discover, *args):
        """ Device with specified MAC is selected."""
        mock_discover.return_value = [self.mock_insight_2, self.mock_insight]
        discover_event = Event()
        blk = EventWeMoDiscovery(discover_event)
        # Looking for the 2nd insight in the list only
        self.configure_block(blk, {'device_mac': 'mac'})
        blk.start()
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(blk.device, self.mock_insight)
        blk.stop()

        # if the specified MAC isn't found discovery continues
        discover_event.clear()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {'device_mac': 'other'})
        blk.start()
        # Wait some time but don't expect discover to actually finish
        self.assertFalse(discover_event.wait(0.2))
        self.assertIsNone(blk.device)
        self.assertTrue(blk._discovering)
        blk.stop()

    def test_rediscover_cmd(self, mock_discover, *args):
        """ Device is dropped and discovery begins when commanded."""
        mock_discover.side_effect = [
            [self.mock_insight], [self.mock_insight_2]]
        discover_event = Event()
        blk = EventWeMoDiscovery(discover_event)
        self.configure_block(blk, {})
        blk.start()
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(blk.device, self.mock_insight)
        discover_event.clear()
        blk.rediscover()
        self.assertTrue(discover_event.wait(1))
        self.assertEqual(blk.device, self.mock_insight_2)
        blk.stop()
