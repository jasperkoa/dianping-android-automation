import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET
from PIL import Image
from auto_apply import Bot, notice_image_controls, ineligible_reason


def notice():
    return ET.fromstring('''<hierarchy>
      <node text="你暂未满足报名要求" bounds="[203,1016][878,1092]"/>
      <node text="该活动仅Lv6-Lv8且是橙V的用户可报名" bounds="[203,1122][878,1242]"/>
      <node class="android.widget.ImageView" clickable="true" bounds="[930,866][1005,941]"/>
      <node class="android.widget.ImageView" clickable="true" bounds="[203,1302][878,1415]"/>
      <node class="android.widget.ImageView" clickable="true" bounds="[948,104][1035,191]"/>
    </hierarchy>''')


class NoticeTests(unittest.TestCase):
    def bot(self):
        bot = Bot.__new__(Bot)
        bot.width, bot.height = 1080, 2340
        bot.tap, bot.back, bot.log = Mock(), Mock(), Mock()
        bot.snapshot = Mock(return_value=ET.fromstring('<hierarchy/>'))
        return bot

    def test_current_notice_detected(self):
        self.assertEqual(ineligible_reason(notice()), '你暂未满足报名要求')

    def test_image_acknowledgement_not_navigation_back(self):
        root = notice()
        primary, cross = notice_image_controls(root,1080,2340)
        bot = self.bot()
        bot.screenshot = Mock(return_value=Image.new('RGB',(1080,2340),(255,102,51)))
        bot.dismiss_submission_notice(root)
        bot.tap.assert_called_once_with(primary)
        bot.back.assert_not_called()
        self.assertEqual(cross.get('bounds'), '[930,866][1005,941]')

    def test_cross_fallback_not_top_toolbar(self):
        root = notice()
        _, cross = notice_image_controls(root,1080,2340)
        bot = self.bot()
        bot.screenshot = Mock(return_value=Image.new('RGB',(1080,2340),'white'))
        bot.dismiss_submission_notice(root)
        bot.tap.assert_called_once_with(cross)
        bot.back.assert_not_called()

    def test_unknown_notice_controls_never_use_back(self):
        root = notice()
        for n in list(root)[2:]:
            root.remove(n)
        bot = self.bot()
        with self.assertRaises(RuntimeError):
            bot.dismiss_submission_notice(root)
        bot.back.assert_not_called()


if __name__ == '__main__':
    unittest.main()
