#!/usr/bin/env python3
"""Newsletter sign-up block for the footer of every page (EN, DE, ES, PL).

The block is added when the site is built for Cloudflare (tools/build_cloudflare.py calls
inject() on every page), so the page generators and the HTML files in the repo stay as
they are. Run it by hand to add the block to one page for a local preview:

    python3 tools/newsletter/add_newsletter.py page.html [more.html ...]

The form posts to /api/newsletter (functions/api/newsletter.js), which passes the
sign-up on to Letaido. Texts per language are in TEXT below; the language comes from
<html lang="..">. The privacy link reuses the page's own footer link, so relative
paths are always right.
"""
import html
import re
import sys

START, END = "<!-- newsletter -->", "<!-- /newsletter -->"

# Version of the consent wording; stored with every sign-up as proof of what was agreed.
CONSENT_VERSION = "2026-11-08"

TEXT = {
    "en": {
        "eyebrow": "Newsletter",
        "title": "New homes in Spain and practical buying tips, straight to your inbox",
        "intro": "Hand-picked new builds on the Costa Blanca, Costa Cálida and Costa del Sol, plus guides "
                 "from our team in Alicante. No spam, unsubscribe with one click.",
        "name": "First name", "email": "Email address", "button": "Subscribe", "sending": "Sending…",
        "consent": "I agree to receive the Elite World Estates newsletter by email. I can withdraw my "
                   "consent at any time. I have read the {privacy}.",
        "privacy": "Privacy policy",
        "req": "required",
        "ok_title": "Thank you for signing up!",
        "ok_text": "Our next newsletter will arrive in your inbox. You can unsubscribe at any time with "
                   "the link at the bottom of every email.",
        "err_name": "Please enter your first name (at least 2 letters).",
        "err_email": "Please check your email address, it looks incomplete.",
        "err_consent": "Please tick the box so we are allowed to send you the newsletter.",
        "err_form": "Something went wrong. Please try again in a moment.",
        "err_net": "We could not connect. Please check your internet connection and try again.",
    },
    "de": {
        "eyebrow": "Newsletter",
        "title": "Neue Immobilien in Spanien und praktische Kauftipps direkt in Ihr Postfach",
        "intro": "Ausgewählte Neubauten an der Costa Blanca, Costa Cálida und Costa del Sol sowie Ratgeber "
                 "von unserem Team in Alicante. Kein Spam, Abmeldung mit einem Klick.",
        "name": "Vorname", "email": "E-Mail-Adresse", "button": "Anmelden", "sending": "Wird gesendet…",
        "consent": "Ich möchte den Newsletter von Elite World Estates per E-Mail erhalten. Ich kann meine "
                   "Einwilligung jederzeit widerrufen. Ich habe die {privacy} gelesen.",
        "privacy": "Datenschutzerklärung",
        "req": "Pflichtfeld",
        "ok_title": "Vielen Dank für Ihre Anmeldung!",
        "ok_text": "Unser nächster Newsletter kommt direkt in Ihr Postfach. Abmelden können Sie sich "
                   "jederzeit über den Link am Ende jeder E-Mail.",
        "err_name": "Bitte geben Sie Ihren Vornamen ein (mindestens 2 Buchstaben).",
        "err_email": "Bitte prüfen Sie Ihre E-Mail-Adresse, sie scheint unvollständig zu sein.",
        "err_consent": "Bitte setzen Sie das Häkchen, damit wir Ihnen den Newsletter senden dürfen.",
        "err_form": "Etwas ist schiefgelaufen. Bitte versuchen Sie es gleich noch einmal.",
        "err_net": "Keine Verbindung. Bitte prüfen Sie Ihre Internetverbindung und versuchen Sie es erneut.",
    },
    "es": {
        "eyebrow": "Newsletter",
        "title": "Nuevas viviendas en España y consejos prácticos de compra, directamente en su correo",
        "intro": "Obra nueva seleccionada en la Costa Blanca, la Costa Cálida y la Costa del Sol, y guías "
                 "de nuestro equipo en Alicante. Sin spam, baja con un solo clic.",
        "name": "Nombre", "email": "Correo electrónico", "button": "Suscribirme", "sending": "Enviando…",
        "consent": "Acepto recibir la newsletter de Elite World Estates por correo electrónico. Puedo "
                   "retirar mi consentimiento en cualquier momento. He leído la {privacy}.",
        "privacy": "Política de privacidad",
        "req": "obligatorio",
        "ok_title": "¡Gracias por suscribirse!",
        "ok_text": "Recibirá nuestra próxima newsletter en su correo. Puede darse de baja en cualquier "
                   "momento con el enlace al final de cada email.",
        "err_name": "Escriba su nombre (al menos 2 letras).",
        "err_email": "Revise su correo electrónico, parece incompleto.",
        "err_consent": "Marque la casilla para que podamos enviarle la newsletter.",
        "err_form": "Algo ha fallado. Inténtelo de nuevo en un momento.",
        "err_net": "No hay conexión. Compruebe su conexión a internet e inténtelo de nuevo.",
    },
    "pl": {
        "eyebrow": "Newsletter",
        "title": "Nowe nieruchomości w Hiszpanii i praktyczna wiedza o zakupie",
        "intro": "Wybrane oferty z Costa Blanca, Costa Cálida i Costa del Sol oraz poradniki od polskiego "
                 "zespołu w Alicante. Bez spamu, rezygnacja jednym kliknięciem.",
        "name": "Imię", "email": "Adres e-mail", "button": "Zapisz się", "sending": "Wysyłanie…",
        "consent": "Wyrażam zgodę na otrzymywanie newslettera Elite World Estates na podany adres e-mail. "
                   "Zgodę mogę wycofać w każdej chwili. Zapoznałem/am się z {privacy}.",
        "privacy": "Polityką prywatności",
        "req": "wymagane",
        "ok_title": "Dziękujemy za zapis!",
        "ok_text": "Najbliższy newsletter trafi na Twoją skrzynkę. Z subskrypcji możesz zrezygnować "
                   "w każdej chwili, klikając link na końcu każdego e-maila.",
        "err_name": "Podaj imię (co najmniej 2 litery).",
        "err_email": "Sprawdź adres e-mail, wygląda na niekompletny.",
        "err_consent": "Zaznacz zgodę na newsletter, abyśmy mogli go wysyłać.",
        "err_form": "Coś poszło nie tak. Spróbuj ponownie za chwilę.",
        "err_net": "Nie udało się połączyć. Sprawdź internet i spróbuj ponownie.",
    },
}

