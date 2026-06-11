from tuebingen_search.html import extract_page, is_html_file


def write_html(tmp_path, body: str):
    path = tmp_path / "page.html"
    path.write_text(body, encoding="utf-8")
    return path


def test_extract_page_title_and_text(tmp_path):
    path = write_html(
        tmp_path,
        "<html><head><title>Market Square</title></head>"
        "<body><h1>Market</h1><p>Weekly market on the square.</p></body></html>",
    )
    page = extract_page(path)
    assert page.title == "Market Square"
    assert "Weekly market" in page.text
    assert "Market" in page.text


def test_extract_page_skips_non_content_tags(tmp_path):
    path = write_html(
        tmp_path,
        "<html><body><nav>navigation junk</nav><script>var x;</script>"
        "<p>real content</p></body></html>",
    )
    page = extract_page(path)
    assert "navigation junk" not in page.text
    assert "var x" not in page.text
    assert page.text == "real content"


def test_is_html_file(tmp_path):
    html = write_html(tmp_path, "<p>hi</p>")
    text = tmp_path / "notes.txt"
    text.write_text("hi")
    assert is_html_file(html)
    assert not is_html_file(text)
