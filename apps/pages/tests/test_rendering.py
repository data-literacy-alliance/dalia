import re
import subprocess
from unittest import mock

import pytest
from pages import rendering
from pages.rendering import RenderError, render_markdown, run_pandoc

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "pandoc"], capture_output=True).returncode != 0,
    reason="pandoc not installed",
)

FORBIDDEN_ATTR = re.compile(r"<[^>]*\s(on[a-z]+|style)\s*=", re.I)  # inside a tag only


def test_external_link_attributes():
    html = render_markdown("[x](https://example.org/p)")
    assert 'target="_blank"' in html
    assert 'rel="nofollow noopener noreferrer"' in html
    assert 'class="external-link no-image"' in html


@pytest.mark.parametrize(
    "target", ["/en/home", "https://dalia.education/en", "https://www.dalia.education/de"]
)
def test_internal_links_untouched(target):
    html = render_markdown(f"[x]({target})")
    assert f'<a href="{target}">x</a>' in html


def test_fragment_link_gets_id_prefix_matching_headers():
    assert '<a href="#c-top">x</a>' in render_markdown("[x](#top)")


def test_userinfo_trick_is_external():
    html = render_markdown("[x](https://dalia.education@evil.example/)")
    assert 'target="_blank"' in html


def test_figure_and_caption_classes():
    html = render_markdown("![Cap](/media/website/2026/a.png)")
    assert '<figure class="image-caption">' in html
    assert 'class="caption"' in html
    assert 'title="Cap"' in html


@pytest.mark.parametrize("src", ["/media/website/2026/a.png", "/static/website/images/a.png"])
def test_allowed_image_src_kept(src):
    assert f'src="{src}"' in render_markdown(f"![alt]({src})")


@pytest.mark.parametrize(
    "src", ["https://x/y.png", "//x/y.png", "data:image/png;base64,AAAA", "img.png", "/other/a.png"]
)
def test_other_image_src_dropped_alt_kept(src):
    html = render_markdown(f"text ![my alt]({src}) end")
    assert "<img" not in html
    assert "my alt" in html


def test_mailto_and_bare_email():
    html = render_markdown("write to me@example.org, please")
    assert '<a href="mailto:me@example.org" class="mailto">me@example.org</a>,' in html
    assert "mailto:" in render_markdown("[mail](mailto:a@b.org)")


def test_autolink_email_not_nested():
    html = render_markdown("<a@b.org>")
    assert html.count("<a ") == 1


def test_script_escaped_not_emitted():
    html = render_markdown("<script>alert(1)</script> and <b onclick=x>y</b>")
    assert "<script" not in html
    assert "<b" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "md",
    [
        "[x](/a){onclick=alert(1)}",
        "[x]{onmouseover=alert(1)}",
        "::: {onclick=alert(1)}\ntext\n:::",
        "# h {onclick=alert(1)}",
        "![a](/media/x.png){onload=alert(1) style=color:red}",
        "`code`{onclick=alert(1)}",
        "```{onclick=alert(1)}\ncode\n```",
        '[x](/a "title"){style="x"}',
    ],
)
def test_attribute_injection_produces_no_event_or_style_attributes(md):
    assert not FORBIDDEN_ATTR.search(render_markdown(md))


@pytest.mark.parametrize(
    "target",
    [
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "java&#x09;script:alert(1)",
        " javascript:alert(1)",
        "\tjavascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "java\x7fscript:alert(1)",
        "vbscript:msgbox(1)",
        "data:text/html,<b>x</b>",
        "DaTa:text/html;base64,AAAA",
    ],
)
def test_dangerous_link_schemes_unwrapped(target):
    html = render_markdown(f"[click](<{target}>)")
    assert "<a " not in html
    assert "click" in html
    assert "script:" not in html.replace("&lt;", "").lower().split("click")[0]


def test_header_ids_prefixed():
    assert '<h2 id="c-intro">' in render_markdown("## Intro")


def test_input_too_long_raises():
    with pytest.raises(RenderError):
        render_markdown("a" * 500_001)


def test_empty_input_renders_empty():
    assert render_markdown("   ") == ""


# --- mocked failure paths ---------------------------------------------------


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["pandoc"], returncode, stdout, stderr)


