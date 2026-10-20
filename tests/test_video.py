"""Personas, seguimiento, tiempo y manos con datos SINTÉTICOS (sin imagen ni MediaPipe)."""

import pytest

from pipeline.gestures import Point
from pipeline.video import (
    Person,
    analyze_frames,
    iou,
    iter_video_frames,
    summarize,
    track_boxes,
    zone_of,
)


def person(x, wrist_y=0.8, w=0.2):
    """Persona sintética centrada en x: hombros en y=0.4, caja de ancho w."""
    pose = {
        11: Point(x + 0.02, 0.4), 12: Point(x - 0.02, 0.4),
        15: Point(x + 0.03, wrist_y), 16: Point(x - 0.03, wrist_y),
    }  # fmt: skip
    return Person(pose, (x - w / 2, 0.2, x + w / 2, 0.9))


def run(per_frame, fps=2.0):
    frames = [(i / fps, people) for i, people in enumerate(per_frame)]
    return analyze_frames(frames, lambda people: people)  # el «detector» devuelve lo dado


def test_zone_of_by_shoulder_midpoint():
    assert [zone_of(person(x).pose) for x in (0.05, 0.3, 0.6, 0.95)] == ["Z1", "Z2", "Z3", "Z4"]


def test_counts_people_and_ignores_arms_down():
    res = run([[person(0.2), person(0.6)], [person(0.2)], []])
    s = summarize(res)
    assert [r.n_people for r in res] == [2, 1, 0]
    assert s["personas_visibles_max"] == 2 and s["personas_visibles_mediana"] == 1.0
    assert s["fotogramas_sin_personas_%"] == pytest.approx(33.3)
    assert s["manos_levantadas"] == []


def test_iou_and_tracking_keeps_ids_and_separates_people():
    assert iou((0, 0, 1, 1), (0, 0, 1, 1)) == 1 and iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0
    # A (izquierda) y B (derecha) se mueven un poco; C aparece después; A se pierde 1 fotograma
    res = run(
        [
            [person(0.2), person(0.7)],
            [person(0.22), person(0.71)],
            [person(0.71)],
            [person(0.23), person(0.72), person(0.5)],
        ]
    )
    ids = track_boxes(res)
    assert ids[0] == [1, 2] and ids[1] == [1, 2] and ids[2] == [2]
    assert ids[3] == [1, 2, 3]  # A retoma su pista tras perderse un fotograma


def test_screen_time_size_and_centrality_per_track():
    res = run(
        [[person(0.5, w=0.4)]] * 4
    )  # 4 fotogramas a 0.5 s: 1.5 s entre el primero y el último
    t = summarize(res)["pistas"][0]
    assert t["tiempo_en_pantalla_s"] == 2.0 and t["centralidad_media"] == 1.0
    assert t["tamano_medio"] == pytest.approx(0.4 * 0.7, abs=1e-3)


def test_gender_only_from_audio_with_close_up_and_enough_votes():
    res = run([[person(0.5)]] * 5 + [[person(0.5), person(0.8)]] * 2)
    voice = lambda t: "mujer" if t < 3 else None  # noqa: E731  (hablan mujeres los primeros 3 s)
    s = summarize(res, voice_gender_at=voice)
    assert (
        s["pistas"][0]["genero_por_audio"] == "mujer"
    )  # 5 fotogramas en plano único, voz de mujer
    assert s["pistas"][1]["genero_por_audio"] == "desconocido"  # nunca estuvo sola en plano
    assert s["tiempo_en_pantalla_por_genero_%"]["mujer"] > 0
    assert "género sale solo del audio" in s["aviso"]


def test_no_audio_means_unknown_not_a_guess():
    s = summarize(run([[person(0.5)]] * 6))
    assert {p["genero_por_audio"] for p in s["pistas"]} == {"desconocido"}
    assert s["tiempo_en_pantalla_por_genero_%"]["desconocido"] == 100.0


def test_contradicting_votes_stay_unknown():
    res = run([[person(0.5)]] * 6)
    voice = lambda t: "mujer" if int(t * 2) % 2 else "hombre"  # noqa: E731
    assert summarize(res, voice_gender_at=voice)["pistas"][0]["genero_por_audio"] == "desconocido"


def test_sustained_raise_is_assigned_to_a_zone_not_a_person():
    seq = [[person(0.3)]] + [[person(0.3, wrist_y=0.1), person(0.8)]] * 4 + [[person(0.3)]]
    s = summarize(run(seq))
    assert s["manos_levantadas_por_zona"] == {"Z2": 2}  # ambas muñecas de esa persona
    assert "identific" in s["aviso"]


def test_short_raise_is_discarded_and_empty_video():
    seq = [[person(0.3)], [person(0.3, 0.1)], [person(0.3)], [person(0.3)]]
    assert summarize(run(seq))["manos_levantadas"] == []
    assert summarize([]) == {"n_fotogramas": 0}


def test_iter_video_frames_samples_and_reads_real_file(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    path = tmp_path / "t.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    if not writer.isOpened():
        pytest.skip("este OpenCV no puede escribir mp4")
    for _ in range(30):  # 3 s a 10 fps
        writer.write(np.zeros((48, 64, 3), dtype="uint8"))
    writer.release()
    frames = list(iter_video_frames(path, sample_fps=2))
    assert len(frames) == 6 and frames[1][0] == pytest.approx(0.5, abs=0.01)
    assert frames[0][1].shape == (48, 64, 3)
