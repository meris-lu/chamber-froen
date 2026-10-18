# Holt täglich die Liste der parlamentarischen Fragen (data.public.lu)
# und speichert die Fragen von Meris Sehovic als docs/froen.json.
import csv, io, json, os, unicodedata, urllib.request

URL = "https://data.public.lu/en/datasets/r/e5a821df-6b96-4da6-9fa5-ff404bc121f3"
NAME = "sehovic"

def norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()

raw = urllib.request.urlopen(URL, timeout=120).read()
text = raw.decode("utf-8-sig", errors="replace")
dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t")
rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
cols = rows[0].keys() if rows else []

def col(*keys):
    for c in cols:
        if all(k in norm(c) for k in keys):
            return c
    return None

c_author = col("auteur") or col("author")
c_title = col("titre") or col("title")
c_num = col("numero") or col("number") or col("num")
c_type = col("type")
c_date = col("date", "depot") or col("date")
c_resp = col("date", "reponse") or col("response", "date")

out = []
for r in rows:
    if NAME not in norm(r.get(c_author, "")):
        continue
    out.append({
        "nummer": r.get(c_num, ""),
        "titel": r.get(c_title, ""),
        "typ": r.get(c_type, ""),
        "datum": r.get(c_date, ""),
        "aentwert": r.get(c_resp, "") if c_resp else "",
    })

def key(q):
    d = q["datum"]
    parts = d.replace("-", "/").split("/")
    if len(parts) == 3 and len(parts[0]) == 2:
        d = f"{parts[2]}-{parts[1]}-{parts[0]}"
    return d
out.sort(key=key, reverse=True)

os.makedirs("docs", exist_ok=True)
json.dump({"spalten": list(cols), "froen": out}, open("docs/froen.json", "w"), ensure_ascii=False, indent=1)
print(len(out), "Fragen gefunden")
