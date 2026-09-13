import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from auto_apply import Bot


def page(*texts):
    root = ET.Element('hierarchy')
    for text in texts:
        ET.SubElement(root, 'node', text=text, bounds='[100,500][300,600]', enabled='true')
    return root


class SubmissionTests(unittest.TestCase):
    def bot(self):
        bot = Bot.__new__(Bot)
        bot.root = page('确认报名信息', '确认报名')
        button = bot.root[1]
        bot.success = 0
        bot.args = SimpleNamespace(delay=1)
        bot.snapshot = Mock(return_value=bot.root)
        bot.choices = Mock(return_value=[('测试活动', button)])
        bot.tap = Mock()
        bot.log = Mock()
        bot.back = Mock()
        bot.return_list = Mock()
        bot.ensure_all_list = Mock()
        bot.scroll_one_activity = Mock()
        return bot, button

    @patch('auto_apply.time.sleep')
    def test_failure_reopens_and_second_submission_succeeds(self, sleep):
        bot, n = self.bot()
        bot.wait_for = Mock(side_effect=[('我要报名', n), ('确认报名', n), ('报名失败', n),
                                         ('确认报名', n), ('报名成功', n)])
        bot.recover_submission = Mock(return_value=('retry', n))
        bot.apply('测试活动', n)
        self.assertEqual(bot.success, 1)
        bot.recover_submission.assert_called_once_with('测试活动')
        self.assertEqual(bot.tap.call_count, 5)  # Open, apply/confirm twice.
        bot.scroll_one_activity.assert_called_once()

    def test_late_success_does_not_resubmit(self):
        bot, n = self.bot()
        bot.wait_for = Mock(side_effect=[('我要报名', n), ('确认报名', n), RuntimeError('timeout')])
        bot.recover_submission = Mock(return_value=('success', n))
        bot.apply('测试活动', n)
        self.assertEqual(bot.tap.call_count, 3)
        self.assertEqual(bot.success, 1)

    @patch('auto_apply.time.sleep')
    def test_three_failures_skip_activity_without_stopping_batch(self, sleep):
        bot, n = self.bot()
        bot.wait_for = Mock(side_effect=[('我要报名', n)] + [('确认报名', n), ('报名失败', n)]*3)
        bot.recover_submission = Mock(return_value=('retry', n))
        bot.apply('测试活动', n)
        self.assertEqual(bot.success, 0)
        self.assertEqual(bot.tap.call_count, 7)
        bot.return_list.assert_called_once()
        bot.scroll_one_activity.assert_not_called()

    def test_stale_detail_must_return_to_list_before_retry(self):
        bot, n = self.bot()
        detail = page('免费试活动详情', '我要报名')
        listing = page('全部商区')
        bot.snapshot = Mock(side_effect=[detail, listing, detail])
        self.assertEqual(bot.recover_submission('测试活动')[0], 'retry')
        bot.back.assert_called_once()
        bot.tap.assert_called_once_with(n)

    def test_disappeared_activity_is_not_counted_as_success(self):
        bot, _ = self.bot()
        bot.snapshot = Mock(return_value=page('全部商区'))
        bot.choices = Mock(return_value=[])
        self.assertEqual(bot.recover_submission('测试活动')[0], 'skip')


if __name__ == '__main__':
    unittest.main()
