# Holt täglich die Liste der parlamentarischen Fragen (data.public.lu)
# und speichert die Fragen von Meris Sehovic als docs/froen.json.
import csv, io, json, os, unicodedata, urllib.request

URL = "https://data.public.lu/en/datasets/r/e5a821df-6b96-4da6-9fa5-ff404bc121f3"
NAME = "sehovic"

def norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()

raw = urllib.request.urlopen(URL, timeout=120).read()
try:
    text = raw.decode("utf-8-sig")
except UnicodeDecodeError:
    text = raw.decode("cp1252")
dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t")
rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
cols = rows[0].keys() if rows else []

def col(*keys):
    for c in cols:
        if all(k in norm(c) for k in keys):
            return c
    return None

c_author = col("question_authors") or col("auteur") or col("author")
c_title = col("question_title") or col("titre") or col("title")
c_num = col("question_number") or col("numero")
c_type = col("question_type") or col("type")
c_date = col("question_chd_entry_date") or col("date", "depot") or col("date")
c_rec = col("question_recipients") or col("destinataire")
c_resp = col("response_deposit_date") or col("date", "reponse")

def clean(v):
    v = (v or "").strip()
    if v.lower() in ("null", "none", "nan"):
        return ""
    return v[:10] if len(v) >= 10 and v[4:5] == "-" else v

out = []
for r in rows:
    if NAME not in norm(r.get(c_author, "")):
        continue
    out.append({
        "nummer": clean(r.get(c_num)),
        "titel": clean(r.get(c_title)),
        "typ": clean(r.get(c_type)),
        "datum": clean(r.get(c_date)),
        "aentwert": clean(r.get(c_resp)) if c_resp else "",
        "minister": clean(r.get(c_rec)) if c_rec else "",
    })

def key(q):
    d = q["datum"]
    parts = d.replace("-", "/").split("/")
    if len(parts) == 3 and len(parts[0]) == 2:
        d = f"{parts[2]}-{parts[1]}-{parts[0]}"
    return d
out.sort(key=key, reverse=True)

os.makedirs("docs", exist_ok=True)
stats = {"total": len(out), "beaentwert": sum(1 for q in out if q["aentwert"])}
json.dump({"spalten": list(cols), "stats": stats, "froen": out}, open("docs/froen.json", "w"), ensure_ascii=False, indent=1)
print(len(out), "Fragen gefunden")

# --- Kommissionen & Delegationen (data.public.lu, täglich) ---
URL_KOM = "https://data.public.lu/en/datasets/r/37638e0a-a211-401b-89df-2cc5fc627632"
try:
    rawk = urllib.request.urlopen(URL_KOM, timeout=120).read()
    try:
        tk = rawk.decode("utf-8-sig")
    except UnicodeDecodeError:
        tk = rawk.decode("cp1252")
    dk = csv.Sniffer().sniff(tk[:5000], delimiters=",;\t")
    import datetime
    heute = datetime.date.today().isoformat()
    kom = []
    for r in csv.DictReader(io.StringIO(tk), dialect=dk):
        if NAME not in norm(" ".join(str(v) for v in r.values())):
            continue
        g = lambda *ks: next((clean(r.get(k)) for k in ks if clean(r.get(k))), "")
        ende = g("rol_date_fin", "end_date")
        if ende and ende[:10] < heute:
            continue
        if g("grp_date_fin", "institution_end_date") and g("grp_date_fin", "institution_end_date")[:10] < heute:
            continue
        name = g("grp_titre", "institution")
        if "Toutes les Commissions" in name:
            continue
        kom.append({
            "id": g("grp_id"),
            "typ": g("grp_type_nom", "institution_type"),
            "name": name,
            "volet": g("rol_volet", "role_section"),
            "roll": g("rol_intitule", "role"),
            "zenter": g("rol_date_debut", "start_date"),
        })
    seen = set(); uniq = []
    for k in kom:
        key = (k["name"], k["roll"], k["volet"])
        if key not in seen:
            seen.add(key); uniq.append(k)
    data = json.load(open("docs/froen.json"))
    data["kommissiounen"] = uniq
    json.dump(data, open("docs/froen.json", "w"), ensure_ascii=False, indent=1)
    print(len(uniq), "Kommissionen gefunden")
    if len(uniq) < 3:
        print("Spalten:", dk and tk.splitlines()[0][:300])
        print("Treffer im Rohtext:", [z[:250] for z in tk.splitlines() if "hovi" in z.lower()][:12])
except Exception as e:
    print("Kommissionen nicht geladen:", e)

# --- Sitzungstermine der Kommissionen (chd.lu Kalender .ics) ---
# Weitere Kommissionen: Nummer aus dem Link "Réunions .ics" (…/icscalendar/NUMMER) hier eintragen.
# Kommissionsseiten auf chd.lu (Nummer aus …/en/commission/NUMMER). Der Job holt Name und Kalender selbst.
KOM_SEITEN = [755, 754, 745, 751, 742, 765, 750]
ICS_IDS = [755]
UA = {"User-Agent": "Mozilla/5.0 (meris-sehovic.eu Webseit)"}
import re, html as _html
NAMEN = {}
for sid in KOM_SEITEN:
    try:
        seite = urllib.request.urlopen(urllib.request.Request("https://www.chd.lu/en/commission/%d" % sid, headers=UA), timeout=60).read().decode("utf-8", "replace")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", seite, re.S) or re.search(r"<title>(.*?)</title>", seite, re.S)
        name = _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).split("|")[0].strip() if m else ""
        for ics in re.findall(r"icscalendar/(\d+)", seite):
            ics = int(ics)
            if ics not in ICS_IDS:
                ICS_IDS.append(ics)
            NAMEN[ics] = (name, "https://www.chd.lu/en/commission/%d" % sid)
        print("Kommissionsseite", sid, ":", name or "ohne Namen", "→ Kalender", re.findall(r"icscalendar/(\d+)", seite)[:1])
    except Exception as e:
        print("Kommissionsseite", sid, "nicht geladen:", e)
