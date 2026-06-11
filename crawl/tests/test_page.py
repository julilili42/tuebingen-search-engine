from tuebingen_crawler.page import parse_page

HTML = b"""
<html lang="en-US">
<head>
  <title>Castle Hohent\xc3\xbcbingen</title>
  <meta name="description" content="A guide to the castle.">
  <script>var ignored = "script text";</script>
</head>
<body>
  <p>The castle sits above the old town.</p>
  <a href="/en/museum">Museum</a>
  <a href="https://example.com/tickets#buy">Tickets</a>
  <a name="anchor-without-href">no link</a>
  <style>.ignored { color: red; }</style>
</body>
</html>
"""


def test_parse_page_extracts_everything():
    page = parse_page(HTML)

    assert page.title == "Castle Hohentübingen"
    assert page.description == "A guide to the castle."
    assert page.lang == "en-us"
    assert page.links == ["/en/museum", "https://example.com/tickets#buy"]
    assert "castle sits above" in page.text


def test_parse_page_skips_script_and_style_text():
    page = parse_page(HTML)
    assert "ignored" not in page.text
    assert "script text" not in page.text


def test_parse_page_handles_broken_bytes():
    page = parse_page(b"<html><body><p>ok\xff</p>")
    assert "ok" in page.text
