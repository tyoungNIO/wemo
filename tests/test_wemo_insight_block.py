from time import sleep
from requests.exceptions import ConnectionError
from unittest.mock import patch, MagicMock
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..wemo_insight_block import WeMoInsight


class TestExample(NIOBlockTestCase):

    @patch(WeMoInsight.__module__ + '.pywemo')
    def test_process_signals(self, mock_pywemo):
        """ Params are read from an Insight device for every signal list 
        processed and each signal is enriched with the contents."""
        mock_insight = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_pywemo.discover_devices.return_value = [mock_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {'enrich': {'exclude_existing': False}})
        blk.start()
        self.assertEqual(mock_pywemo.discover_devices.call_count, 1)
        blk.process_signals([Signal({'foo': 'bar'}), Signal({'foo': 'baz'})])
        self.assertEqual(mock_insight.update_insight_params.call_count, 1)
        blk.stop()
        self.assert_num_signals_notified(2)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'pi': 3.14, 'foo': 'bar'})
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][1].to_dict(),
            {'pi': 3.14, 'foo': 'baz'})

    @patch(WeMoInsight.__module__ + '.pywemo')
    def test_rediscovery(self, mock_pywemo):
        """ Retry discovery if it has failed."""
        mock_insight = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_pywemo.discover_devices.side_effect = [
            ConnectionError, [mock_insight]]
        blk = WeMoInsight()
        self.configure_block(blk, {})
        blk.start()
        self.assertTrue(blk._discovering)
        self.assertEqual(mock_pywemo.discover_devices.call_count, 1)
        # ConnectionError raised
        sleep(0.1)
        # discovery aborted
        self.assertFalse(blk._discovering)

        blk.process_signals([Signal()])
        self.assertEqual(mock_pywemo.discover_devices.call_count, 2)
        # device discovered
        self.assertEqual(blk.device, mock_insight)
        # signal was dropped, so no params retrieved from device
        self.assertEqual(mock_insight.update_insight_params.call_count, 0)
        # and nothing notified
        self.assert_num_signals_notified(0)

        blk.process_signals([Signal()])
        self.assertEqual(mock_pywemo.discover_devices.call_count, 2)
        self.assertEqual(mock_insight.update_insight_params.call_count, 1)
        blk.stop()
        self.assert_num_signals_notified(1)
