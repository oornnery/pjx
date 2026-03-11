from pjx import PJXRouter


tooltips = PJXRouter()


@tooltips.directive("tooltip")
def tooltip_directive(element, value, ctx):
    element.attrs["data-tooltip"] = value
    element.attrs["x-data"] = "{ open: false }"
    element.attrs["x-on:mouseenter"] = "open = true"
    element.attrs["x-on:mouseleave"] = "open = false"
    element.attrs["x-bind:data-tooltip-open"] = "open ? 'true' : 'false'"
    return element


__all__ = ["tooltips"]
