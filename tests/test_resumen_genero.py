import pytest

from dashboard.voice import with_validated_gender, without_gendered_titles


@pytest.mark.parametrize(
    "text, expected",
    [
        ("La diputada Persona 2 cuestionó al Gobierno.", "Persona 2 cuestionó al Gobierno."),
        ("La ministra Persona 3 respondió.", "Persona 3 respondió."),
        ("Luego la ministra de Hacienda Persona 7 replicó.", "Luego Persona 7 replicó."),
        ("Y el presidente del Gobierno Persona 4 cerró.", "Y Persona 4 cerró."),
        ("La señora ministra de Trabajo y Economía Social Persona 5 habló.", "Persona 5 habló."),
        ("Se habló del Gobierno y de Persona 3.", "Se habló del Gobierno y de Persona 3."),
    ],
)
def test_gendered_titles_before_a_code_are_removed(text, expected):
    assert without_gendered_titles(text) == expected


def test_title_without_code_stays_known_limit():
    assert without_gendered_titles("La ministra respondió.") == "La ministra respondió."


def test_validated_gender_only_first_time_and_only_known_voices():
    text = "Persona 2 preguntó. Persona 3 respondió y Persona 2 replicó. Persona 9 aplaudió."
    genders = {"Persona 2": "mujer", "Persona 3": "desconocido"}
    assert with_validated_gender(text, genders) == (
        "Persona 2 (mujer) preguntó. Persona 3 (género desconocido) respondió y Persona 2 "
        "replicó. Persona 9 aplaudió."
    )


def test_persona_12_is_not_persona_1():
    assert (
        with_validated_gender("Persona 12 habló.", {"Persona 1": "hombre"}) == "Persona 12 habló."
    )


def test_codes_also_cited_as_names_get_no_gender():
    from types import SimpleNamespace as NS

    voice_a = NS(speaker_id="S0", gender=NS(value="mujer"))
    voice_b = NS(speaker_id="S1", gender=NS(value="hombre"))
    events = [NS(text="Pregunta de doña Persona 1.", speaker_id="S1")]
    session = NS(timeline=NS(speakers=[voice_a, voice_b], events=events))
    import dashboard.voice as v

    original = __import__("decision.pseudonymize", fromlist=["x"]).speaker_codes
    try:
        __import__("decision.pseudonymize", fromlist=["x"]).speaker_codes = lambda tl: {
            "S0": "Persona 1",
            "S1": "Persona 2",
        }
        assert v.voice_genders(session) == {"Persona 2": "hombre"}  # Persona 1 es ambiguo
    finally:
        __import__("decision.pseudonymize", fromlist=["x"]).speaker_codes = original
