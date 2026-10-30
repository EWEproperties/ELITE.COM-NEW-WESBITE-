"""Build the legal pages: legal notice and terms of use, privacy policy, cookie policy.

Usage:
  python3 tools/build_legal.py

Writes terms-and-conditions.html, privacy-policy.html and cookie-policy.html to the site root
(the live URLs). The texts follow Spanish law (LSSI-CE, GDPR + LOPDGDD), replacing the eGO
template on the live site, which named Portuguese law and left the company details empty.
Company details are in COMPANY below: check them with the company before launch.
Update the cookie policy as soon as any analytics, chat, map or advertising tool is added.
"""
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.eliteworldestates.com"
UPDATED = "30 October 2026"
e = html.escape

# Seen on the RAICV badge of the live site; to be confirmed by the company (and the
# Registro Mercantil entry added) before launch.
COMPANY = {
    "name": "EWE PROPERTIES S.L.",
    "brand": "Elite World Estates",
    "cif": "B42681106",
    "address": "C/ Clemente Gosálvez 63/19, 03181 Torrevieja (Alicante), Spain",
    "email": "info@eliteworldestates.com",
    "phone": "+34 672 519 809",
    "raicv": "2321",
}
C = COMPANY

COMPANY_TABLE = f"""<table class="cost-table legal-table">
        <tbody>
          <tr><th scope="row">Company</th><td>{C['name']}, trading as {C['brand']}</td></tr>
          <tr><th scope="row">Tax ID (CIF)</th><td>{C['cif']}</td></tr>
          <tr><th scope="row">Registered address</th><td>{C['address']}</td></tr>
          <tr><th scope="row">Email</th><td><a href="mailto:{C['email']}">{C['email']}</a></td></tr>
          <tr><th scope="row">Phone</th><td><a href="tel:+34672519809">{C['phone']}</a></td></tr>
          <tr><th scope="row">Estate agent register</th><td>Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV), no. {C['raicv']}</td></tr>
        </tbody>
      </table>"""

