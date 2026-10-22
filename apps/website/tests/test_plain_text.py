from django.template import Context, Template
from website.templatetags.website_tags import plain_text


def render(html):
    tpl = Template("{% load website_tags %}{{ h|plain_text|truncatechars:12 }}")
    return tpl.render(Context({"h": html}))


def test_plain_text_strips_tags_and_decodes_entities():
    assert plain_text("<p>Tom &amp; <b>Jerry</b></p>") == "Tom & Jerry"


def test_truncation_never_cuts_an_entity():
    # decoded text is "12345678 & more text"; the cut falls right after the ampersand
    assert render("<p>12345678 &amp; more text</p>") == "12345678 &amp; …"
    assert render("<p>1234567 &amp;&amp;&amp; more</p>") == "1234567 &amp;&amp;&amp;…"


def test_output_is_escaped():
    out = render("&lt;script&gt;alert(1)&lt;/script&gt;")
    assert "<script" not in out