EXTRA = {'en': {'opt': '(optional)', 'region': 'Region', 'choose': '— choose —', 'unsure': 'Not sure yet', 'phone': 'Phone', 'dial_label': 'Country code', 'consent_phone': 'I agree to be contacted by phone or WhatsApp about properties.', 'err_phone': 'Please check the phone number, use digits only, e.g. 7700 900123.', 'note': 'Data controller: EWE PROPERTIES S.L. (CIF: ESB42681106), Calle Clemente Gonsalvez 63, piso 19, 03181 Torrevieja, Spain. Details in our {privacy2}.', 'privacy2': 'Privacy policy', 'ph': '7700 900123', 'dial': '+44', 'countries': [('+44', 'United Kingdom'), ('+353', 'Ireland'), ('+34', 'Spain'), ('+49', 'Germany'), ('+31', 'Netherlands'), ('+32', 'Belgium'), ('+46', 'Sweden'), ('+47', 'Norway'), ('+45', 'Denmark'), ('+48', 'Poland'), ('+1', 'USA / Canada')], 'ok_title': 'Thank you! You are on our newsletter list.', 'ok_text': 'We will send the first newsletter with new properties to your email address.'}, 'de': {'opt': '(optional)', 'region': 'Region', 'choose': '— bitte wählen —', 'unsure': 'Noch nicht sicher', 'phone': 'Telefon', 'dial_label': 'Ländervorwahl', 'consent_phone': 'Ich bin einverstanden, telefonisch oder per WhatsApp zu Immobilien kontaktiert zu werden.', 'err_phone': 'Bitte prüfen Sie die Telefonnummer, nur Ziffern, z. B. 151 23456789.', 'note': 'Verantwortlich für die Daten: EWE PROPERTIES S.L. (CIF: ESB42681106), Calle Clemente Gonsalvez 63, piso 19, 03181 Torrevieja, Spanien. Einzelheiten in der {privacy2}.', 'privacy2': 'Datenschutzerklärung', 'ph': '151 23456789', 'dial': '+49', 'countries': [('+49', 'Deutschland'), ('+43', 'Österreich'), ('+41', 'Schweiz'), ('+34', 'Spanien'), ('+31', 'Niederlande'), ('+32', 'Belgien'), ('+44', 'Großbritannien'), ('+48', 'Polen'), ('+1', 'USA / Kanada')], 'ok_title': 'Vielen Dank! Sie sind für unseren Newsletter angemeldet.', 'ok_text': 'Den ersten Newsletter mit neuen Immobilien senden wir an Ihre E-Mail-Adresse.'}, 'es': {'opt': '(opcional)', 'region': 'Región', 'choose': '— elegir —', 'unsure': 'Aún no lo sé', 'phone': 'Teléfono', 'dial_label': 'Prefijo del país', 'consent_phone': 'Acepto que me contacten por teléfono o WhatsApp sobre inmuebles.', 'err_phone': 'Revise el número de teléfono, solo cifras, p. ej. 612 345 678.', 'note': 'Responsable de los datos: EWE PROPERTIES S.L. (CIF: ESB42681106), Calle Clemente Gonsalvez 63, piso 19, 03181 Torrevieja. Más información en la {privacy2}.', 'privacy2': 'Política de privacidad', 'ph': '612 345 678', 'dial': '+34', 'countries': [('+34', 'España'), ('+44', 'Reino Unido'), ('+49', 'Alemania'), ('+33', 'Francia'), ('+31', 'Países Bajos'), ('+32', 'Bélgica'), ('+48', 'Polonia'), ('+52', 'México'), ('+1', 'EE. UU. / Canadá')], 'ok_title': '¡Gracias! Ya está suscrito a nuestra newsletter.', 'ok_text': 'Enviaremos la primera newsletter con nuevos inmuebles a su correo electrónico.'}, 'pl': {'opt': '(opcjonalnie)', 'region': 'Region', 'choose': '— wybierz —', 'unsure': 'Jeszcze nie wiem', 'phone': 'Telefon', 'dial_label': 'Numer kierunkowy kraju', 'consent_phone': 'Wyrażam zgodę na kontakt telefoniczny lub przez WhatsApp w sprawie ofert.', 'err_phone': 'Sprawdź numer telefonu — wpisz same cyfry, np. 600 123 456.', 'note': 'Administratorem danych jest EWE PROPERTIES S.L. (CIF: ESB42681106), Calle Clemente Gonsalvez 63, piso 19, 03181 Torrevieja. Szczegóły w {privacy2}.', 'privacy2': 'Polityce prywatności', 'ph': '600 123 456', 'dial': '+48', 'countries': [('+48', 'Polska'), ('+34', 'Hiszpania'), ('+44', 'Wlk. Brytania'), ('+49', 'Niemcy'), ('+353', 'Irlandia'), ('+31', 'Holandia'), ('+32', 'Belgia'), ('+47', 'Norwegia'), ('+46', 'Szwecja'), ('+1', 'USA / Kanada')], 'ok_title': 'Dziękujemy! Zapisaliśmy Cię do newslettera.', 'ok_text': 'Pierwszy newsletter z nowymi ofertami wyślemy na podany adres e-mail.'}}
for _l, _x in EXTRA.items():
    TEXT[_l].update(_x)
