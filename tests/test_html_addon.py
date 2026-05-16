from builtin_addons.html import _toast_oob
from pathlib import Path


def test_toast_oob_escapes_message_html():
    toast = _toast_oob("Procedure '<script>alert(1)</script>' already exists.")

    assert "<script>" not in toast
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in toast


def test_toast_oob_targets_persistent_toast_container():
    toast = _toast_oob("message")

    assert 'hx-swap-oob="innerHTML:#toast"' in toast
    assert "innerHTML = ''" in toast


def test_base_template_has_toast_container_and_error_handler():
    template = Path("builtin_addons/html/templates/base.html").read_text()

    assert '<div id="toast"></div>' in template
    assert "htmx:responseError" in template
    assert "span.textContent = message" in template
