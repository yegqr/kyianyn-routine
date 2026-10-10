# python3 -I va_count.py data/bronze/telegram/VA_Kyiv.jsonl   (Kyiv-city alerts per Kyiv month from T0)
import json, re, sys, collections
from datetime import datetime, timedelta
S = re.compile(r"(м\.\s*Київ\s*[-–]\s*)?[Пп]овітряна тривога|(Червоний|Жовтий) рівень небезпеки|(У Києві |У столиці )?[Оо]голошено повітряну тривогу")
E = re.compile(r"(м\.\s*Київ\s*[-–]\s*)?[Вв]ідбій")
rows = {}
for line in open(sys.argv[1], encoding="utf-8"):
    r = json.loads(line)
    rows.setdefault(r["post_id"], r)
c, is_open, orph = collections.Counter(), False, []
for r in sorted(rows.values(), key=lambda r: r["post_id"]):
    if r["published_at"] < "2026-04-30T21:00:00Z":  # before T0
        continue
    h = re.sub(r"^[^0-9A-Za-zА-Яа-яЄєІіЇїҐґ]+", "", r["text"]).strip()[:120]
    m = (datetime.fromisoformat(r["published_at"]) + timedelta(hours=3)).strftime("%m")  # Kyiv = UTC+3 until 2026-10-25
    if E.match(h):
        if not is_open:
            orph.append(r["post_id"])
        is_open = False
    elif S.match(h):
        if not is_open:
            c[m] += 1
        is_open = True
print("alerts by Kyiv month:", dict(sorted(c.items())), "total", sum(c.values()), "orphan ends:", orph)
