const euro = new Intl.NumberFormat("en-GB", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

function card(p) {
  const facts = [];
  if (p.beds) facts.push(`${p.beds} bed`);
  if (p.baths) facts.push(`${p.baths} bath`);
  if (p.note) facts.push(p.note);
  const photo = p.image
    ? `<img src="${p.image}" alt="${p.type} in ${p.town}" loading="lazy">`
    : `<span class="photo-placeholder">${p.town}</span>`;
  return `
    <a class="card" href="${PROPERTY_URL(p)}" target="_blank" rel="noopener">
      <div class="card-photo">${photo}<span class="badge">${p.type}</span></div>
      <div class="card-body">
        <p class="price">${euro.format(p.price)}</p>
        <h3>${p.town}</h3>
        ${facts.length ? `<p class="facts">${facts.join(" · ")}</p>` : ""}
        <span class="card-link">View property &rarr;</span>
      </div>
    </a>`;
}

document.querySelectorAll(".grid[data-group]").forEach((grid) => {
  grid.innerHTML = PROPERTIES[grid.dataset.group].map(card).join("");
});

const toggle = document.querySelector(".nav-toggle");
const nav = document.querySelector(".main-nav");
toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  toggle.setAttribute("aria-expanded", open);
});

document.getElementById("year").textContent = new Date().getFullYear();
