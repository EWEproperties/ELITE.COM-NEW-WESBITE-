/* Newsletter sign-up in the footer. Texts come from data- attributes on the form,
   so the same file serves every language. Posts to /api/newsletter (same site). */
(function () {
  "use strict";
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  document.querySelectorAll("form.nl-form").forEach(wire);

  function wire(form) {
  var d = form.dataset;
  form.elements.t.value = String(Date.now()); // bots post instantly; the server checks the delay

  function clear() {
    form.querySelectorAll(".nl-err").forEach(function (e) { e.textContent = ""; });
    form.querySelectorAll("[aria-invalid]").forEach(function (e) { e.removeAttribute("aria-invalid"); });
    form.querySelectorAll(".nl-chk.is-bad").forEach(function (e) { e.classList.remove("is-bad"); });
  }
  function show(key, msg) {
    var slot = form.querySelector('.nl-err[data-for="' + key + '"]') || form.querySelector('.nl-err[data-for="form"]');
    slot.textContent = msg;
    var el = form.elements[key];
    if (el && el.type === "checkbox") el.closest(".nl-chk").classList.add("is-bad");
    else if (el && el.setAttribute) el.setAttribute("aria-invalid", "true");
    return el;
  }
  function check() {
    var errs = {};
    if (form.elements.name.value.trim().length < 2) errs.name = d.errName;
    if (!EMAIL_RE.test(form.elements.email.value.trim())) errs.email = d.errEmail;
    if (!form.elements.consent.checked) errs.consent = d.errConsent;
    return errs;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    clear();
    var errs = check(), first = null;
    Object.keys(errs).forEach(function (k) { var el = show(k, errs[k]); if (!first) first = el; });
    if (first) { if (first.focus) first.focus(); return; }

    var btn = form.querySelector("button[type=submit]"), label = btn.textContent;
    btn.disabled = true; btn.textContent = d.sending;
    var fd = new FormData(form);
    fd.append("source_url", location.href.split("#")[0]);
    fetch(form.getAttribute("action"), { method: "POST", body: fd, headers: { Accept: "application/json" } })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (res) {
        btn.disabled = false; btn.textContent = label;
        if (res && res.ok) {
          var ok = form.parentNode.querySelector(".nl-ok");
          form.hidden = true; ok.hidden = false; ok.focus();
          return;
        }
        var bad = (res && res.errors) || { form: d.errForm }, f = null;
        Object.keys(bad).forEach(function (k) {
          var msg = d["err" + k.charAt(0).toUpperCase() + k.slice(1)] || d.errForm;
          var el = show(k, msg); if (!f) f = el;
        });
        if (f && f.focus) f.focus();
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = label;
        show("form", d.errNet);
      });
  });
  }
})();
