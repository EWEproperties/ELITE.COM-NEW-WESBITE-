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

LANG_RE = re.compile(r'<html[^>]*\blang="([a-zA-Z]{2})')
FOOTER_RE = re.compile(r'(<footer class="site-footer"[^>]*>)')
PRIVACY_RE = re.compile(r'href="((?:\.\./)*)privacy-policy(?:\.html)?"')


def block(lang, prefix):
    t = TEXT.get(lang, TEXT["en"])
    e = lambda s: html.escape(s, quote=True)
    privacy = f'<a href="{prefix}privacy-policy.html" target="_blank" rel="noopener">{e(t["privacy"])}</a>'
    consent = e(t["consent"]).replace("{privacy}", privacy)
    msgs = " ".join(f'data-{k.replace("_", "-")}="{e(t[k])}"'
                    for k in ("sending", "err_name", "err_email", "err_consent", "err_form", "err_net"))
    star = f'<em class="nl-req" title="{e(t["req"])}">*</em>'
    return f"""{START}
  <section class="nl-band" aria-labelledby="nl-h">
    <div class="container nl-inner">
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
        <div class="nl-row">
          <div class="nl-f">
            <label for="nl-name">{e(t["name"])} {star}</label>
            <input id="nl-name" name="name" autocomplete="given-name" required minlength="2" maxlength="80">
            <span class="nl-err" data-for="name" role="alert"></span>
          </div>
          <div class="nl-f">
            <label for="nl-email">{e(t["email"])} {star}</label>
            <input id="nl-email" name="email" type="email" autocomplete="email" required maxlength="160">
            <span class="nl-err" data-for="email" role="alert"></span>
          </div>
          <button class="btn btn-gold nl-btn" type="submit">{e(t["button"])}</button>
        </div>
        <label class="nl-chk" for="nl-consent">
          <input type="checkbox" id="nl-consent" name="consent" value="1" required>
          <span>{consent} {star}</span>
        </label>
        <span class="nl-err" data-for="consent" role="alert"></span>
        <span class="nl-err" data-for="form" role="alert"></span>
      </form>
      <div class="nl-ok" hidden tabindex="-1">
        <p class="nl-ok-h">{e(t["ok_title"])}</p>
        <p>{e(t["ok_text"])}</p>
      </div>
    </div>
  </section>
  <script src="{prefix}js/newsletter.js" defer></script>
{END}"""


def inject(text):
    """Return the page with the newsletter block at the top of its footer (idempotent)."""
    text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", text, flags=re.S)
    m = FOOTER_RE.search(text)
    if not m:
        return text
    lang = (LANG_RE.search(text) or [None, "en"])[1].lower()
    p = PRIVACY_RE.search(text)
    prefix = p.group(1) if p else ""
    return text[: m.end()] + "\n" + block(lang, prefix) + text[m.end():]


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out = inject(src)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(("updated " if out != src else "no footer ") + path)
