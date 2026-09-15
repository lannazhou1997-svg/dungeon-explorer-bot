from __future__ import annotations

import random
import unittest
from pathlib import Path

from school_dungeon.game.engine import GameEngine
from school_dungeon.game.models import Player
from school_dungeon.game.questions import CHARACTER_QUESTION_BANK


class SchoolDungeonImprovementTests(unittest.TestCase):
    def test_static_fallback_starts_gentle_and_grows_with_floor(self):
        early_hp, early_attack = GameEngine.school_difficulty_multipliers(1)
        deep_hp, deep_attack = GameEngine.school_difficulty_multipliers(100)

        self.assertEqual((early_hp, early_attack), (1.04, 1.03))
        self.assertEqual((deep_hp, deep_attack), (1.20, 1.15))

    def test_static_fallback_applies_without_player_data(self):
        engine = GameEngine(random.Random(1))
        monster = engine._make_monster(100)
        boss = engine._make_boss(100)

        base_monster_hp = int(38 * (1 + 100 * 0.11 + 90 * 0.006))
        base_boss_hp = int(115 * (1 + 100 * 0.13 + 90 * 0.007))
        self.assertGreaterEqual(monster.max_hp, int(base_monster_hp * 1.19))
        self.assertGreaterEqual(boss.max_hp, int(base_boss_hp * 1.19))

    def test_adaptive_stats_match_the_comfortable_target_rounds(self):
        engine = GameEngine(random.Random(5))
        player = Player(
            1,
            "动态考生",
            level=20,
            hp=250,
            max_hp=250,
            weapon_attack=100,
            clothing_defense=60,
        )

        normal = engine._make_monster(100, player=player)
        boss = engine._make_boss(100, player=player)

        self.assertEqual(engine.expected_player_hit(player), 160)
        self.assertEqual((normal.max_hp, normal.attack), (640, 88))
        self.assertEqual((boss.max_hp, boss.attack), (1920, 102))

    def test_actual_encounter_strength_varies_by_player(self):
        engine = GameEngine(random.Random(6))
        beginner = Player(1, "新生", floor=60)
        veteran = Player(
            2,
            "高练度考生",
            floor=60,
            level=35,
            hp=420,
            max_hp=420,
            weapon_attack=140,
            clothing_defense=85,
        )

        beginner_enemy = engine._make_monster(60, player=beginner)
        veteran_enemy = engine._make_monster(60, player=veteran)

        self.assertGreater(veteran_enemy.max_hp, beginner_enemy.max_hp)
        self.assertGreater(veteran_enemy.attack, beginner_enemy.attack)

    def test_floor_sixty_and_above_use_character_card_questions(self):
        engine = GameEngine(random.Random(2))
        player = Player(1, "高层考生", floor=60)
        player.enemy = engine._make_boss(60)
        player.enemy.hp = player.enemy.max_hp * 0.69

        result = engine._maybe_start_boss_quiz(player)

        self.assertIsNotNone(result)
        self.assertEqual(player.pending_quiz["subject"], "角色卡")
        self.assertTrue(str(player.pending_quiz["key"]).startswith("char_"))

    def test_character_question_bank_is_large_and_uses_multiple_characters(self):
        prefixes = {item.key.rsplit("_", 1)[0] for item in CHARACTER_QUESTION_BANK}

        self.assertGreaterEqual(len(CHARACTER_QUESTION_BANK), 12)
        self.assertGreaterEqual(len(prefixes), 6)

    def test_timeout_counts_as_skipped_turn_and_boss_attacks(self):
        engine = GameEngine(random.Random(3))
        player = Player(1, "超时考生", floor=60, hp=200, max_hp=200)
        player.enemy = engine._make_boss(60)
        player.pending_quiz = {
            "answer": "正确答案",
            "explanation": "测试解析",
            "correct_index": 0,
            "deadline": 1,
        }
        hp_before = player.hp

        result = engine.answer_quiz(player, None, now=2)

        self.assertEqual(result.title, "❌ 答题超时！")
        self.assertLess(player.hp, hp_before)
        self.assertIsNone(player.pending_quiz)

    def test_all_normal_potions_convert_in_bulk_at_three_to_one(self):
        engine = GameEngine(random.Random(4))
        player = Player(1, "合成考生")
        player.consumables = {
            "学生牛奶": 8,
            "校园营养餐": 1,
            "清凉油": 3,
            "运动饮料": 2,
        }

        result = engine.convert_potions(player)

        self.assertEqual(result.title, "🧪 补给合成完成")
        self.assertEqual(player.consumables["学生牛奶"], 2)
        self.assertEqual(player.consumables["校园营养餐"], 3)
        self.assertEqual(player.consumables["清凉油"], 0)
        self.assertEqual(player.consumables["强劲薄荷糖"], 1)
        self.assertEqual(player.consumables["运动饮料"], 2)

    def test_adventure_panel_wires_daily_tasks_conversion_and_keeps_timeout_task(self):
        runtime_source = (
            Path(__file__).parents[1] / "school_dungeon" / "runtime.py"
        ).read_text(encoding="utf-8")

        self.assertIn("container.add_item(DungeonQuestUtilities(player))", runtime_source)
        self.assertIn('DailyQuestButton("dungeon:adventure_daily_quests")', runtime_source)
        self.assertIn('"convert_potions", "一键合成补给"', runtime_source)
        self.assertIn("QUIZ_TIMEOUT_TASKS.add(task)", runtime_source)
        self.assertIn("task.add_done_callback(finish_quiz_timeout_task)", runtime_source)


if __name__ == "__main__":
    unittest.main()
