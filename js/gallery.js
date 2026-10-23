// Lightbox for the property photo gallery. Links still work without JavaScript.
const thumbs = [...document.querySelectorAll(".thumb-grid .thumb")];
const photos = thumbs.map((a) => ({ src: a.getAttribute("href"), alt: a.querySelector("img").alt }));
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const count = box.querySelector(".lb-count");
let current = 0;

function show(i) {
  current = (i + photos.length) % photos.length;
  boxImg.src = photos[current].src;
  boxImg.alt = photos[current].alt;
  count.textContent = `${current + 1} / ${photos.length}`;
  box.hidden = false;
  document.body.style.overflow = "hidden";
}

function close() {
  box.hidden = true;
  document.body.style.overflow = "";
}

document.querySelectorAll(".thumb, .gallery-all").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    show(Number(el.dataset.i));
  });
});
box.querySelector(".lb-close").addEventListener("click", close);
box.querySelector(".lb-prev").addEventListener("click", () => show(current - 1));
box.querySelector(".lb-next").addEventListener("click", () => show(current + 1));
box.addEventListener("click", (e) => { if (e.target === box) close(); });
document.addEventListener("keydown", (e) => {
  if (box.hidden) return;
  if (e.key === "Escape") close();
  if (e.key === "ArrowLeft") show(current - 1);
  if (e.key === "ArrowRight") show(current + 1);
});
