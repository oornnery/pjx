from pjx.core.scanner import Scanner, ScanTokenType


def test_unclosed_comment():
    source = "<!-- unclosed comment"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.COMMENT
    assert tokens[0].value == source


def test_normal_comment():
    source = "<!-- a comment -->"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.COMMENT
    assert tokens[0].value == source


def test_unclosed_tag():
    source = "<div class='foo'"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.OPEN_TAG
    assert tokens[0].tag_name == "div"


def test_self_closing_tag():
    source = "<br />"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.SELF_CLOSING_TAG
    assert tokens[0].tag_name == "br"


def test_nested_braces_in_expression():
    source = "<div class={fn({a: 1})}>"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.OPEN_TAG
    assert tokens[0].attributes[0].is_expression
    assert tokens[0].attributes[0].value == "fn({a: 1})"


def test_string_in_expression():
    source = '<a href={"/users/" ~ str(id)}>'
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    attr = tokens[0].attributes[0]
    assert attr.is_expression
    assert attr.value == '"/users/" ~ str(id)'


def test_quoted_attribute_with_special_chars():
    source = '<a href="https://example.com?a=1&b=2">link</a>'
    tokens = Scanner(source).scan()
    assert tokens[0].type == ScanTokenType.OPEN_TAG
    assert tokens[0].attributes[0].value == "https://example.com?a=1&b=2"


def test_multiple_tokens():
    source = "<h1>Hello</h1>"
    tokens = Scanner(source).scan()
    assert len(tokens) == 3
    assert tokens[0].type == ScanTokenType.OPEN_TAG
    assert tokens[0].tag_name == "h1"
    assert tokens[1].type == ScanTokenType.TEXT
    assert tokens[1].value == "Hello"
    assert tokens[2].type == ScanTokenType.CLOSE_TAG
    assert tokens[2].tag_name == "h1"


def test_namespaced_attributes():
    source = '<div htmx:post="/api" stimulus:controller="app">'
    tokens = Scanner(source).scan()
    attrs = tokens[0].attributes
    assert len(attrs) == 2
    assert attrs[0].namespace == "htmx"
    assert attrs[0].name == "htmx:post"
    assert attrs[1].namespace == "stimulus"


def test_boolean_attribute():
    source = "<input disabled>"
    tokens = Scanner(source).scan()
    assert tokens[0].attributes[0].name == "disabled"
    assert tokens[0].attributes[0].value is None


def test_line_tracking():
    source = "<div>\n  <span>text</span>\n</div>"
    tokens = Scanner(source).scan()
    assert tokens[0].line == 1
    assert tokens[0].col == 1
    # <span> is on line 2
    span_token = [t for t in tokens if t.tag_name == "span" and t.type == ScanTokenType.OPEN_TAG][0]
    assert span_token.line == 2


def test_empty_source():
    tokens = Scanner("").scan()
    assert tokens == []


def test_text_only():
    source = "just plain text"
    tokens = Scanner(source).scan()
    assert len(tokens) == 1
    assert tokens[0].type == ScanTokenType.TEXT
    assert tokens[0].value == source
