import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET
from PIL import Image
from auto_apply import Bot, activity_step
from screen_guard import inside, list_area, orange_button


class GuardTests(unittest.TestCase):
    def test_success_scrolls_after_returning_to_list(self):
        root = ET.fromstring('''<hierarchy>
            <node text="确认报名信息" bounds="[1,1][10,10]"/>
            <node text="确认报名" bounds="[1,11][10,20]"/></hierarchy>''')
        button = root.find('node')
        bot = Bot.__new__(Bot)
        bot.root, bot.success = root, 0
        bot.snapshot = Mock(return_value=root)
        bot.choices = Mock(return_value=[('测试餐厅', button)])
        bot.tap = Mock()
        bot.log = Mock()
        bot.wait_for = Mock(side_effect=[('我要报名', button), ('确认报名', button), ('报名成功', button)])
        order = []
        bot.return_list = lambda: order.append('return')
        bot.ensure_all_list = lambda: order.append('list')
        bot.scroll_one_activity = lambda: order.append('scroll-one')
        bot.apply('测试餐厅', button)
        self.assertEqual(bot.success, 1)
        self.assertEqual(order, ['return', 'list', 'scroll-one'])

    def test_one_card_height_includes_registered_rows(self):
        root = ET.fromstring('''<hierarchy>
            <node text="已报名餐厅 | 双人套餐" bounds="[324,800][950,860]"/>
            <node text="下一餐厅 | 双人套餐" bounds="[324,1180][950,1290]"/>
            <node text="第三餐厅 | 双人套餐" bounds="[324,1610][950,1670]"/>
            </hierarchy>''')
        self.assertEqual(activity_step(root, 1080, 2340), (380, '下一餐厅 | 双人套餐', 1180))

    def test_one_card_fallback_is_not_a_full_page(self):
        self.assertEqual(activity_step(ET.fromstring('<hierarchy/>'), 1080, 2340), (335, None, None))

    def test_more_menu_detected_but_filter_label_is_not_menu(self):
        menu = ET.fromstring('''<hierarchy><node text="活动订阅" bounds="[1,1][10,10]"/>
            <node text="免费试规则" bounds="[1,11][10,20]"/></hierarchy>''')
        filters = ET.fromstring('''<hierarchy><node text="更多筛选" bounds="[1,1][10,10]"/></hierarchy>''')
        self.assertTrue(Bot.menu_visible(menu))
        self.assertFalse(Bot.menu_visible(filters))

    def test_toolbar_and_footer_are_excluded(self):
        area = list_area(1080, 2340)
        self.assertFalse(inside([882, 140, 999, 190], area))
        self.assertFalse(inside([882, 2000, 999, 2070], area))
        self.assertTrue(inside([882, 1500, 999, 1570], area))

    def test_gray_mine_tab_is_not_an_orange_button(self):
        gray = Image.new('RGB', (100, 50), (180, 180, 180))
        orange = Image.new('RGB', (100, 50), (255, 102, 51))
        self.assertFalse(orange_button(gray, [0, 0, 100, 50]))
        self.assertTrue(orange_button(orange, [0, 0, 100, 50]))

    def test_retry_does_not_use_title_from_hidden_button(self):
        root = ET.fromstring('''<hierarchy><node><node text="普通餐厅双人套餐" bounds="[324,1900][950,1970]"/>
            <node text="免费抽" bounds="[882,2020][999,2070]"/></node></hierarchy>''')
        bot = Bot.__new__(Bot)
        bot.width, bot.height = 1080, 2340
        self.assertEqual(bot.choices(root), [])


if __name__ == '__main__':
    unittest.main()
