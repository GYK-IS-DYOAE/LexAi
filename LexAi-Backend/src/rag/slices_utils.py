import re

HDR_RE = re.compile(r"(HÜKÜM|SONUÇ|H U ̈ K U ̈ M|S O N U Ç)\s*[:\-]?", re.IGNORECASE)

def extract_key_slices(text: str, head=1200, tail=1200, verdict_span=3000):
    if not text:
        return []
    t = text.strip()
    out = []

    m = HDR_RE.search(t)
    if m:
        start = m.start()
        out.append(t[start:start+verdict_span])  # HÜKÜM/SONUÇ bloğu

    out.append(t[:head])                         # baş
    if len(t) > tail:
        out.append(t[-tail:])                    # son

    uniq, seen = [], set()
    for s in out:
        s = (s or "").strip()
        if s and s not in seen:
            uniq.append(s); seen.add(s)
    return uniq
