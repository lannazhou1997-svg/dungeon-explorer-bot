from school_dungeon.runtime import floor_scene_filename


def test_every_floor_has_a_unique_scene_filename() -> None:
    filenames = [floor_scene_filename(floor) for floor in range(1, 101)]

    assert len(set(filenames)) == 100
    assert filenames[0] == "floor-001.webp"
    assert filenames[-1] == "floor-100.webp"


def test_floor_scene_filename_clamps_out_of_range_values() -> None:
    assert floor_scene_filename(0) == "floor-001.webp"
    assert floor_scene_filename(101) == "floor-100.webp"

