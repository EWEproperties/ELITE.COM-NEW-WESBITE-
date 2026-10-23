// Listings shown on the live home page (eliteworldestates.com), October 2026.
// Photos are copied from the live site into assets/properties/<id>.jpg.
const LIVE = "https://www.eliteworldestates.com/property-details/";

window.PROPERTIES = {
  apartments: [
    { id: "24798038", town: "Mar de Pulpí", price: 212000, type: "Apartment", image: "assets/properties/24798038.jpg" },
    { id: "23844656", town: "Villajoyosa", price: 335000, type: "Apartment", image: "assets/properties/23844656.jpg" },
    { id: "21207621", town: "Villajoyosa", price: 384000, type: "Apartment", image: "assets/properties/21207621.jpg" },
    { id: "24758318", town: "Calpe", price: 395000, type: "Apartment", image: "assets/properties/24758318.jpg" },
    { id: "21695545", town: "Villajoyosa", price: 424000, type: "Apartments & penthouses", note: "164 units · 1–3 bedrooms", image: "assets/properties/21695545.jpg" },
    { id: "19432296", town: "Cumbre del Sol", price: 473000, type: "Apartment", beds: 2, baths: 2, image: "assets/properties/19432296.jpg" },
    { id: "23935651", town: "Benidorm", price: 607000, type: "Apartment", image: "assets/properties/23935651.jpg" },
    { id: "22583636", town: "Calpe", price: 633000, type: "Apartment", image: "assets/properties/22583636.jpg" },
    { id: "19818128", town: "Benidorm", price: 1065000, type: "Apartment", image: "assets/properties/19818128.jpg" }
  ],
  villas: [
    { id: "23891053", town: "Dolores", price: 389000, type: "Villa", image: "assets/properties/23891053.jpg" },
    { id: "24765955", town: "Daya Nueva", price: 399900, type: "Villa", image: "assets/properties/24765955.jpg" },
    { id: "26052239", town: "La Finca Golf", price: 420000, type: "Villa", image: "assets/properties/26052239.jpg" },
    { id: "24623926", town: "Finestrat", price: 425000, type: "Villa", image: "assets/properties/24623926.jpg" },
    { id: "21647014", town: "Polop", price: 440000, type: "Villa", image: "assets/properties/21647014.jpg" },
    { id: "21034180", town: "La Nucía", price: 465000, type: "Villa", image: "assets/properties/21034180.jpg" },
    { id: "26157630", town: "El Campello", price: 537000, type: "Villa", image: "assets/properties/26157630.jpg" },
    { id: "24558913", town: "Finestrat", price: 610000, type: "Villa", image: "assets/properties/24558913.jpg" },
    { id: "26239846", town: "Torrevieja", price: 650000, type: "Villa", image: "assets/properties/26239846.jpg" },
    { id: "21036181", town: "Polop", price: 755000, type: "Villa", image: "assets/properties/21036181.jpg" },
    { id: "23527654", town: "Benissa", price: 890000, type: "Villa", image: "assets/properties/23527654.jpg" }
  ],
  luxury: [
    { id: "26234196", town: "Jávea", price: 1695000, type: "Luxury villa", image: "assets/properties/26234196.jpg" },
    { id: "18595762", town: "Altea", price: 2349000, type: "Luxury villa", image: "assets/properties/18595762.jpg" },
    { id: "", town: "Benitachell", price: 2350000, type: "Luxury villa" },
    { id: "23527637", town: "Benissa", price: 2450000, type: "Luxury villa", image: "assets/properties/23527637.jpg" },
    { id: "20598512", town: "Cumbre del Sol", price: 2495000, type: "Luxury villa", image: "assets/properties/20598512.jpg" },
    { id: "26232788", town: "Cumbre del Sol", price: 2800000, type: "Luxury villa", image: "assets/properties/26232788.jpg" },
    { id: "26232807", town: "Real de la Quinta", price: 5995000, type: "Luxury villa", image: "assets/properties/26232807.jpg" }
  ]
};

window.PROPERTY_URL = (p) => (p.id ? LIVE + p.id : "https://www.eliteworldestates.com/");
