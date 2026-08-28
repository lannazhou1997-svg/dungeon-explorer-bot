import random
import unittest

from school_dungeon.game.engine import GameEngine
from school_dungeon.game.models import Player
from school_dungeon.game.questions import QUESTION_BANK, draw_question
from school_dungeon.game.school_content import (
    FINAL_BOSS_ALIAS,
    MAJOR_BOSS_NAMES,
    MERCHANT_NAME,
    monster_names_for_floor,
)


class SchoolContentTests(unittest.TestCase):
    def test_every_floor_has_three_names_not_used_by_another_floor(self):
        names = [name for floor in range(1, 101) for name in monster_names_for_floor(floor)]
        self.assertEqual(len(names), 300)
        self.assertEqual(len(set(names)), 300)

    def test_fixed_merchant_and_final_boss_identity(self):
        self.assertEqual(MERCHANT_NAME, "ego")
        self.assertEqual(MAJOR_BOSS_NAMES[100], "塞纳河畔的春水")
        self.assertEqual(FINAL_BOSS_ALIAS, "期末考试")
        boss = GameEngine(random.Random(1))._make_boss(100)
        self.assertEqual(boss.name, "塞纳河畔的春水")
        self.assertEqual(boss.alias, "期末考试")

    def test_ordinary_monsters_never_start_a_quiz(self):
        engine = GameEngine(random.Random(2))
        player = Player(1, "测试者", floor=71, level=20)
        player.enemy = engine._make_monster(71)
        player.enemy.hp = player.enemy.max_hp
        engine.attack(player)
        self.assertIsNone(player.pending_quiz)

    def test_small_boss_starts_exactly_one_quiz(self):
        engine = GameEngine(random.Random(3))
        player = Player(1, "测试者", floor=75, level=20)
        player.enemy = engine._make_boss(75)
        player.enemy.hp = player.enemy.max_hp * 0.49

        result = engine._maybe_start_boss_quiz(player)
        self.assertIsNotNone(result)
        self.assertIsNotNone(player.pending_quiz)
        player.pending_quiz = None
        self.assertIsNone(engine._maybe_start_boss_quiz(player))

    def test_correct_answer_hurts_boss_and_cancels_attack(self):
        engine = GameEngine(random.Random(4))
        player = Player(1, "测试者", floor=80)
        player.enemy = engine._make_boss(80)
        player.enemy.hp = player.enemy.max_hp * 0.69
        engine._maybe_start_boss_quiz(player)
        before = player.enemy.hp
        answer = int(player.pending_quiz["correct_index"])

        result = engine.answer_quiz(player, answer, now=float(player.pending_quiz["deadline"]) - 1)

        self.assertEqual(result.title, "✅ 回答正确！")
        self.assertLess(player.enemy.hp, before)
        self.assertIsNone(player.pending_quiz)

    def test_wrong_or_late_answer_grants_one_boss_attack(self):
        engine = GameEngine(random.Random(5))
        player = Player(1, "测试者", floor=90, hp=999, max_hp=999)
        player.enemy = engine._make_boss(90)
        player.enemy.hp = player.enemy.max_hp * 0.69
        engine._maybe_start_boss_quiz(player)
        deadline = float(player.pending_quiz["deadline"])
        before = player.hp

        result = engine.answer_quiz(player, None, now=deadline + 1)

        self.assertIn("答题超时", result.title)
        self.assertLess(player.hp, before)
        self.assertIsNone(player.pending_quiz)

    def test_question_draw_avoids_recent_keys_and_shuffles_options(self):
        pool = [item for item in QUESTION_BANK if item.subject == "语文"]
        recent = [item.key for item in pool[:-1]]
        result = draw_question("语文", recent, random.Random(7))
        self.assertEqual(result["key"], pool[-1].key)
        self.assertEqual(len(result["options"]), 4)
        self.assertEqual(result["options"][result["correct_index"]], result["answer"])

    def test_final_boss_cannot_be_defeated_before_three_subject_questions(self):
        engine = GameEngine(random.Random(8))
        player = Player(1, "高攻击测试者", floor=100, level=500)
        player.enemy = engine._make_boss(100)
        subjects = []

        for _ in range(3):
            engine.attack(player)
            self.assertIsNotNone(player.pending_quiz)
            subjects.append(player.pending_quiz["subject"])
            answer = int(player.pending_quiz["correct_index"])
            engine.answer_quiz(player, answer, now=float(player.pending_quiz["deadline"]) - 1)

        self.assertEqual(subjects, ["英语", "语文", "数学"])
        self.assertIsNotNone(player.enemy)


if __name__ == "__main__":
    unittest.main()

