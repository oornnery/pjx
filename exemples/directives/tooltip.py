from pjx import directive


@directive("tooltip")
def tooltip_directive(element, value, ctx):
    element.attrs["data-tooltip"] = value
    element.attrs["x-data"] = "{ open: false }"
    element.attrs["x-on:mouseenter"] = "open = true"
    element.attrs["x-on:mouseleave"] = "open = false"
    return element
