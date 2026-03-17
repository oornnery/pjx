(() => {
  const configureHtmx = () => {
    if (!window.htmx) {
      return;
    }
    window.htmx.config.responseHandling = [
      { code: "204", swap: false },
      { code: "[23]..", swap: true },
      { code: "422", swap: true },
      { code: "[45]..", swap: true },
      { code: ".*", swap: true },
    ];
  };

  const reinitAfterSwap = (event) => {
    if (!event.target) return;
    // Re-initialize Alpine components in the swapped fragment
    if (window.Alpine?.initTree) {
      window.Alpine.initTree(event.target);
    }
    // Re-initialize Basecoat components in the swapped fragment
    if (window.basecoat?.init) {
      window.basecoat.init();
    }
  };

  const boot = () => {
    configureHtmx();
    document.body.addEventListener("htmx:afterSwap", reinitAfterSwap);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
