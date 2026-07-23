import random
import unittest

from game.engine import GameEngine
from game.models import Enemy, Player


class EngineTests(unittest.TestCase):
    def test_required_steps_expand_with_depth(self):
        early = GameEngine(random.Random(1)).required_steps(1)
        deep = GameEngine(random.Random(1)).required_steps(100)
        self.assertTrue(12 <= early <= 24)
        self.assertTrue(24 <= deep <= 36)

    def test_every_fifth_floor_is_major_boss(self):
        engine = GameEngine(random.Random(1))
        self.assertEqual(engine._make_boss(4).boss_kind, "小 Boss")
        self.assertEqual(engine._make_boss(5).boss_kind, "大 Boss")
        self.assertEqual(engine._make_boss(100).boss_kind, "大 Boss")

    def test_death_keeps_equipment_and_currency_only(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "测试者", level=8, exp=77, floor=20, hp=1, gold=888, crystals=9)
        player.weapon, player.clothing = "传说之剑", "龙鳞甲"
        player.consumables = {"治疗药水": 5}
        player.enemy = Enemy("测试怪", 999, 999, 999, 1)
        engine.attack(player)
        self.assertEqual((player.level, player.exp, player.floor), (1, 0, 1))
        self.assertEqual((player.gold, player.crystals), (888, 9))
        self.assertEqual((player.weapon, player.clothing), ("传说之剑", "龙鳞甲"))
        self.assertEqual(player.consumables, {})

    def test_boss_victory_advances_floor(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "测试者", floor=4)
        player.enemy = Enemy("守门石像", 1, 1, 1, 10, "小 Boss")
        engine.attack(player)
        self.assertEqual(player.floor, 5)
        self.assertEqual(player.steps, 0)
        self.assertIsNone(player.enemy)

    def test_mimic_is_hidden_until_interaction(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "测试者")

        result = engine._event_mimic(player)

        self.assertEqual(result.title, "📦 你遇到了宝箱？")
        self.assertIsNone(player.enemy)
        self.assertEqual(player.pending_event, "mimic")

        reveal = engine.interact_event(player)

        self.assertEqual(reveal.title, "😈 你遇到了宝箱怪！")
        self.assertIsNotNone(player.enemy)
        self.assertEqual(player.enemy.boss_kind, "宝箱怪")
        self.assertIsNone(player.pending_event)

    def test_level_and_weapon_both_increase_damage(self):
        low_engine = GameEngine(random.Random(10))
        high_engine = GameEngine(random.Random(10))
        low = Player(1, "新手", level=1, weapon_attack=4)
        high = Player(2, "高手", level=10, weapon_attack=20)
        low.enemy = Enemy("木桩", 9999, 9999, 1, 0)
        high.enemy = Enemy("木桩", 9999, 9999, 1, 0)

        low_before, high_before = low.enemy.hp, high.enemy.hp
        low_engine.attack(low)
        high_engine.attack(high)

        self.assertGreater(high_before - high.enemy.hp, low_before - low.enemy.hp)

    def test_merchant_sells_a_potion(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "顾客", floor=3, gold=100)
        engine._event_shop(player)

        result = engine.interact_event(player)

        self.assertEqual(result.title, "🤝 交易完成！")
        self.assertEqual(player.gold, 69)
        self.assertEqual(player.consumables["治疗药水"], 3)
        self.assertIsNone(player.pending_event)


if __name__ == "__main__":
    unittest.main()
