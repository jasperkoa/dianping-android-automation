import unittest
import xml.etree.ElementTree as ET
from auto_apply import candidates


def node(text='', children='', rect='[0,0][100,100]'):
    return f'<node text="{text}" bounds="{rect}" enabled="true">{children}</node>'


class ParserTest(unittest.TestCase):
    def test_both_member_and_ordinary_rows(self):
        orange = node(children=node('橙V专享') + node('甲餐厅双人套餐') + node('免费抽'))
        normal = node(children=node('乙餐厅双人套餐') + node('免费抽'))
        result = candidates(ET.fromstring(node(children=orange + normal)))
        self.assertEqual([t for t, _ in result], ['甲餐厅双人套餐', '乙餐厅双人套餐'])

    def test_hidden_button(self):
        root = ET.fromstring(node(children=node('橙V专享') + node('甲餐厅双人套餐') + node('免费抽', rect='[0,0][0,0]')))
        self.assertEqual(candidates(root), [])

    def test_no_badge_required(self):
        root = ET.fromstring(node(children=node('甲餐厅双人套餐') + node('免费抽')))
        self.assertEqual([t for t, _ in candidates(root)], ['甲餐厅双人套餐'])

    def test_all_list_excludes_only_registered(self):
        registered = node(children=node('甲餐厅双人套餐') + node('已报名'))
        eligible = node(children=node('乙餐厅双人套餐') + node('免费抽'))
        ordinary = node(children=node('丙餐厅双人套餐') + node('免费抽'))
        root = ET.fromstring(node(children=registered + eligible + ordinary))
        self.assertEqual([t for t, _ in candidates(root)], ['乙餐厅双人套餐', '丙餐厅双人套餐'])

    def test_identity_does_not_include_price(self):
        root = ET.fromstring(node(children=node('橙V专享') + node('甲餐厅双人套餐') + node('西单店') + node('2 3 0') + node('免费抽')))
        self.assertEqual([t for t, _ in candidates(root)], ['甲餐厅双人套餐 | 西单店'])

    def test_price_button_container_is_not_an_activity_title(self):
        price = node(children=node('2 3 8') + node('30个中奖名额') + node('免费抽'))
        root = ET.fromstring(node(children=node('普通餐厅双人套餐') + node('西单店') + price))
        self.assertEqual([t for t, _ in candidates(root)], ['普通餐厅双人套餐 | 西单店'])


if __name__ == '__main__':
    unittest.main()
