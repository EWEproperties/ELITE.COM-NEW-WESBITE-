// Property gallery: "View all" opens every photo on one scrolling page,
// and any photo opens full screen. Without JavaScript each photo link still opens the image.
const allView = document.querySelector(".all-photos");
const photos = [...allView.querySelectorAll(".photo")].map((a) => ({ src: a.getAttribute("href"), alt: a.querySelector("img").alt }));
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const count = box.querySelector(".lb-count");
let current = 0;

function lockScroll(lock) {
  document.body.style.overflow = lock ? "hidden" : "";
}

function openAll(scrollTo) {
  allView.hidden = false;
  lockScroll(true);
  const target = scrollTo != null ? allView.querySelector(`.photo[data-i="${scrollTo}"]`) : null;
  if (target) target.scrollIntoView({ block: "center" });
  else allView.scrollTop = 0;
}

function closeAll() {
  allView.hidden = true;
  lockScroll(false);
}

function show(i) {
  current = (i + photos.length) % photos.length;
  boxImg.src = photos[current].src;
  boxImg.alt = photos[current].alt;
  count.textContent = `${current + 1} / ${photos.length}`;
  box.hidden = false;
  lockScroll(true);
}

function closeBox() {
  box.hidden = true;
  if (allView.hidden) lockScroll(false);
}

// Photos at the top of the page open the all-photos page at that photo
document.querySelectorAll(".gallery .photo").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    openAll(el.dataset.i ?? null);
  });
});
// Photos inside the all-photos page open full screen
allView.querySelectorAll(".photo").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    show(Number(el.dataset.i));
  });
});
allView.querySelector(".ap-close").addEventListener("click", closeAll);
allView.querySelector(".ap-cta").addEventListener("click", closeAll);
box.querySelector(".lb-close").addEventListener("click", closeBox);
box.querySelector(".lb-prev").addEventListener("click", () => show(current - 1));
box.querySelector(".lb-next").addEventListener("click", () => show(current + 1));
box.addEventListener("click", (e) => { if (e.target === box) closeBox(); });
document.addEventListener("keydown", (e) => {
  if (!box.hidden) {
    if (e.key === "Escape") closeBox();
    if (e.key === "ArrowLeft") show(current - 1);
    if (e.key === "ArrowRight") show(current + 1);
  } else if (!allView.hidden && e.key === "Escape") {
    closeAll();
  }
});

// "Ask about this property" opens the enquiry form inside the agent box
const askBtn = document.querySelector('[aria-controls="enquiry"]');
if (askBtn) {
  askBtn.addEventListener("click", () => {
    const form = document.getElementById("enquiry");
    form.hidden = !form.hidden;
    askBtn.setAttribute("aria-expanded", String(!form.hidden));
    if (!form.hidden) form.querySelector("input").focus();
  });
}
