from unittest.mock import patch, MagicMock
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..wemo_insight_block import WeMoInsight


class TestExample(NIOBlockTestCase):

    @patch(WeMoInsight.__module__ + '.pywemo')
    def test_process_signals(self, mock_pywemo):
        """ Params are read from an Insight device for every signal processed
        and signals are enriched with the contents."""
        mock_insight = MagicMock()
        mock_insight.insight_params = {'pi': 3.14}
        mock_pywemo.discover_devices.return_value = [mock_insight]
        blk = WeMoInsight()
        self.configure_block(blk, {'enrich': {'exclude_existing': False}})
        blk.start()
        self.assertEqual(mock_pywemo.discover_devices.call_count, 1)
        blk.process_signals([Signal({'et': 'cetera'})])
        self.assertEqual(mock_insight.update_insight_params.call_count, 1)
        blk.stop()
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {'pi': 3.14, 'et': 'cetera'})
