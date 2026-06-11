import socket

from tuebingen_search.desktop import SpotlightApi, free_port


def test_free_port_is_bindable():
    port = free_port()
    assert 1024 < port < 65536
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_spotlight_api_close_without_window_is_safe():
    SpotlightApi().close()


def test_spotlight_api_close_destroys_window():
    class FakeWindow:
        destroyed = False

        def destroy(self):
            self.destroyed = True

    api = SpotlightApi()
    api.window = FakeWindow()
    api.close()
    assert api.window.destroyed
