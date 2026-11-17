from jobmatch.ingest.clean import clean_text, detect_language


def test_clean_text_removes_html_and_extra_spaces():
    assert clean_text("<p>Hello   <b>world</b></p>") == "Hello world"


def test_clean_text_handles_empty_input():
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_detect_language_swedish():
    text = "Vi söker en utvecklare som har erfarenhet av Python och som vill arbeta med data."
    assert detect_language(text) == "sv"


def test_detect_language_english():
    text = "We are looking for a developer with experience in Python who wants to work with data."
    assert detect_language(text) == "en"