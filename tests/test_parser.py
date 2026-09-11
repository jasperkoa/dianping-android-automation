import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from auto_apply import candidates  # noqa: E402


def node(text="", children="", rect="[0,0][100,100]"):
    return f'<node text="{text}" bounds="{rect}" enabled="true">{children}</node>'


class ParserTest(unittest.TestCase):
    def test_orange_and_ordinary_rows_are_candidates(self):
        orange = node(children=node("橙V专享") + node("甲餐厅双人套餐") + node("免费抽"))
        ordinary = node(children=node("乙餐厅双人套餐") + node("免费抽"))
        result = candidates(ET.fromstring(node(children=orange + ordinary)))
        self.assertEqual([title for title, _ in result], ["甲餐厅双人套餐", "乙餐厅双人套餐"])

    def test_hidden_button_is_ignored(self):
        root = ET.fromstring(node(children=node("甲餐厅双人套餐") + node("免费抽", rect="[0,0][0,0]")))
        self.assertEqual(candidates(root), [])

    def test_registered_row_without_action_button_is_ignored(self):
        registered = node(children=node("甲餐厅双人套餐") + node("已报名"))
        eligible = node(children=node("乙餐厅双人套餐") + node("免费抽"))
        root = ET.fromstring(node(children=registered + eligible))
        self.assertEqual([title for title, _ in candidates(root)], ["乙餐厅双人套餐"])

    def test_identity_does_not_include_price(self):
        root = ET.fromstring(
            node(children=node("甲餐厅双人套餐") + node("西单店") + node("230") + node("免费抽"))
        )
        self.assertEqual([title for title, _ in candidates(root)], ["甲餐厅双人套餐 | 西单店"])

    def test_parent_with_multiple_action_buttons_is_not_used_as_single_card(self):
        first = node(children=node("甲餐厅双人套餐") + node("免费抽"))
        second = node(children=node("乙餐厅双人套餐") + node("免费抽奖"))
        root = ET.fromstring(node(children=first + second))
        self.assertEqual([title for title, _ in candidates(root)], ["甲餐厅双人套餐", "乙餐厅双人套餐"])


if __name__ == "__main__":
    unittest.main()