def test_pandoc_missing_raises():
    with mock.patch.object(rendering.subprocess, "run", side_effect=FileNotFoundError):
        with pytest.raises(RenderError):
            run_pandoc(["-t", "html5"], stdin="x")


def test_timeout_raises():
    with mock.patch.object(
        rendering.subprocess, "run", side_effect=subprocess.TimeoutExpired("pandoc", 20)
    ):
        with pytest.raises(RenderError):
            run_pandoc([], stdin="x")


def test_nonzero_exit_uses_first_stderr_line_truncated():
    err = "[WARNING] ignore me\n" + "E" * 400 + "\nsecond"
    with mock.patch.object(rendering.subprocess, "run", return_value=_proc(1, stderr=err)):
        with pytest.raises(RenderError) as exc:
            run_pandoc([], stdin="x")
    assert str(exc.value) == "E" * 300


def test_command_shape():
    with mock.patch.object(rendering.subprocess, "run", return_value=_proc(0, "<p>x</p>")) as run:
        assert run_pandoc(["-t", "html5"], stdin="x") == "<p>x</p>"
    args, kwargs = run.call_args
    assert args[0] == ["pandoc", "-t", "html5", "+RTS", "-M512m", "-RTS"]
    assert kwargs["shell"] is False and kwargs["timeout"] == 20 and kwargs["input"] == "x"


def test_render_uses_sandbox_and_stdin():
    render_markdown.cache_clear()
    with mock.patch.object(rendering, "run_pandoc", return_value="<p>x</p>") as run:
        render_markdown("unique text for sandbox test")
    assert "--sandbox" in run.call_args.args[0]
    assert run.call_args.kwargs["stdin"] == "unique text for sandbox test"


def test_rts_rejected_falls_back_to_setrlimit():
    rejected = _proc(1, stderr="pandoc: Most RTS options are disabled. Link with -rtsopts")
    ok = _proc(0, "<p>x</p>")
    with (
        mock.patch.object(rendering, "_use_rts", True),
        mock.patch.object(rendering.subprocess, "run", side_effect=[rejected, ok, ok]) as run,
    ):
        assert run_pandoc([], stdin="x") == "<p>x</p>"
        first, second = run.call_args_list
        assert "+RTS" in first.args[0]
        assert "+RTS" not in second.args[0]
        assert second.kwargs["preexec_fn"] is rendering._limit_address_space
        assert rendering._use_rts is False  # process-wide switch
        run_pandoc([], stdin="y")
        assert "+RTS" not in run.call_args.args[0]


def test_limit_address_space_calls_setrlimit():
    with mock.patch.object(rendering.resource, "setrlimit") as srl:
        rendering._limit_address_space()
    srl.assert_called_once_with(rendering.resource.RLIMIT_AS, (1024**3, 1024**3))


def test_heap_exhaustion_is_a_render_error_and_keeps_rts():
    heap = _proc(
        251,
        stderr="pandoc: Heap exhausted;\npandoc: Current maximum heap size is 536870912 bytes "
        "(512 MB).\npandoc: Use `+RTS -M<size>' to increase it.",
    )
    with (
        mock.patch.object(rendering, "_use_rts", True),
        mock.patch.object(rendering.subprocess, "run", return_value=heap) as run,
    ):
        with pytest.raises(RenderError):
            run_pandoc([], stdin="x")
        assert run.call_count == 1  # no retry
        assert rendering._use_rts is True


@pytest.mark.parametrize(
    "message",
    [
        "pandoc: Most RTS options are disabled. Link with -rtsopts",
        "pandoc: unknown RTS option: -M512m",
    ],
)
def test_specific_rts_rejection_messages_detected(message):
    assert rendering._rts_rejected(_proc(1, stderr=message))
    assert not rendering._rts_rejected(_proc(0, stderr=message))


@pytest.mark.parametrize("target", ["/\\evil.com", "/\\/evil.com"])
def test_backslash_link_targets_are_external(target):
    html = render_markdown(f"[x]({target})")
    assert "external-link" in html and 'target="_blank"' in html


def test_backslash_normalised_in_href():
    assert 'href="//evil.com"' in render_markdown("[x](/\\evil.com)")
