"""Une transcripción y diarización en un `AnalysisTimeline` y prepara la revisión humana.

El género de cada voz queda siempre `desconocido` aquí: lo rellenan dos anotadoras,
cada una en su propio CSV, para poder medir el acuerdo entre ellas.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    Provenance,
    ReviewRow,
    Speaker,
    write_rows,
)
from pipeline.diarize import SpeakerTurn
from pipeline.transcribe import Segment

DEFAULT_ANNOTATORS = ("anotadora_1", "anotadora_2")
FRAGMENTS_PER_SPEAKER = 3


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def assign_speaker(segment: Segment, turns: Sequence[SpeakerTurn]) -> str | None:
    """Voz con más solapamiento con el segmento; None si ninguna se solapa (tiempo sin atribuir)."""
    totals: dict[str, float] = defaultdict(float)
    for t in turns:
        totals[t.speaker_id] += _overlap(segment.start_s, segment.end_s, t.start_s, t.end_s)
    best = max(totals.items(), key=lambda kv: kv[1], default=(None, 0.0))
    return best[0] if best[1] > 0 else None


def shift_times(segments: Sequence[Segment], turns: Sequence[SpeakerTurn], offset_s: float):
    """Pasa los tiempos de un tramo (que empiezan en 0) a tiempos del vídeo original."""
    if not offset_s:
        return list(segments), list(turns)
    return (
        [replace(s, start_s=s.start_s + offset_s, end_s=s.end_s + offset_s) for s in segments],
        [replace(t, start_s=t.start_s + offset_s, end_s=t.end_s + offset_s) for t in turns],
    )


def build_timeline(
    video_id: str,
    duration_s: float,
    segments: Sequence[Segment],
    turns: Sequence[SpeakerTurn],
) -> AnalysisTimeline:
    speech: dict[str, float] = defaultdict(float)
    for t in turns:
        speech[t.speaker_id] += min(t.end_s, duration_s) - min(t.start_s, duration_s)
    speakers = [
        Speaker(speaker_id=sid, total_speech_s=round(total, 3))
        for sid, total in sorted(speech.items())
    ]

    events = []
    for i, seg in enumerate(sorted(segments, key=lambda s: (s.start_s, s.end_s))):
        speaker_id = assign_speaker(seg, turns)
        events.append(
            AnalysisEvent(
                event_id=f"ev_{i:05d}",
                type=EventType.SPEECH,
                start_s=min(seg.start_s, duration_s),
                end_s=min(seg.end_s, duration_s),
                speaker_id=speaker_id,
                text=seg.text,
                confidence=seg.confidence,
                provenance=Provenance.AI_INFERRED,
                source=seg.source + ("+pyannote" if speaker_id else ""),
            )
        )
    return AnalysisTimeline(
        video_id=video_id, duration_s=duration_s, speakers=speakers, events=events
    )


def build_review_rows(timeline: AnalysisTimeline, annotator_id: str) -> list[ReviewRow]:
    """Una fila por voz, con el inicio de sus 3 intervenciones más largas para escucharlas."""
    by_speaker: dict[str, list[AnalysisEvent]] = defaultdict(list)
    for e in timeline.events:
        if e.speaker_id is not None:
            by_speaker[e.speaker_id].append(e)

    rows = []
    for sp in timeline.speakers:
        longest = sorted(by_speaker[sp.speaker_id], key=lambda e: e.start_s - e.end_s)
        starts = sorted(e.start_s for e in longest[:FRAGMENTS_PER_SPEAKER])
        starts += [None] * (FRAGMENTS_PER_SPEAKER - len(starts))
        rows.append(
            ReviewRow(
                video_id=timeline.video_id,
                speaker_id=sp.speaker_id,
                total_seconds=sp.total_speech_s,
                fragment_1_start_s=starts[0],
                fragment_2_start_s=starts[1],
                fragment_3_start_s=starts[2],
                annotator_id=annotator_id,
            )
        )
    return rows


def write_outputs(
    timeline: AnalysisTimeline,
    out_dir: Path,
    annotators: Sequence[str] = DEFAULT_ANNOTATORS,
) -> list[Path]:
    """Escribe `timeline.json` y un `review_<anotadora>.csv` por anotadora."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "timeline.json"
    json_path.write_text(timeline.model_dump_json(indent=2), encoding="utf-8")
    paths = [json_path]
    for annotator in annotators:
        csv_path = out_dir / f"review_{annotator}.csv"
        write_rows(build_review_rows(timeline, annotator), ReviewRow, csv_path)
        paths.append(csv_path)
    return paths
