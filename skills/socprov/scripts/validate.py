#!/usr/bin/env python3
"""
SOCProv 0.003 minimal preprint validation.
Checks BLOCK uniqueness, WikiLink resolution, PROV hash match, no external hyperlinks.
"""
import json, re, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def validate(draft_path: Path):
    errors = []
    warnings = []

    draft = draft_path.read_text(encoding="utf-8")

    # 1. BLOCK markers unique
    blocks = re.findall(r"\{#BLOCK-(\d{3})\}", draft)
    if len(blocks) != len(set(blocks)):
        errors.append("duplicate BLOCK identifiers")
    for b in blocks:
        if not re.search(rf"^#{{1,6}}\s+.+\{{#BLOCK-{b}\}}", draft, re.M):
            errors.append(f"BLOCK-{b} marker not at end of heading")

    # 2. Collect valid targets
    valid = set(f"BLOCK-{b}" for b in blocks)
    for xp in (DATA / "xref").glob("XREF-*.json"):
        x = load_json(xp)
        if not x or x.get("not_used"):
            continue
        sid = x.get("source_id", "")
        if not sid.startswith("XREF-"):
            sid = f"XREF-{sid}"
        valid.add(sid)
        for ex in (x.get("excerpts") or x.get("quotes") or []):
            qid = ex.get("quote_id", "")
            valid.add(qid if qid.startswith("XREF-") else f"{sid}-{qid}")
    for cp in (DATA / "claim").glob("CLAIM-*.json"):
        c = load_json(cp)
        if c and not c.get("not_used"):
            cid = c.get("id") or c.get("claim_id") or ""
            if not cid.startswith("CLAIM-"):
                cid = f"CLAIM-{cid}"
            valid.add(cid)
    for ip in (DATA / "indx").glob("INDX-*.json"):
        ind = load_json(ip)
        if ind and not ind.get("not_used"):
            valid.add(f"INDX-{ind.get('indx_id')}")

    # 3. WikiLinks resolve
    for m in re.finditer(r"\[\[([^|\]]+)", draft):
        target = m.group(1).strip()
        if target not in valid:
            errors.append(f"unresolved WikiLink: {target}")

    # 4. PROV hash match when include_in_packet
    for pp in (DATA / "prov").glob("PROV-*.json"):
        prov = load_json(pp)
        if not prov or not prov.get("include_in_packet") or prov.get("not_used"):
            continue
        raw_path = ROOT / prov.get("raw_path", "")
        if not raw_path.exists():
            errors.append(f"PROV-{prov.get('source_id')} raw missing")
            continue
        h = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if h != prov.get("hash"):
            errors.append(f"PROV-{prov.get('source_id')} hash mismatch")

    # 5. No external hyperlink markup in draft
    if re.search(r"https?://", draft) and re.search(r"\[https?://", draft):
        warnings.append("possible external hyperlink markup in draft")

    print(f"errors: {len(errors)}")
    for e in errors:
        print(f"  ERROR: {e}")
    print(f"warnings: {len(warnings)}")
    for w in warnings:
        print(f"  WARN: {w}")
    return len(errors) == 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <draft.md>")
        sys.exit(1)
    ok = validate(Path(sys.argv[1]))
    sys.exit(0 if ok else 1)
