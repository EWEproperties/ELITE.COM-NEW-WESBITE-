// Listing filters. All cards are in the page (good for search engines and for
// visitors without JavaScript); this script hides the ones that don't match,
// sorts them, and keeps the filters in the address bar so a search can be shared.
const form = document.getElementById("filters");
const grid = document.getElementById("results");
const cards = [...grid.querySelectorAll(".card")];
const countEl = form.querySelector(".results-count");
const empty = document.querySelector(".no-results");
const townSelect = form.elements.town;
const townOptions = [...townSelect.options].slice(1);

function readUrl() {
  const q = new URLSearchParams(window.location.search);
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === "checkbox") el.checked = q.getAll(el.name).includes(el.value);
    else if (q.has(el.name)) el.value = q.get(el.name);
  }
}

function writeUrl() {
  const q = new URLSearchParams();
  for (const el of form.elements) {
    if (!el.name || (el.type === "checkbox" && !el.checked)) continue;
    if (el.value && !(el.name === "sort" && el.value === "newest")) q.append(el.name, el.value);
  }
  const s = q.toString();
  history.replaceState(null, "", s ? `?${s}` : window.location.pathname);
}

function narrowTowns() {
  const area = form.elements.area.value;
  townOptions.forEach((o) => { o.hidden = !!area && o.dataset.area !== area; });
  if (townSelect.selectedOptions[0]?.hidden) townSelect.value = "";
}

function apply() {
  narrowTowns();
  const f = form.elements;
  const min = Number(f.min.value) || 0;
  const max = Number(f.max.value) || Infinity;
  const beds = Number(f.beds.value) || 0;
  const must = [...form.querySelectorAll('input[name="f"]:checked')].map((el) => el.value);
  const showSold = f.sold.checked;
  let shown = 0;

  cards.forEach((c) => {
    const d = c.dataset;
    const price = Number(d.price);
    const feats = d.features.split(" ");
    const ok =
      (!f.area.value || d.area === f.area.value) &&
      (!f.town.value || d.town === f.town.value) &&
      (!f.type.value || d.type === f.type.value) &&
      price >= min && price <= max &&
      Number(d.beds) >= beds &&
      must.every((m) => feats.includes(m)) &&
      (showSold || d.status !== "sold");
    c.hidden = !ok;
    if (ok) shown++;
  });

  const sort = f.sort.value;
  const key = {
    newest: (c) => c.dataset.date,
    price_asc: (c) => Number(c.dataset.price),
    price_desc: (c) => -Number(c.dataset.price),
    size_desc: (c) => -Number(c.dataset.size),
  }[sort];
  const sorted = [...cards].sort((a, b) => {
    const ka = key(a), kb = key(b);
    if (sort === "newest") return ka < kb ? 1 : ka > kb ? -1 : 0;
    return ka - kb;
  });
  // Sold homes always go last
  sorted.sort((a, b) => (a.dataset.status === "sold") - (b.dataset.status === "sold"));
  sorted.forEach((c) => grid.appendChild(c));

  countEl.textContent = shown === 1 ? form.dataset.one : form.dataset.many.replace("{n}", shown);
  empty.hidden = shown > 0;
  writeUrl();
}

form.addEventListener("change", apply);
form.addEventListener("submit", (e) => { e.preventDefault(); apply(); });
form.addEventListener("reset", () => setTimeout(apply));
readUrl();
apply();
