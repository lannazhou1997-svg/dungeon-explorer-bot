from pathlib import Path

import bot as dungeon_one
from school_dungeon import runtime as school_runtime


def test_shared_tavern_lists_both_dungeons() -> None:
    selection = dungeon_one.CaveSelect()

    assert [option.value for option in selection.options] == [
        "youden_cave",
        "endless_school",
    ]


def test_school_runtime_uses_the_logged_in_bot() -> None:
    assert school_runtime.bot is dungeon_one.bot


def test_school_dungeon_has_one_scene_for_every_floor() -> None:
    floor_dir = Path(school_runtime.FLOOR_SCENE_DIR)
    expected = {
        f"floor-{floor_number:03d}.webp"
        for floor_number in range(1, 101)
    }

    assert {path.name for path in floor_dir.glob("floor-*.webp")} == expected