PAGES = [
 {
  "page": "terms-and-conditions",
  "title": "Legal Notice and Terms of Use | Elite World Estates",
  "description": "Legal notice and terms of use of eliteworldestates.com: who runs the website, how you may use it, property information, copyright and applicable law.",
  "h1": "Legal notice and terms of use",
  "lead": "Who runs this website and the rules for using it.",
  "sections": [
   ("1. Who we are", f"""<p>This website, {SITE.replace('https://', '')}, is run by:</p>
      {COMPANY_TABLE}
      <p>This information is given under Article 10 of Spanish Law 34/2002 on information society services and electronic commerce (LSSI-CE).</p>"""),
   ("2. Using this website", """<p>By using this website you accept these terms. If you do not agree with them, please do not use the website. We may update these terms from time to time; the version published here applies from the date shown at the bottom of the page.</p>
      <p>You may use the website to find information about properties and about living and buying in Spain, and to contact us. You must not use it for anything unlawful, try to access parts of it that are not public, overload or damage it, or copy its content in bulk (for example with automated tools).</p>"""),
   ("3. Property information", """<p>We prepare the property descriptions, prices, plans and photos carefully, mostly with information supplied by the owners and developers. They are for information only and are not a contract or a binding offer. Prices, availability, sizes and specifications can change, and plans and computer images of new developments may differ from the finished home.</p>
      <p>Always ask us to confirm the details of a property before you make any decision. Our articles and guides explain general rules on tax, law and buying in Spain; they are not legal or tax advice for your own situation.</p>"""),
   ("4. Links to other websites", """<p>The website links to other sites, such as social networks, WhatsApp and official sources. We do not control those sites and are not responsible for their content or their privacy practices.</p>"""),
   ("5. Copyright", f"""<p>The texts, photos, design, logo and other content of this website belong to {C['name']} or are used with the permission of their owners. You may not copy, publish or change them without our written permission, except for personal, non-commercial use or short quotations with a link to the source. Some photos are used under Creative Commons licences; their authors are credited next to them.</p>"""),
   ("6. Liability", """<p>We work to keep the website accurate and available, but we cannot guarantee that it is always free of errors or interruptions. As far as the law allows, we are not liable for damage caused by using the website or by relying on its general information. Nothing in these terms limits your rights as a consumer.</p>"""),
   ("7. Applicable law", """<p>These terms are governed by Spanish law. Any dispute will be decided by the courts that are competent under the law; if you are a consumer, that normally means the courts of the place where you live.</p>
      <p>Questions about these terms? Write to us at <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a>.</p>"""),
  ],
 },
 {
  "page": "privacy-policy",
  "title": "Privacy Policy | Elite World Estates",
  "description": "How Elite World Estates (EWE PROPERTIES S.L.) collects and uses personal data, the legal bases, how long we keep it and how to exercise your rights.",
  "h1": "Privacy policy",
  "lead": "How we use your personal data when you contact us, buy or sell a property with us, or receive our newsletter.",
  "sections": [
   ("1. Who is responsible for your data", f"""<p>The controller of your personal data is:</p>
      {COMPANY_TABLE}
      <p>We follow the EU General Data Protection Regulation (GDPR, Regulation 2016/679) and the Spanish Organic Law 3/2018 on data protection (LOPDGDD). For any question about your data, write to <a href="mailto:{C['email']}">{C['email']}</a>.</p>"""),
   ("2. What data we use and why", """<p>We only use the data we need, for these purposes:</p>
      <table class="cost-table legal-table legal-wide">
        <thead><tr><th scope="col">Purpose</th><th scope="col">Data</th><th scope="col">Legal basis</th></tr></thead>
        <tbody>
          <tr><td>Answering your enquiry by email, phone or WhatsApp, and sending you properties that match what you ask for</td><td>Name, email, phone, the properties and budget you tell us about</td><td>Steps you ask for before a contract (Art. 6.1.b GDPR)</td></tr>
          <tr><td>Helping you buy, sell or rent a property: viewings, reservation, contracts, notary</td><td>Identity and contact details, ID or passport, NIE, address, payment details</td><td>Contract (Art. 6.1.b GDPR)</td></tr>
          <tr><td>Checks required by the anti-money-laundering law for estate agents</td><td>Identity documents, origin of funds, ownership of companies</td><td>Legal obligation (Art. 6.1.c GDPR; Spanish Law 10/2010)</td></tr>
          <tr><td>Advertising a property you ask us to sell or rent, on this website and on property portals</td><td>Details and photos of the property; your name and contact details stay with us and are not published</td><td>Contract (Art. 6.1.b GDPR)</td></tr>
          <tr><td>Our newsletter with new properties and articles</td><td>Name, email, language, interests</td><td>Your consent (Art. 6.1.a GDPR), which you can withdraw at any time</td></tr>
          <tr><td>Telling clients we have already worked with about similar properties and services</td><td>Name, email, the kind of property you were interested in</td><td>Legitimate interest (Art. 6.1.f GDPR and Art. 21.2 LSSI-CE); every email lets you say no with one click</td></tr>
          <tr><td>Job applications you send us</td><td>Your CV and the details in it</td><td>Your consent (Art. 6.1.a GDPR)</td></tr>
          <tr><td>Accounting and tax records</td><td>Invoices and payment records</td><td>Legal obligation (Art. 6.1.c GDPR)</td></tr>
          <tr><td>Keeping the website secure and working</td><td>IP address and technical data in server logs</td><td>Legitimate interest (Art. 6.1.f GDPR)</td></tr>
        </tbody>
      </table>
      <p>We do not use your data for automated decisions or profiling, and we do not sell it.</p>
      <p>We do not ask for sensitive data, such as health, religion or political opinions. Please do not send it to us; if it reaches us by mistake, we delete it.</p>"""),
   ("3. Where the data comes from", """<p>Almost always from you: when you email, call or message us, sign up for the newsletter or work with us on a purchase or sale. Sometimes we receive your details from another agent, a developer or a lawyer who is working with you on the same transaction.</p>
      <p>This website has no forms and no user accounts at the moment. Simply visiting it does not give us your name or contact details.</p>
      <p>Giving us your data is voluntary, but without your contact details we cannot answer you, and without the documents the law requires we cannot complete a purchase or sale. Please make sure the data you give us is correct and tell us when it changes. If you give us data about another person, such as your partner, please tell them first.</p>"""),
   ("4. How long we keep it", """<ul>
        <li>Enquiries: while we are helping you, and up to two years after our last contact, unless you ask us to delete them sooner.</li>
        <li>Contracts and transaction files: for the time limits of legal claims (generally five years under Spanish civil law) and six years for accounting records.</li>
        <li>Anti-money-laundering documents: ten years, as Law 10/2010 requires.</li>
        <li>Newsletter: until you unsubscribe.</li>
        <li>Job applications: one year, unless you ask us to delete them sooner.</li>
        <li>Server logs: a short time, normally a few weeks.</li>
      </ul>"""),
   ("5. Who we share it with", """<p>Only with the people and companies needed for the purposes above:</p>
      <ul>
        <li>Service providers who work for us under a data processing agreement: our property and client management system (eGO Real Estate), our newsletter service, our email provider and the company that hosts this website.</li>
        <li>Property portals where we advertise a property for its owner: only the property details and photos, never the owner's personal data.</li>
        <li>The other parties to a transaction, when you ask us to act: the seller or buyer, developers, notaries, lawyers, banks and the land registry.</li>
        <li>Public authorities, when the law requires it, such as the tax authorities or the anti-money-laundering service (SEPBLAC).</li>
      </ul>
      <p>The property photos on this website are loaded from eGO's image servers, so your browser connects to them and they see your IP address, as with any website you visit. If you write to us on WhatsApp, Meta processes the messages under its own privacy policy.</p>"""),
   ("6. Transfers outside the EU", """<p>We try to use providers in the European Economic Area. If a provider handles data outside it, we make sure the transfer is protected by an adequacy decision of the European Commission (such as the EU–US Data Privacy Framework) or by the European Commission's standard contractual clauses.</p>"""),
   ("7. Your rights", f"""<p id="rights">You can ask us at any time to:</p>
      <ul>
        <li>see the data we hold about you (access);</li>
        <li>correct it (rectification) or delete it (erasure);</li>
        <li>limit how we use it (restriction) or object to its use;</li>
        <li>receive it in a common electronic format (portability);</li>
        <li>withdraw your consent, for example to the newsletter, without affecting what we did before.</li>
      </ul>
      <p>Write to <a href="mailto:{C['email']}">{C['email']}</a> or to our address above. It is free of charge, and someone else can do it for you with your written authorisation. We may ask for proof of identity, and we reply within one month. Some data we have to keep by law even if you ask us to delete it, as explained in section 4.</p>
      <p>If you think we have not handled your data properly, you can complain to the Spanish Data Protection Agency (Agencia Española de Protección de Datos, <a href="https://www.aepd.es" target="_blank" rel="noopener">www.aepd.es</a>).</p>"""),
   ("8. Security", """<p>We protect your data with technical and organisational measures: the website uses HTTPS encryption, access to client files is limited to the staff who need it, and our providers are bound by confidentiality and security obligations.</p>"""),
   ("9. Children", """<p>Our services are for adults. We do not knowingly collect data from children under 14.</p>"""),
   ("10. Changes to this policy", """<p>We will update this policy when we change how we use data, for example if we add a contact form or website statistics. Any future form will show a short summary of this policy next to it. If a change affects you in an important way, we will also tell you directly. The date of the latest version is shown at the bottom of the page.</p>"""),
  ],
 },
 {
  "page": "cookie-policy",
  "title": "Cookie Policy | Elite World Estates",
  "description": "eliteworldestates.com does not use cookies, statistics or advertising trackers. What that means and what we will tell you if this changes.",
  "h1": "Cookie policy",
  "lead": "This website does not use cookies.",
  "sections": [
   ("1. What cookies are", """<p>Cookies are small files that a website stores in your browser, for example to remember your settings or to count visits. Similar technologies, such as local storage or tracking pixels, work in the same way.</p>"""),
   ("2. Our website does not use cookies", """<p>This website does not store cookies or similar technologies in your browser, and it does not use statistics, advertising or social media trackers. That is why you do not see a cookie banner.</p>
      <p>Our fonts are stored on our own server, so loading a page does not send your data to font services. The property photos come from the image servers of our property system (eGO Real Estate); they do not set cookies.</p>"""),
   ("3. Other websites", """<p>When you follow a link to another site, such as WhatsApp, Facebook, Instagram or YouTube, that site may use its own cookies under its own policy.</p>"""),
   ("4. If this changes", """<p>If we add website statistics, a map, a chat or any other tool that uses cookies, we will update this page with a list of the cookies, and ask for your consent before setting any cookie that is not strictly necessary, as Article 22.2 of the Spanish LSSI-CE requires.</p>
      <p>You can always delete cookies and block them in your browser settings.</p>
      <p>Questions? Write to <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a>. More about how we use personal data is in our <a href="privacy-policy.html">privacy policy</a>.</p>"""),
  ],
 },
]

