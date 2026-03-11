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

  const reinitAlpine = (event) => {
    if (!window.Alpine?.initTree || !event.target) {
      return;
    }
    window.Alpine.initTree(event.target);
  };

  const boot = () => {
    configureHtmx();
    document.body.addEventListener("htmx:afterSwap", reinitAlpine);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
