import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_fixture_dirs():
    return [
        d
        for d in sorted(FIXTURES_DIR.iterdir())
        if d.is_dir()
        and (d / "input.jinja").exists()
        and (d / "expected.jinja").exists()
    ]


@pytest.fixture(params=get_fixture_dirs(), ids=lambda d: d.name)
def golden_fixture(request):
    fixture_dir = request.param
    return {
        "input": (fixture_dir / "input.jinja").read_text(),
        "expected": (fixture_dir / "expected.jinja").read_text(),
        "dir": fixture_dir,
    }