LEGAL_LINKS = '<p class="footer-legal"><a href="terms-and-conditions.html">Legal notice</a> · <a href="privacy-policy.html">Privacy policy</a> · <a href="cookie-policy.html">Cookie policy</a></p>'


def build(p):
    url = f"{SITE}/{p['page']}"
    sections = "\n".join(f"""    <section class="legal-section">
      <h2>{e(h)}</h2>
      {body}
    </section>""" for h, body in p["sections"])
    toc = "\n".join(f'        <li><a href="#s{n + 1}">{e(h.split(". ", 1)[1])}</a></li>' for n, (h, _) in enumerate(p["sections"]))
    sections = sections.replace('<section class="legal-section">', "\x00")
    for n in range(len(p["sections"])):
        sections = sections.replace("\x00", f'<section class="legal-section" id="s{n + 1}">', 1)
    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(p['title'])}</title>
  <meta name="description" content="{e(p['description'])}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{url}">
  <link rel="icon" href="assets/logo.png" type="image/png">
  <link rel="stylesheet" href="css/style.css">
</head>
<body>

<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="index.html" aria-label="Elite World Estates – Home">
      <img src="assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="Main">
      <a href="index.html">Home</a>
      <a href="index.html#properties">Properties</a>
      <a href="blog.html">Blog</a>
      <a href="about-us.html">About Us</a>
      <a href="index.html#contact">Contact Us</a>
    </nav>
  </div>
</header>

<main class="legal-page">
  <div class="container legal">
    <nav class="t-crumbs legal-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> <span>/</span> {e(p['h1'])}</nav>
    <h1>{e(p['h1'])}</h1>
    <p class="lead">{e(p['lead'])}</p>
    <nav class="legal-toc" aria-label="On this page">
      <ol>
{toc}
      </ol>
    </nav>
{sections}
    <p class="legal-updated">Last updated: {UPDATED}</p>
  </div>
</main>

<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="index.html">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>Registered in the Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) no. 2321.</p>
    {LEGAL_LINKS}
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="js/main.js"></script>
</body>
</html>
"""
    open(os.path.join(ROOT, p["page"] + ".html"), "w", encoding="utf-8").write(out)
    print(p["page"] + ".html")


if __name__ == "__main__":
    for p in PAGES:
        build(p)
