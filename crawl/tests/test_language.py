from tuebingen_crawler.language import is_english

ENGLISH_TEXT = """
Tübingen is a traditional university town in central Baden-Württemberg.
It is situated on a ridge between the Neckar and Ammer rivers, and the
town has been home to one of the oldest universities in Germany since
1477. About one in three people living in the town is a student, which
gives the city a young and lively atmosphere throughout the year.
"""

GERMAN_TEXT = """
Tübingen ist eine Universitätsstadt im Zentrum von Baden-Württemberg.
Die Stadt liegt am Neckar und ist seit 1477 Sitz einer der ältesten
Universitäten in Deutschland. Etwa ein Drittel der Einwohner sind
Studierende, was der Stadt eine junge Atmosphäre verleiht und das
Stadtbild bis heute stark prägt, wie man überall sehen kann.
"""


def test_accepts_english_text():
    assert is_english(ENGLISH_TEXT)


def test_rejects_german_text():
    assert not is_english(GERMAN_TEXT)


def test_rejects_german_text_with_misleading_lang_attribute():
    assert not is_english(GERMAN_TEXT, lang_attribute="en")


def test_short_text_falls_back_to_lang_attribute():
    assert is_english("Welcome to the castle", lang_attribute="en-GB")
    assert not is_english("Welcome to the castle", lang_attribute="de")
    assert not is_english("Welcome to the castle")
