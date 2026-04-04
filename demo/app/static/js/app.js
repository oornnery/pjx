// --- HTMX error handling ---

document.addEventListener("htmx:responseError", function(evt) {
  if (evt.detail.xhr.status === 422) {
    // Find the closest error container relative to the form that triggered
    var form = evt.detail.elt.closest("form");
    var errorsDiv = form
      ? form.querySelector("[id$='-errors']") || document.getElementById("form-errors")
      : document.getElementById("form-errors");
    if (errorsDiv) errorsDiv.innerHTML = evt.detail.xhr.responseText;
  }
});

document.addEventListener("htmx:afterOnLoad", function(evt) {
  if (evt.detail.xhr.status < 200 || evt.detail.xhr.status >= 300) return;

  // Create form: reset and clear errors
  if (evt.detail.elt.id === "user-form") {
    evt.detail.elt.reset();
    var errorsDiv = document.getElementById("form-errors");
    if (errorsDiv) errorsDiv.innerHTML = "";
  }

  // Edit modal: close on success
  var modal = evt.detail.elt.closest("#edit-modal");
  if (modal) modal.remove();
});

// --- Custom confirm modal (replaces browser confirm()) ---

document.addEventListener("htmx:confirm", function(evt) {
  var message = evt.detail.question;
  if (!message) return;

  evt.preventDefault();

  var modal = document.getElementById("confirm-modal");
  var msgEl = modal.querySelector("[data-modal-target='message']");
  msgEl.textContent = message;
  modal.style.display = "flex";

  // Store the event so we can issue it later
  modal._pendingEvent = evt;
});

// --- Stimulus controllers ---

var application = Stimulus.Application.start();

application.register("modal", class extends Stimulus.Controller {
  static targets = ["message"];

  confirm() {
    this.element.style.display = "none";
    var evt = this.element._pendingEvent;
    if (evt) {
      evt.detail.issueRequest(true);
      this.element._pendingEvent = null;
    }
  }

  cancel() {
    this.element.style.display = "none";
    this.element._pendingEvent = null;
  }
});

application.register("edit-modal", class extends Stimulus.Controller {
  close() {
    this.element.remove();
  }
});

application.register("dropdown", class extends Stimulus.Controller {
  static targets = ["menu"];
  toggle() { this.menuTarget.classList.toggle("hidden"); }
  close() { this.menuTarget.classList.add("hidden"); }
});

application.register("toast", class extends Stimulus.Controller {
  static values = { duration: { type: Number, default: 3000 } };
  connect() { this.timeout = setTimeout(() => this.dismiss(), this.durationValue); }
  disconnect() { clearTimeout(this.timeout); }
  dismiss() { this.element.remove(); }
});
