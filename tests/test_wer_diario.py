from evaluation.wer_diario import anchored, clean_diario, session_wer, words_without_names

DIARIO = """DIARIO DE SESIONES DEL CONGRESO DE LOS DIPUTADOS
Núm. 209 30 de septiembre de 2026 Pág. 12
La señora PRESIDENTA: Gracias, señorías. (Aplausos).
El señor GARCÍA PÉREZ: Señora ministra, el precio de la vivienda sube cada mes y las familias
no pueden pagar el alquiler ni la hipoteca. Le pregunto qué va a hacer el Gobierno con los
alquileres este año, porque la situación de los jóvenes es insostenible en todo el país.
"""


def test_clean_diario_drops_headers_labels_and_stage_directions():
    t = clean_diario(DIARIO)
    assert "PRESIDENTA" not in t and "Aplausos" not in t and "Pág" not in t
    assert "precio de la vivienda" in t


def test_names_are_dropped_on_both_sides():
    assert words_without_names("Gracias, señora García. Persona 3 habla.") == [
        "gracias", "señora", "habla",
    ]  # fmt: skip


def test_anchored_aligns_a_window_inside_the_reference():
    ref = words_without_names(clean_diario(DIARIO))
    hyp = words_without_names(
        "el precio de la vivienda sube cada mes y las familias no pueden pagar el alquiler "
        "ni la hipoteca le pregunto qué va a hacer el gobierno con los alquileres"
    )
    ref_part, hyp_part = anchored(ref, hyp)
    assert ref_part[0] == "el" and hyp_part == ref_part


def test_session_wer_returns_one_row_per_window_and_never_crashes():
    events = [{"start_s": 0.0, "text": "Gracias."}]
    rows = session_wer(DIARIO, events)
    assert len(rows) == 3 and all("error" in r or "wer" in r for r in rows)
