/**
 * PJX Example App — custom JavaScript.
 */

// Highlight active navbar link
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  document.querySelectorAll(".navbar__links a").forEach((link) => {
    if (link.getAttribute("href") === path) {
      link.classList.add("active");
    }
  });
});

// Reset todo-add form after successful HTMX request
document.body.addEventListener("htmx:afterRequest", (evt) => {
  if (evt.detail.successful && evt.detail.elt.classList.contains("todo-add")) {
    evt.detail.elt.reset();
    evt.detail.elt.querySelector("input")?.focus();
  }
});

// Animate counter value changes
document.body.addEventListener("htmx:afterSwap", (evt) => {
  const counter = evt.detail.target.querySelector?.(".counter__value") || evt.detail.elt.querySelector?.(".counter__value");
  if (counter) {
    counter.style.transform = "scale(1.15)";
    setTimeout(() => { counter.style.transform = ""; }, 150);
  }
});

// Log HTMX events in debug mode
document.addEventListener("htmx:afterRequest", (evt) => {
  const { verb, path } = evt.detail.requestConfig;
  console.debug(`[htmx] ${verb.toUpperCase()} ${path}`, evt.detail.successful ? "OK" : "FAIL");
});
