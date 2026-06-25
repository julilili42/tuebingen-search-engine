from helpers import make_page_load


def test_page_load_reads_saved_page_metadata(tmp_path):
    site_dir = tmp_path / "html"
    site_dir.mkdir()
    path = site_dir / "page.html"
    path.write_text("<html></html>", encoding="utf-8")

    pages_db = make_page_load(tmp_path / "pages.sqlite", {path: "text/html"})

    [page] = list(pages_db.iter_html_pages())
    same_page = pages_db.get_page_by_file_path(path)

    assert same_page == page
    assert page.title == "page"
    assert page.crawl_depth == 0
    assert page.language == "en"
    assert page.relevance == 5.0
    assert page.token_count == 100
