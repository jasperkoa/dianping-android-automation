import unittest
from unittest.mock import Mock, patch
from auto_apply import candidates, lv6_8_exclusive, ineligible_reason, IneligibleActivity
from test_parser import node
import test_submission_retry as retry_tests
from test_submission_retry import page
import xml.etree.ElementTree as ET


class EligibilityTests(unittest.TestCase):
    def test_only_explicit_range_exclusive_is_prefiltered(self):
        for value in ['Lv6-8专享', 'LV6–LV8专享', 'Ｌｖ６～８ 专享']:
            self.assertTrue(lv6_8_exclusive(value))
        for value in ['橙V专享', 'Lv5专享', 'Lv6专享', 'Lv6-8', '普通活动']:
            self.assertFalse(lv6_8_exclusive(value))

    def test_restricted_row_does_not_exclude_ordinary_neighbor(self):
        restricted = node(children=node('受限餐厅双人套餐')+node('Lv6-8专享')+node('免费抽'))
        ordinary = node(children=node('普通餐厅双人套餐')+node('免费抽'))
        root = ET.fromstring(node(children=restricted+ordinary))
        self.assertEqual([t for t, _ in candidates(root)], ['普通餐厅双人套餐'])

    def test_post_click_insufficient_level_is_not_retried(self):
        bot, n = retry_tests.SubmissionTests().bot()
        bot.seen = set()
        bot.wait_for = Mock(side_effect=[('我要报名', n), IneligibleActivity('您的等级暂不符合报名条件')])
        bot.apply('测试活动', n)
        self.assertIn('测试活动', bot.seen)
        self.assertEqual(bot.success, 0)
        self.assertEqual(bot.tap.call_count, 2)
        bot.return_list.assert_called_once()

    @patch('auto_apply.time.sleep')
    def test_confirmation_open_failure_can_retry(self, sleep):
        bot, n = retry_tests.SubmissionTests().bot()
        bot.wait_for = Mock(side_effect=[('我要报名', n), RuntimeError('network'),
                                         ('确认报名', n), ('报名成功', n)])
        bot.recover_submission = Mock(return_value=('retry', n))
        bot.apply('测试活动', n)
        self.assertEqual(bot.success, 1)
        bot.recover_submission.assert_called_once()

    def test_restriction_notice_without_exclusive_word(self):
        self.assertIsNotNone(ineligible_reason(page('本活动仅限Lv6-Lv8用户报名')))
        self.assertIsNone(ineligible_reason(page('网络异常，请重试')))


if __name__ == '__main__':
    unittest.main()
