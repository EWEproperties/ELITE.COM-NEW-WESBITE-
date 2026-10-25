// Home: each featured property block is a slideshow that moves to the next property every few seconds.
// Without JavaScript the first property shows on its own. Every slide is in the HTML for search engines.
const INTERVAL = 4000;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

document.querySelectorAll(".feature-slider").forEach((slider) => {
  const slides = [...slider.querySelectorAll(".slide")];
  const dots = [...slider.querySelectorAll(".slide-dots button")];
  const cards = [...slider.parentElement.querySelectorAll(".grid .card")];
  let current = 0;
  let timer = null;
  let paused = false;

  function show(i) {
    current = (i + slides.length) % slides.length;
    slides.forEach((s, k) => {
      const on = k === current;
      s.classList.toggle("is-active", on);
      s.setAttribute("aria-hidden", on ? "false" : "true");
      s.tabIndex = on ? 0 : -1;
    });
    dots.forEach((d, k) => d.setAttribute("aria-current", k === current ? "true" : "false"));
    const href = slides[current].getAttribute("href");
    cards.forEach((c) => c.classList.toggle("is-current", c.getAttribute("href") === href));
  }

  function start() {
    stop();
    if (!reduceMotion && !paused) timer = setInterval(() => show(current + 1), INTERVAL);
  }

  function stop() {
    clearInterval(timer);
    timer = null;
  }

  slider.querySelector(".slide-prev").addEventListener("click", () => { show(current - 1); start(); });
  slider.querySelector(".slide-next").addEventListener("click", () => { show(current + 1); start(); });
  dots.forEach((d, k) => d.addEventListener("click", () => { show(k); start(); }));

  // Pause while the visitor points at or tabs into the slideshow
  slider.addEventListener("mouseenter", () => { paused = true; stop(); });
  slider.addEventListener("mouseleave", () => { paused = false; start(); });
  slider.addEventListener("focusin", () => { paused = true; stop(); });
  slider.addEventListener("focusout", () => { paused = false; start(); });

  // Swipe on phones
  let x0 = null;
  slider.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  slider.addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 40) { show(current + (dx < 0 ? 1 : -1)); start(); }
    x0 = null;
  });

  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));

  slider.classList.add("is-ready");
  show(0);
  start();
});
