// Home: the featured properties row moves one card along every few seconds.
// Visitors can also use the arrows or swipe. Every card is in the HTML for search engines.
const FEATURED_INTERVAL = 4000;

document.querySelectorAll(".fcarousel").forEach((box) => {
  const track = box.querySelector(".fcarousel-track");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let timer = null;

  function step() {
    const card = track.querySelector(".fcard");
    return card ? card.getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 0) : track.clientWidth;
  }

  function move(dir) {
    const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
    const atStart = track.scrollLeft <= 4;
    if (dir > 0 && atEnd) track.scrollTo({ left: 0 });
    else if (dir < 0 && atStart) track.scrollTo({ left: track.scrollWidth });
    else track.scrollBy({ left: dir * step() });
  }

  function start() {
    stop();
    if (!reduceMotion) timer = setInterval(() => move(1), FEATURED_INTERVAL);
  }

  function stop() {
    clearInterval(timer);
    timer = null;
  }

  box.querySelector(".fc-prev").addEventListener("click", () => { move(-1); start(); });
  box.querySelector(".fc-next").addEventListener("click", () => { move(1); start(); });
  box.addEventListener("mouseenter", stop);
  box.addEventListener("mouseleave", start);
  box.addEventListener("focusin", stop);
  box.addEventListener("focusout", start);
  track.addEventListener("touchstart", stop, { passive: true });
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));

  start();
});
