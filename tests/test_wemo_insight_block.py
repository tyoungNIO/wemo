import pywemo
from requests.exceptions import ConnectionError
from unittest.mock import patch, MagicMock
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..wemo_insight_block import WeMoInsight


class TestExample(NIOBlockTestCase):

    @patch(WeMoInsight.__module__ + '.discover_devices')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.requests')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.deviceParser')
    def test_process_signals(self, mock_parser, mock_requests, mock_discover):
        """ Params are read from an Insight device for every signal list 
        processed and each signal is enriched with the contents."""
        mock_insight = pywemo.ouimeaux_device.insight.Insight('host', 'mac')
        mock_insight.update_insight_params = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_discover.return_value = [mock_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {'enrich': {'exclude_existing': False}})
        blk.start()
        self.assertEqual(mock_discover.call_count, 1)
        blk.process_signals([Signal({'foo': 'bar'}), Signal({'foo': 'baz'})])
        self.assertEqual(mock_insight.update_insight_params.call_count, 1)
        self.assert_num_signals_notified(2)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'pi': 3.14, 'foo': 'bar'})
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][1].to_dict(),
            {'pi': 3.14, 'foo': 'baz'})
        blk.stop()

    @patch(WeMoInsight.__module__ + '.discover_devices')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.requests')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.deviceParser')
    def test_rediscovery(self, mock_parser, mock_requests, mock_discover):
        """ Retry discovery if it has failed."""
        mock_insight = pywemo.ouimeaux_device.insight.Insight('host', 'mac')
        mock_insight.update_insight_params = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_discover.side_effect = [ConnectionError, [mock_insight]]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk._thread.join(1)
        self.assertEqual(mock_discover.call_count, 1)
        self.assertFalse(blk._discovering)
        self.assertIsNone(blk.device)
        blk.start()
        # ConnectionError raised, discovery aborted

        blk.process_signals([Signal()])
        self.assertEqual(mock_discover.call_count, 2)
        # device discovered
        self.assertEqual(blk.device, mock_insight)
        # signal was dropped, so no params retrieved from device
        self.assertEqual(mock_insight.update_insight_params.call_count, 0)
        # and nothing notified
        self.assert_num_signals_notified(0)

        # now we have a device
        blk.process_signals([Signal()])
        self.assertEqual(mock_discover.call_count, 2)
        self.assertEqual(mock_insight.update_insight_params.call_count, 1)
        self.assert_num_signals_notified(1)
        blk.stop()

    @patch(WeMoInsight.__module__ + '.discover_devices')
    def test_single_update_caller(self, mock_discover):
        """ Only one thread should have an active/retrying call to update."""
        mock_insight = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_discover.return_value = [mock_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk.start()
        # another call to process_signals is still waiting for params
        blk._updating = True
        blk.process_signals([Signal()])
        # these signals are dropped
        self.assertEqual(mock_insight.update_insight_params.call_count, 0)
        blk.stop()

    @patch(WeMoInsight.__module__ + '.discover_devices')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.requests')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.deviceParser')
    def test_insight_devices_only(self, mock_parser, mock_requests, mock_discover):
        """ WeMo devices other than Insight are ignored"""
        mock_insight = pywemo.ouimeaux_device.insight.Insight('host', 'mac')
        mock_discover.return_value = [MagicMock(), mock_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk.start()
        self.assertEqual(blk.device, mock_insight)
        blk.stop()

        # if no insight devices are found discovery continues
        mock_discover.return_value = [MagicMock()]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk.start()
        self.assertIsNone(blk.device)
        self.assertTrue(blk._discovering)
        blk.stop()

    @patch(WeMoInsight.__module__ + '.discover_devices')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.requests')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.deviceParser')
    def test_configured_mac(self, mock_parser, mock_requests, mock_discover):
        """ Device with specified MAC is selected."""
        my_insight = pywemo.ouimeaux_device.insight.Insight('host', 'my')
        your_insight = pywemo.ouimeaux_device.insight.Insight('host', 'your')
        mock_discover.return_value = [your_insight, my_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {'device_mac': 'my'})
        blk.start()
        self.assertEqual(blk.device, my_insight)
        blk.stop()

        # if the specified MAC isn't found discovery continues
        blk = WeMoInsight()
        self.configure_block(blk, {'device_mac': 'other'})
        blk.start()
        self.assertIsNone(blk.device)
        self.assertTrue(blk._discovering)
        blk.stop()

    @patch(WeMoInsight.__module__ + '.discover_devices')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.requests')
    @patch(pywemo.ouimeaux_device.Device.__module__ + '.deviceParser')
    def test_rediscover_cmd(self, mock_parser, mock_requests, mock_discover):
        """ Device is dropped and discovery begins when commanded."""
        my_insight = pywemo.ouimeaux_device.insight.Insight('host', 'my')
        your_insight = pywemo.ouimeaux_device.insight.Insight('host', 'your')
        mock_discover.side_effect = [[my_insight], [your_insight]]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk.start()
        self.assertEqual(blk.device, my_insight)
        blk.rediscover()
        self.assertEqual(blk.device, your_insight)
        blk.stop()
