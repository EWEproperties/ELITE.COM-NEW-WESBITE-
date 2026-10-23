// Listings shown on the live home page (eliteworldestates.com), October 2026.
// `image` is empty until the listing photos are added to assets/properties/.
const LIVE = "https://www.eliteworldestates.com/property-details/";

window.PROPERTIES = {
  apartments: [
    { id: "24798038", town: "Mar de Pulpí", price: 212000, type: "Apartment" },
    { id: "23844656", town: "Villajoyosa", price: 335000, type: "Apartment" },
    { id: "21207621", town: "Villajoyosa", price: 384000, type: "Apartment" },
    { id: "24758318", town: "Calpe", price: 395000, type: "Apartment" },
    { id: "21695545", town: "Villajoyosa", price: 424000, type: "Apartments & penthouses", note: "164 units · 1–3 bedrooms" },
    { id: "19432296", town: "Cumbre del Sol", price: 473000, type: "Apartment", beds: 2, baths: 2 },
    { id: "23935651", town: "Benidorm", price: 607000, type: "Apartment" },
    { id: "22583636", town: "Calpe", price: 633000, type: "Apartment" },
    { id: "19818128", town: "Benidorm", price: 1065000, type: "Apartment" }
  ],
  villas: [
    { id: "23891053", town: "Dolores", price: 389000, type: "Villa" },
    { id: "24765955", town: "Daya Nueva", price: 399900, type: "Villa" },
    { id: "26052239", town: "La Finca Golf", price: 420000, type: "Villa" },
    { id: "24623926", town: "Finestrat", price: 425000, type: "Villa" },
    { id: "21647014", town: "Polop", price: 440000, type: "Villa" },
    { id: "21034180", town: "La Nucía", price: 465000, type: "Villa" },
    { id: "26157630", town: "El Campello", price: 537000, type: "Villa" },
    { id: "24558913", town: "Finestrat", price: 610000, type: "Villa" },
    { id: "26239846", town: "Torrevieja", price: 650000, type: "Villa" },
    { id: "21036181", town: "Polop", price: 755000, type: "Villa" },
    { id: "23527654", town: "Benissa", price: 890000, type: "Villa" }
  ],
  luxury: [
    { id: "26234196", town: "Jávea", price: 1695000, type: "Luxury villa" },
    { id: "18595762", town: "Altea", price: 2349000, type: "Luxury villa" },
    { id: "", town: "Benitachell", price: 2350000, type: "Luxury villa" },
    { id: "23527637", town: "Benissa", price: 2450000, type: "Luxury villa" },
    { id: "20598512", town: "Cumbre del Sol", price: 2495000, type: "Luxury villa" },
    { id: "26232788", town: "Cumbre del Sol", price: 2800000, type: "Luxury villa" },
    { id: "", town: "Real de la Quinta", price: 5995000, type: "Luxury villa" }
  ]
};

window.PROPERTY_URL = (p) => (p.id ? LIVE + p.id : "https://www.eliteworldestates.com/");
