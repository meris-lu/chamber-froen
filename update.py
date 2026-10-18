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
