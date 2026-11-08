const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".main-nav");
toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  toggle.setAttribute("aria-expanded", open);
});

document.getElementById("year").textContent = new Date().getFullYear();
