
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


if __name__ == "__main__":
    unittest.main()
