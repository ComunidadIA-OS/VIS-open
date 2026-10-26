import pytest

from dashboard.voice import without_gendered_titles


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
