/**
 * POST /api/newsletter : newsletter sign-up from the footer form (Cloudflare Pages Function).
 *
 * Settings in Cloudflare Pages > Settings > Variables and Secrets / Bindings:
 *   LETAIDO_NEWSLETTER_URL  Letaido's sign-up endpoint (from Letaido)
 *   LETAIDO_API_KEY         secret key for that endpoint (Secret, never in the repo)
 *   NEWSLETTER_KV           KV namespace binding: a copy of every sign-up with the consent
 *                           record (time, wording version, page). Also the safety net when
 *                           Letaido is not reachable, so no sign-up is lost.
 * At least one of LETAIDO_NEWSLETTER_URL or NEWSLETTER_KV must be set.
 *
 * Spam protection: hidden "website" field (bots fill it) and a minimum time on the page.
 * Both fail silently (the bot sees "ok", nothing is stored).
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const LANGS = ["en", "de", "es", "pl"];
const MIN_MS = 3000;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export async function onRequestPost({ request, env }) {
  // Only our own pages may post here.
  const origin = request.headers.get("Origin");
  let foreign = false;
  try {
    foreign = !!origin && new URL(origin).host !== new URL(request.url).host;
  } catch {
    foreign = true;
  }
  if (foreign) return json({ ok: false }, 403);

  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, errors: { form: true } }, 400);
  }
  const get = (k) => String(form.get(k) || "").trim();

  const loadedAt = Number(get("t"));
  if (get("website") || (loadedAt && Date.now() - loadedAt < MIN_MS)) return json({ ok: true });

  const name = get("name").slice(0, 80);
  const email = get("email").toLowerCase().slice(0, 160);
  const errors = {};
  if (name.length < 2) errors.name = true;
  if (!EMAIL_RE.test(email)) errors.email = true;
  if (get("consent") !== "1") errors.consent = true;
  const phone = get("phone").slice(0, 20);
  if (phone && !/^[\d\s()\-./+]{5,20}$/.test(phone)) errors.phone = true;
  const dial = /^\+\d{1,4}$/.test(get("dial")) ? get("dial") : "";
  if (Object.keys(errors).length) return json({ ok: false, errors }, 422);

  const lang = LANGS.includes(get("lang")) ? get("lang") : "en";
  const signup = {
    name,
    email,
    language: lang,
    region: get("region").slice(0, 40),
    phone: phone ? `${dial} ${phone}`.trim() : "",
    consent_phone: !!phone && get("consent_phone") === "1",
    source: "eliteworldestates.com",
    source_url: get("source_url").slice(0, 500),
    consent_newsletter: true,
    consent_version: get("consent_version").slice(0, 20),
    consented_at: new Date().toISOString(),
  };

  let sent = false, stored = false;
  if (env.LETAIDO_NEWSLETTER_URL) {
    try {
      const r = await fetch(env.LETAIDO_NEWSLETTER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${env.LETAIDO_API_KEY || ""}` },
        body: JSON.stringify(signup),
      });
      sent = r.ok;
      signup.letaido_status = r.status;
    } catch {
      signup.letaido_status = "unreachable";
    }
  }
  if (env.NEWSLETTER_KV) {
    try {
      await env.NEWSLETTER_KV.put(`signup:${signup.consented_at}:${email}`, JSON.stringify(signup));
      stored = true;
    } catch {}
  }
  if (!sent && !stored) return json({ ok: false, errors: { form: true } }, 503);
  return json({ ok: true });
}

export function onRequest() {
  return json({ ok: false }, 405);
}
