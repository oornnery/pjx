"""PJX CLI — powered by Typer."""

import typer

from pjx.cli.analyze import analyze
from pjx.cli.build import build, check, robots, sitemap
from pjx.cli.build import format_cmd as format_command
from pjx.cli.demo import demo
from pjx.cli.dev import dev, run
from pjx.cli.init import init
from pjx.cli.packages import add, remove

app = typer.Typer(
    name="pjx",
    help="PJX — the fast and powerful Python DSL for modern web templates.",
    no_args_is_help=True,
)

app.command()(init)
app.command()(demo)
app.command()(dev)
app.command()(run)
app.command()(build)
app.command()(check)
app.command(name="format")(format_command)
app.command()(analyze)
app.command()(sitemap)
app.command()(robots)
app.command()(add)
app.command()(remove)
