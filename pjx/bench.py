"""Bench: compare Jinja2 vs MiniJinja rendering performance.

Compiles all .pjx files, then renders each template with both engines,
measuring parse+compile time and render time separately.

With ``--bundle``, page templates are compiled with all component macros
inlined, removing Python callback overhead from MiniJinja.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .compiler import compile_pjx
from .parser import parse


@dataclass(slots=True)
class TemplateTimings:
    path: str
    compile_us: float
    jinja2_render_us: float
    minijinja_render_us: float
    speedup: float  # jinja2 / minijinja
    bundled: bool = False


@dataclass(slots=True)
class BenchReport:
    templates: list[TemplateTimings] = field(default_factory=list)
    total_jinja2_us: float = 0.0
    total_minijinja_us: float = 0.0
    total_compile_us: float = 0.0
    iterations: int = 1
    overall_speedup: float = 0.0
    bundle: bool = False


def run_bench(
    project: Any,
    *,
    iterations: int = 100,
    warmup: int = 5,
    bundle: bool = False,
) -> BenchReport:
    """Benchmark Jinja2 vs MiniJinja on all project templates."""
    from jinja2 import Environment as Jinja2Env
    from jinja2 import StrictUndefined

    try:
        import minijinja
    except ImportError:
        raise ImportError(
            "minijinja is required for benchmarks. "
            "Install with: pip install pjx[minijinja]"
        )

    # Set up bundler if needed
    resolver = None
    if bundle:
        from .compile import _ImportResolver
        resolver = _ImportResolver(project.catalog)

    # Collect templates
    templates: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for template_root in project.catalog.template_roots:
        for pjx_file in sorted(template_root.rglob("*.pjx")):
            if not pjx_file.is_file():
                continue
            resolved = str(pjx_file.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            relative = str(pjx_file.relative_to(template_root))
            source = pjx_file.read_text(encoding="utf-8")
            templates.append((relative, resolved, source))

    report = BenchReport(iterations=iterations, bundle=bundle)

    for display_path, source_path, source in templates:
        # Phase 1: Compile
        t0 = time.perf_counter_ns()
        ast = parse(source, filename=source_path)

        is_bundled = False
        if bundle and not ast.is_multi_component and ast.imports:
            from .compile import _compile_bundled
            jinja_source, _ = _compile_bundled(ast, source_path, resolver)
            is_bundled = True
        else:
            jinja_source = compile_pjx(ast, filename=source_path)

        compile_ns = time.perf_counter_ns() - t0

        ctx = _build_dummy_context(ast, bundled=is_bundled)

        # Phase 2a: Jinja2
        j2_env = Jinja2Env(autoescape=True, undefined=StrictUndefined)
        j2_template = j2_env.from_string(jinja_source)

        for _ in range(warmup):
            try:
                j2_template.render(**ctx)
            except Exception:
                break

        t0 = time.perf_counter_ns()
        j2_ok = True
        for _ in range(iterations):
            try:
                j2_template.render(**ctx)
            except Exception:
                j2_ok = False
                break
        j2_ns = time.perf_counter_ns() - t0
        j2_count = iterations if j2_ok else 1

        # Phase 2b: MiniJinja
        mj_env = minijinja.Environment()
        mj_env.auto_escape_callback = lambda _: True
        template_key = f"bench_{display_path}"
        mj_env.add_template(template_key, jinja_source)

        for _ in range(warmup):
            try:
                mj_env.render_template(template_key, **ctx)
            except Exception:
                break

        t0 = time.perf_counter_ns()
        mj_ok = True
        for _ in range(iterations):
            try:
                mj_env.render_template(template_key, **ctx)
            except Exception:
                mj_ok = False
                break
        mj_ns = time.perf_counter_ns() - t0
        mj_count = iterations if mj_ok else 1

        j2_avg_us = (j2_ns / j2_count) / 1000
        mj_avg_us = (mj_ns / mj_count) / 1000
        compile_us = compile_ns / 1000
        speedup = j2_avg_us / mj_avg_us if mj_avg_us > 0 else 0

        timing = TemplateTimings(
            path=display_path,
            compile_us=compile_us,
            jinja2_render_us=j2_avg_us,
            minijinja_render_us=mj_avg_us,
            speedup=speedup,
            bundled=is_bundled,
        )
        report.templates.append(timing)
        report.total_jinja2_us += j2_avg_us
        report.total_minijinja_us += mj_avg_us
        report.total_compile_us += compile_us

    if report.total_minijinja_us > 0:
        report.overall_speedup = report.total_jinja2_us / report.total_minijinja_us

    return report


def render_bench_report(report: BenchReport) -> str:
    mode = "bundled" if report.bundle else "unbundled"
    lines = [
        f"PJX Benchmark — Jinja2 vs MiniJinja (Rust) [{mode}]",
        f"Iterations per template: {report.iterations}",
        "",
    ]

    lines.append(
        f"{'Template':<45} {'Compile':>10} {'Jinja2':>12} {'MiniJinja':>12} {'Speedup':>8}"
    )
    lines.append("-" * 91)

    for t in sorted(report.templates, key=lambda x: -x.speedup):
        tag = " *" if t.bundled else ""
        lines.append(
            f"{t.path + tag:<45} {t.compile_us:>9.0f}µs {t.jinja2_render_us:>10.1f}µs "
            f"{t.minijinja_render_us:>10.1f}µs {t.speedup:>7.2f}x"
        )

    lines.append("-" * 91)
    lines.append(
        f"{'TOTAL':<45} {report.total_compile_us:>9.0f}µs "
        f"{report.total_jinja2_us:>10.1f}µs {report.total_minijinja_us:>10.1f}µs "
        f"{report.overall_speedup:>7.2f}x"
    )

    lines.append("")
    if report.overall_speedup > 1:
        lines.append(
            f"MiniJinja is {report.overall_speedup:.1f}x faster than Jinja2 overall"
        )
    elif report.overall_speedup > 0:
        lines.append(
            f"Jinja2 is {1/report.overall_speedup:.1f}x faster than MiniJinja overall"
        )

    if report.bundle:
        bundled = [t for t in report.templates if t.bundled]
        if bundled:
            lines.append("")
            lines.append("* = bundled (all component macros inlined, no Python callbacks)")

    # Show breakdown if there's a mix
    faster = [t for t in report.templates if t.speedup >= 1.0]
    slower = [t for t in report.templates if t.speedup < 1.0]
    if faster and slower:
        f_j2 = sum(t.jinja2_render_us for t in faster)
        f_mj = sum(t.minijinja_render_us for t in faster)
        s_j2 = sum(t.jinja2_render_us for t in slower)
        s_mj = sum(t.minijinja_render_us for t in slower)
        lines.append("")
        lines.append(
            f"  MiniJinja wins: {f_j2/f_mj:.1f}x faster ({f_j2:.0f}µs vs {f_mj:.0f}µs)"
        )
        lines.append(
            f"  Jinja2 wins: {s_mj/s_j2:.1f}x faster ({s_j2:.0f}µs vs {s_mj:.0f}µs)"
        )

    return "\n".join(lines)


def _build_dummy_context(ast: Any, *, bundled: bool = False) -> dict[str, Any]:
    """Build a minimal context dict so templates can render without errors."""
    ctx: dict[str, Any] = {
        "__pjx_id": "bench-id-000",
        "__pjx_event_url": lambda event, **params: f"/__pjx_event/{event}",
        "pjx_assets": lambda: "",
        "request": None,
    }
    # Only add render_component stub if not bundled
    if not bundled:
        ctx["__pjx_render_component"] = lambda *a, **kw: ""

    # Add prop defaults
    if ast.props:
        for p in ast.props.props:
            if p.default_expr is not None:
                try:
                    ctx[p.name] = eval(p.default_expr, {"__builtins__": {}}, {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict})  # noqa: S307
                except Exception:
                    ctx[p.name] = ""
            elif p.name not in ctx:
                ctx[p.name] = ""

    # Slot variables
    for s in ast.slots:
        ctx[f"__slot_{s.name}"] = ""

    return ctx
