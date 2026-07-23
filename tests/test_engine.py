
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

    def test_every_tenth_floor_is_major_boss(self):
        engine = GameEngine(random.Random(1))
        self.assertEqual(engine._make_boss(4).boss_kind, "小 Boss")
        self.assertEqual(engine._make_boss(5).boss_kind, "小 Boss")
        self.assertEqual(engine._make_boss(10).boss_kind, "大 Boss")
        self.assertEqual(engine._make_boss(100).boss_kind, "大 Boss")

    def test_regular_floor_clears_without_a_boss(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "冒险者", floor=4, required_steps=1)

        result = engine.explore(player)

        self.assertEqual(result.title, "🚪 找到下层入口")
        self.assertEqual(player.floor, 5)
        self.assertIsNone(player.enemy)

    def test_floor_five_can_randomly_spawn_a_small_boss(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "冒险者", floor=5, required_steps=1)

        engine.explore(player)

        self.assertIsNotNone(player.enemy)
        self.assertEqual(player.enemy.boss_kind, "小 Boss")

    def test_floor_ten_always_spawns_its_fixed_major_boss(self):
        engine = GameEngine(random.Random(999))
        player = Player(1, "冒险者", floor=10, required_steps=1)

        engine.explore(player)

        self.assertEqual(player.enemy.boss_kind, "大 Boss")
        self.assertEqual(player.enemy.name, "黏液大公·噗叽伯爵")

    def test_old_saved_major_boss_name_is_migrated(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "老存档", floor=10, required_steps=5)
        player.enemy = Enemy("深渊领主", 100, 100, 10, 100, "大 Boss")

        engine.ensure_floor(player)

        self.assertEqual(player.enemy.name, "黏液大公·噗叽伯爵")

    def test_death_keeps_equipment_crystals_half_gold_and_two_items(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "测试者", level=8, exp=77, floor=20, hp=1, gold=888, crystals=9)
        player.weapon, player.clothing = "传说之剑", "龙鳞甲"
        player.consumables = {"治疗药水": 5}
        player.enemy = Enemy("测试怪", 999, 999, 999, 1)
        engine.attack(player)
        self.assertEqual((player.level, player.exp, player.floor), (1, 0, 1))
        self.assertEqual((player.gold, player.crystals), (444, 9))
        self.assertEqual((player.weapon, player.clothing), ("传说之剑", "龙鳞甲"))
        self.assertEqual(player.consumables, {"治疗药水": 2})

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

        self.assertEqual(result.title, "📦 你遇到了宝箱")
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

    def test_three_magic_skills_have_ordered_cost_and_damage(self):
        damages = []
        costs = []
        for tier in ("minor", "medium", "major"):
            engine = GameEngine(random.Random(10))
            player = Player(1, "法师", mp=50)
            player.enemy = Enemy("木桩", 9999, 9999, 1, 0)
            before_hp, before_mp = player.enemy.hp, player.mp

            engine.attack(player, skill_tier=tier)

            damages.append(before_hp - player.enemy.hp)
            costs.append(before_mp - player.mp)
        self.assertEqual(costs, [6, 12, 22])
        self.assertLess(damages[0], damages[1])
        self.assertLess(damages[1], damages[2])

    def test_merchant_menu_supports_repeated_purchases(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "顾客", floor=3, gold=200)
        engine._event_shop(player)

        first = engine.buy_merchant_item(player, "healing_potion")
        second = engine.buy_merchant_item(player, "healing_potion")

        self.assertEqual(first.title, "🛍️ 购买成功")
        self.assertEqual(second.title, "🛍️ 购买成功")
        self.assertEqual(player.gold, 140)
        self.assertEqual(player.consumables["治疗药水"], 4)
        self.assertEqual(player.pending_event, "merchant")

    def test_fountain_waits_for_interaction(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "冒险者", hp=40, mp=10, energy=50)

        found = engine._event_recovery(player)

        self.assertEqual(found.title, "⛲ 你遇到了宁静泉水！")
        self.assertEqual((player.hp, player.mp, player.energy), (40, 10, 50))
        self.assertEqual(player.pending_event, "fountain")

        engine.interact_event(player)

        self.assertGreater(player.hp, 40)
        self.assertGreater(player.mp, 10)
        self.assertGreater(player.energy, 48)
        self.assertIsNone(player.pending_event)

    def test_admin_can_force_a_hidden_mimic(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "管理员")

        result = engine.force_event(player, "mimic")

        self.assertEqual(result.title, "📦 你遇到了宝箱")
        self.assertEqual(player.pending_event, "mimic")
        self.assertIsNone(player.enemy)

    def test_admin_forced_major_boss_survives_panel_migration_check(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "管理员", floor=1)

        engine.force_event(player, "major_boss")
        forced_name = player.enemy.name
        engine.ensure_floor(player)

        self.assertEqual(player.enemy.boss_kind, "大 Boss")
        self.assertEqual(player.enemy.name, forced_name)
        self.assertIn(forced_name, engine.MAJOR_BOSS_NAMES.values())

    def test_admin_non_monster_events_never_create_an_enemy(self):
        for event in (
            "chest", "mimic", "fountain", "merchant", "fairy", "mystery",
            "treasure_map", "trapped_beast", "wishing_well", "empty",
        ):
            with self.subTest(event=event):
                engine = GameEngine(random.Random(1))
                player = Player(1, "管理员")

                engine.force_event(player, event)

                self.assertIsNone(player.enemy)

    def test_every_major_boss_has_a_unique_name(self):
        engine = GameEngine(random.Random(1))
        names = [engine._make_boss(floor).name for floor in range(10, 101, 10)]

        self.assertEqual(len(names), 10)
        self.assertEqual(len(set(names)), 10)

    def test_bought_mana_and_energy_potions_can_be_used(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "顾客", gold=500, mp=1, energy=1)
        engine._event_shop(player)
        engine.buy_merchant_item(player, "mana_potion")
        engine.buy_merchant_item(player, "energy_potion")

        mana = engine.use_mana_potion(player)
        energy = engine.use_energy_potion(player)

        self.assertEqual(mana.title, "💧 使用魔力药水")
        self.assertEqual(energy.title, "⚡ 使用精力药水")
        self.assertEqual(player.mp, 26)
        self.assertEqual(player.energy, 31)

    def test_death_retains_exactly_two_consumable_units(self):
        engine = GameEngine(random.Random(1))
        player = Player(1, "冒险者", hp=1)
        player.consumables = {"治疗药水": 5, "魔力药水": 4, "精力药水": 3}
        before = sum(player.consumables.values())
        player.enemy = Enemy("危险木桩", 9999, 9999, 999, 0)

        result = engine.attack(player)

        after = sum(player.consumables.values())
        self.assertTrue(result.death)
        self.assertEqual(result.title, "💀 你死了")
        self.assertEqual(after, 2)
        self.assertLess(after, before)


if __name__ == "__main__":
    unittest.main()
