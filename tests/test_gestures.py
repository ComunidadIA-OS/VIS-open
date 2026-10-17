"""Mano levantada con puntos SINTÉTICOS (sin imagen ni personas reales)."""

import pytest

from pipeline.gestures import Point, detect_raises, raised_hands


def pose(l_wrist_y=0.8, r_wrist_y=0.8, vis=1.0):
    return {
        11: Point(0.6, 0.4, vis), 12: Point(0.4, 0.4, vis),
        15: Point(0.7, l_wrist_y, vis), 16: Point(0.3, r_wrist_y, vis),
    }  # fmt: skip


def test_arms_down_is_not_raised():
    assert raised_hands(pose()) == set()


def test_wrist_above_shoulder_is_raised_per_side():
    assert raised_hands(pose(r_wrist_y=0.2)) == {"right"}
    assert raised_hands(pose(l_wrist_y=0.1, r_wrist_y=0.1)) == {"left", "right"}


def test_margin_and_visibility_and_missing_points():
    assert raised_hands(pose(r_wrist_y=0.38)) == set()  # por encima, pero dentro del margen
    assert raised_hands(pose(r_wrist_y=0.1, vis=0.2)) == set()  # poco visible
    assert raised_hands({11: Point(0.6, 0.4)}) == set()  # faltan puntos


def test_detect_sustained_raise_with_times():
    frames = [pose()] * 10 + [pose(r_wrist_y=0.1)] * 20 + [pose()] * 10  # 10 fps
    assert detect_raises(frames, fps=10) == [(1.0, 3.0)]


def test_short_raise_is_discarded_and_small_gaps_bridged():
    assert detect_raises([pose(r_wrist_y=0.1)] * 5, fps=10) == []  # 0,5 s < 1 s
    up, down = pose(r_wrist_y=0.1), pose()
    assert detect_raises([up] * 8 + [down, None] + [up] * 8, fps=10) == [(0.0, 1.8)]


def test_two_separate_raises_and_edge_cases():
    up, down = pose(r_wrist_y=0.1), pose()
    frames = [up] * 12 + [down] * 5 + [up] * 12
    assert len(detect_raises(frames, fps=10)) == 2
    assert detect_raises([], fps=10) == []
    with pytest.raises(ValueError):
        detect_raises([up], fps=0)
