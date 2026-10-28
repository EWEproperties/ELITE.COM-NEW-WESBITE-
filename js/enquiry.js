// Enquiry forms. With a form_endpoint in site.json (for example Formspree) the form
// is posted there; without one, the visitor's email app opens with the message filled in.
document.querySelectorAll("form[data-enquiry]").forEach((form) => {
  const status = form.querySelector(".form-status");
  const button = form.querySelector('button[type="submit"]');

  function say(msg, ok) {
    status.textContent = msg;
    status.hidden = false;
    status.classList.toggle("is-error", !ok);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    if (data.get("_gotcha")) return;

    if (!form.getAttribute("action")) {
      const lines = [];
      for (const [k, v] of data) {
        if (!k.startsWith("_") && k !== "message" && v) lines.push(`${k}: ${v}`);
      }
      const body = `${data.get("message") || ""}\n\n${lines.join("\n")}`;
      window.location.href = `mailto:${form.dataset.email}?subject=${encodeURIComponent(data.get("_subject"))}&body=${encodeURIComponent(body)}`;
      say(form.dataset.fallback, true);
      return;
    }

    const label = button.textContent;
    button.disabled = true;
    button.textContent = form.dataset.sending;
    data.append("page", window.location.href);
    try {
      const res = await fetch(form.action, { method: "POST", body: data, headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(res.status);
      form.reset();
      say(form.dataset.thanks, true);
    } catch {
      say(form.dataset.error, false);
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  });
});