TEXT["pl"]["button"] = "Zapisuję się"

LANG_RE = re.compile(r'<html[^>]*\blang="([a-zA-Z]{2})')
FOOTER_RE = re.compile(r'(<footer class="site-footer"[^>]*>)')
PRIVACY_RE = re.compile(r'href="((?:\.\./)*)privacy-policy(?:\.html)?"')


def block(lang, prefix):
    t = TEXT.get(lang, TEXT["en"])
    e = lambda s: html.escape(s, quote=True)
    pp = f"{prefix}privacy-policy.html"
    consent = e(t["consent"]).replace("{privacy}", f'<a href="{pp}" target="_blank" rel="noopener">{e(t["privacy"])}</a>')
    note = e(t["note"]).replace("{privacy2}", f'<a href="{pp}">{e(t["privacy2"])}</a>')
    msgs = " ".join(f'data-{k.replace("_", "-")}="{e(t[k])}"'
                    for k in ("sending", "err_name", "err_email", "err_consent", "err_phone", "err_form", "err_net"))
    star = '<em class="nl-req" aria-hidden="true">*</em>'
    opt = f'<small>{e(t["opt"])}</small>'
    regions = "".join(f'<option value="{e(v)}">{e(v)}</option>'
                      for v in ("Costa Blanca", "Costa Cálida", "Costa del Sol", t["unsure"]))
    dials = "".join(f'<option value="{c}"{" selected" if c == t["dial"] else ""}>{e(n)} {c}</option>'
                    for c, n in t["countries"])
    return f"""{START}
  <div class="container nl-wrap">
  <section class="nl-block" aria-labelledby="nl-h">
    <div class="nl-intro">
      <p class="eyebrow">{e(t["eyebrow"])}</p>
      <h2 id="nl-h">{e(t["title"])}</h2>
      <p class="nl-sub">{e(t["intro"])}</p>
    </div>
    <form class="nl-form" action="/api/newsletter" method="post" novalidate {msgs}>
      <input type="hidden" name="lang" value="{lang}">
      <input type="hidden" name="consent_version" value="{CONSENT_VERSION}">
      <input type="hidden" name="t" value="">
      <div class="nl-hp" aria-hidden="true"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
      <div class="nl-grid">
        <div class="nl-f">
          <label for="nl-name">{e(t["name"])} {star}</label>
          <input class="inp" id="nl-name" name="name" autocomplete="given-name" required minlength="2" maxlength="80">
          <span class="nl-err" data-for="name" role="alert"></span>
        </div>
        <div class="nl-f">
          <label for="nl-email">{e(t["email"])} {star}</label>
          <input class="inp" id="nl-email" name="email" type="email" autocomplete="email" required maxlength="160">
          <span class="nl-err" data-for="email" role="alert"></span>
        </div>
        <div class="nl-f">
          <label for="nl-region">{e(t["region"])} {opt}</label>
          <select class="inp" id="nl-region" name="region"><option value="">{e(t["choose"])}</option>{regions}</select>
        </div>
        <div class="nl-f nl-f-phone">
          <label for="nl-tel">{e(t["phone"])} {opt}</label>
          <div class="nl-tel">
            <select class="inp" name="dial" aria-label="{e(t["dial_label"])}">{dials}</select>
            <input class="inp" id="nl-tel" name="phone" type="tel" inputmode="tel" autocomplete="tel-national" placeholder="{e(t["ph"])}" maxlength="20">
          </div>
          <span class="nl-err" data-for="phone" role="alert"></span>
        </div>
        <label class="nl-chk nl-c2" for="nl-c2" hidden>
          <input type="checkbox" id="nl-c2" name="consent_phone" value="1">
          <span>{e(t["consent_phone"])}</span>
        </label>
      </div>
      <label class="nl-chk" for="nl-consent">
        <input type="checkbox" id="nl-consent" name="consent" value="1" required>
        <span>{consent} {star}</span>
      </label>
      <span class="nl-err" data-for="consent" role="alert"></span>
      <span class="nl-err" data-for="form" role="alert"></span>
      <button class="btn btn-gold nl-btn" type="submit">{e(t["button"])}</button>
      <p class="nl-note">{note}</p>
    </form>
    <div class="nl-ok" hidden tabindex="-1" role="status">
      <p class="nl-ok-h">{e(t["ok_title"])}</p>
      <p class="nl-ok-s">{e(t["ok_text"])}</p>
    </div>
  </section>
  </div>
  <script src="{prefix}js/newsletter.js" defer></script>
{END}"""


def inject(text):
    """Return the page with the newsletter block just above its footer (idempotent)."""
    text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", text, flags=re.S)
    m = FOOTER_RE.search(text)
    if not m:
        return text
    lang = (LANG_RE.search(text) or [None, "en"])[1].lower()
    p = PRIVACY_RE.search(text)
    prefix = p.group(1) if p else ""
    return text[: m.start()] + block(lang, prefix) + "\n" + text[m.start():]


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out = inject(src)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(("updated " if out != src else "no footer ") + path)