try:
    import datetime
    jetzt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M")
    sitz = []
    for nr in ICS_IDS:
        try:
            req = urllib.request.Request("https://www.chd.lu/en/icscalendar/%d" % nr,
                                         headers=UA)
            ics = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            print("Kalender", nr, "nicht geladen:", e)
            continue
        ics = ics.replace("\r\n ", "").replace("\n ", "")  # Zeilenumbrüche (folding) auflösen
        kal = ""
        for z in ics.splitlines():
            if z.startswith("X-WR-CALNAME"):
                kal = z.split(":", 1)[1].strip()
        for blk in ics.split("BEGIN:VEVENT")[1:]:
            ev = {}
            for z in blk.splitlines():
                if ":" in z:
                    k, v = z.split(":", 1)
                    ev[k.split(";")[0]] = v.replace(r"\,", ",").replace(r"\n", " ").replace(r"\;", ";").strip()
            start = ev.get("DTSTART", "")
            if start[:8] < jetzt[:8]:
                continue
            sitz.append({
                "kommissioun": NAMEN.get(nr, ("",))[0] or kal or ev.get("SUMMARY", ""),
                "titel": ev.get("SUMMARY", ""),
                "start": start,
                "uert": ev.get("LOCATION", ""),
                "link": ev.get("URL") or NAMEN.get(nr, ("", "https://www.chd.lu/en/direct"))[1],
            })
    sitz.sort(key=lambda s: s["start"])
    data = json.load(open("docs/froen.json"))
    data["sitzungen"] = sitz[:8]
    json.dump(data, open("docs/froen.json", "w"), ensure_ascii=False, indent=1)
    print(len(sitz), "anstehende Sitzungen gefunden")
except Exception as e:
    print("Sitzungen nicht geladen:", e)

# --- Test: Abstimmungen im Plenum (nur Protokoll, noch nichts auf der Webseite) ---
try:
    rv = urllib.request.urlopen("https://download.data.public.lu/resources/liste-des-votes-en-seances-plenieres/20261018-033013/109-votes.csv", timeout=180).read()
    try:
        tv = rv.decode("utf-8-sig")
    except UnicodeDecodeError:
        tv = rv.decode("cp1252")
    dv = csv.Sniffer().sniff(tv[:5000], delimiters=",;\t")
    rows = list(csv.DictReader(io.StringIO(tv), dialect=dv))
    print("Abstimmungen Spalten:", list(rows[0].keys()) if rows else "-")
    daten = sorted({clean(r.get("meeting_date")) for r in rows if clean(r.get("meeting_date"))})
    meine = [r for r in rows if NAME in norm(" ".join(str(v) for v in r.values()))]
    print("Abstimmungen gesamt:", len(rows), "| Zeitraum:", daten[:1], "bis", daten[-1:], "| davon Meris:", len(meine))
    print("Letzte 3 von Meris:", [(clean(r.get("meeting_date")), (r.get("vote_name") or "")[:80], r.get("vote_result")) for r in sorted(meine, key=lambda r: clean(r.get("meeting_date")))[-3:]])
except Exception as e:
    print("Abstimmungen nicht geladen:", e)

# --- Abstimmungen im Plenum für die Webseite ---
# Begründungen ("Firwat") pflegt Meris in firwat.csv (Spalten: datum;titel_anfang;text).
try:
    from collections import Counter, defaultdict
    total = defaultdict(Counter)
    for r in rows:
        k = (clean(r.get("meeting_date")), (r.get("vote_name") or "").strip())
        total[k][(r.get("vote_result") or "").strip()] += 1
    firwat = []
    if os.path.exists("firwat.csv"):
        for z in csv.reader(open("firwat.csv", encoding="utf-8-sig"), delimiter=";"):
            if len(z) >= 3 and z[0].strip() and not z[0].startswith(("datum", "#")):
                firwat.append((z[0].strip(), norm(z[1].strip()), z[2].strip()))
    ab = []
    for r in meine:
        d = clean(r.get("meeting_date")); t = (r.get("vote_name") or "").strip()
        c = total[(d, t)]
        txt = next((f[2] for f in firwat if f[0] == d and f[1] and f[1] in norm(t)), "")
        ab.append({"datum": d, "titel": t, "typ": clean(r.get("vote_type")),
                   "votum": (r.get("vote_result") or "").strip(),
                   "jo": c.get("Oui", 0), "nee": c.get("Non", 0), "enth": c.get("Abstention", 0),
                   "firwat": txt})
    ab.sort(key=lambda a: a["datum"], reverse=True)
    data = json.load(open("docs/froen.json"))
    data["abstimmungen"] = ab[:30]
    json.dump(data, open("docs/froen.json", "w"), ensure_ascii=False, indent=1)
    print(len(ab), "Abstimmungen von Meris gespeichert")
except Exception as e:
    print("Abstimmungen nicht gespeichert:", e)
