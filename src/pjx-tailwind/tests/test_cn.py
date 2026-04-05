from pjx_tailwind import cn


def test_basic_merge():
    assert cn("foo", "bar") == "foo bar"


def test_filters_false():
    assert cn("base", False, "extra") == "base extra"


def test_filters_none():
    assert cn("base", None, "extra") == "base extra"


def test_filters_empty_string():
    assert cn("base", "", "extra") == "base extra"


def test_conditional_and():
    active = True
    inactive = False
    assert cn("base", active and "selected") == "base selected"
    assert cn("base", inactive and "selected") == "base"


def test_dedup():
    assert cn("foo bar", "bar baz") == "foo bar baz"


def test_empty():
    assert cn() == ""


def test_all_falsy():
    assert cn(False, None, "") == ""


def test_single():
    assert cn("only") == "only"
