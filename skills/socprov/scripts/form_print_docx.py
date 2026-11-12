#!/usr/bin/env python3
"""
SOCProv 0.003 Word form-print emitter.
Clean-room implementation of FORM-PRINT-CONTRACT.txt.
Zero synthesis. Internal bookmarks only.
"""
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PRODUCTS = ROOT / "products"

def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def get_quotes(x):
    return x.get("excerpts") or x.get("quotes") or []

def get_extract(ex):
    return ex.get("text") or ex.get("extract") or ""

def add_bookmark(paragraph, name):
    bid = str(abs(hash(name)) % 100000)
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), bid)
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), bid)
    paragraph._p.insert(0, start)
    paragraph._p.append(end)

def add_internal_link(paragraph, text, anchor):
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), anchor)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "0000FF")
    rPr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)

def linkify_runs(paragraph, text, valid):
    pattern = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        target = m.group(1).strip()
        display = m.group(2).strip() if m.group(2) else target
        if target in valid:
            add_internal_link(paragraph, display, target)
        else:
            paragraph.add_run(display)
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])

def form_print_docx(draft_path: Path):
    PRODUCTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    out = PRODUCTS / f"{draft_path.stem}-report-{stamp}.docx"

    # Collect valid anchors
    valid = set()
    block_map = {}  # object_id -> list of BLOCK ids
    draft_text = draft_path.read_text(encoding="utf-8")

    # Parse BLOCK markers and build scope map
    current_block = None
    for line in draft_text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*\{#BLOCK-(\d{3})\}\s*$", line)
        if m:
            current_block = f"BLOCK-{m.group(3)}"
            valid.add(current_block)
            continue
        if line.startswith("#") and not re.search(r"\{#BLOCK-", line):
            # heading without marker ends current block at same or higher level
            level = len(line) - len(line.lstrip("#"))
            # simple: any new heading without marker closes current
            current_block = None
        if current_block:
            for wm in re.finditer(r"\[\[([^|\]]+)", line):
                target = wm.group(1).strip()
                block_map.setdefault(target, []).append(current_block)

    for xp in (DATA / "xref").glob("XREF-*.json"):
        x = load_json(xp)
        if not x or x.get("not_used"):
            continue
        sid = x.get("source_id", "")
        if not sid.startswith("XREF-"):
            sid = f"XREF-{sid}"
        valid.add(sid)
        for ex in get_quotes(x):
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

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    # Body
    for line in draft_text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*\{#BLOCK-(\d{3})\}\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            p = doc.add_heading("", level=min(level, 3))
            linkify_runs(p, text, valid)
            add_bookmark(p, f"BLOCK-{m.group(3)}")
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            p = doc.add_heading("", level=min(level, 3))
            linkify_runs(p, text, valid)
        elif line.strip():
            p = doc.add_paragraph()
            linkify_runs(p, line, valid)
        else:
            doc.add_paragraph()

    # Appendix 1: XREF
    doc.add_page_break()
    doc.add_heading("Appendix 1: Extracted References", level=1)
    first = True
    for xp in sorted((DATA / "xref").glob("XREF-*.json")):
        xref = load_json(xp)
        if not xref or xref.get("not_used"):
            continue
        if not first:
            doc.add_paragraph()
        first = False
        sid = xref.get("source_id", "")
        if not sid.startswith("XREF-"):
            sid = f"XREF-{sid}"
        p = doc.add_heading("", level=2)
        p.add_run(f"{sid} — {xref.get('short_title','')}")
        add_bookmark(p, sid)
        cit = xref.get("traditional_citation", "")
        if cit:
            doc.add_paragraph(cit)
        for ex in get_quotes(xref):
            qid = ex.get("quote_id", "")
            full = qid if qid.startswith("XREF-") else f"{sid}-{qid}"
            qp = doc.add_paragraph()
            qp.add_run(full).bold = True
            add_bookmark(qp, full)
            ep = doc.add_paragraph()
            linkify_runs(ep, get_extract(ex), valid)
            if ex.get("translation"):
                tp = doc.add_paragraph()
                tp.add_run("Translation: ").italic = True
                tp.add_run(ex["translation"])
            # return links
            returns = block_map.get(full, [])
            if returns:
                rp = doc.add_paragraph()
                rp.add_run("Narrative references: ").italic = True
                for b in sorted(set(returns)):
                    add_internal_link(rp, f" {b}", b)

    # Appendix 2: CLAIM
    doc.add_page_break()
    doc.add_heading("Appendix 2: Claims", level=1)
    first = True
    for cp in sorted((DATA / "claim").glob("CLAIM-*.json")):
        c = load_json(cp)
        if not c or c.get("not_used"):
            continue
        if not first:
            doc.add_paragraph()
        first = False
        cid = c.get("id") or c.get("claim_id") or ""
        if not cid.startswith("CLAIM-"):
            cid = f"CLAIM-{cid}"
        p = doc.add_heading("", level=2)
        p.add_run(f"{cid} — {c.get('short_title','')}")
        add_bookmark(p, cid)
        returns = block_map.get(cid, [])
        if returns:
            rp = doc.add_paragraph()
            rp.add_run("Narrative references: ").italic = True
            for b in sorted(set(returns)):
                add_internal_link(rp, f" {b}", b)
        for label, field in [("Specific Claim", "specific_claim"), ("Specific Context", "specific_context"), ("Logic", "logic")]:
            fp = doc.add_paragraph()
            fp.add_run(f"{label}: ").bold = True
            linkify_runs(fp, c.get(field, ""), valid)
        for src in c.get("sources", []):
            if isinstance(src, str) and src in valid:
                qp = doc.add_paragraph()
                add_internal_link(qp, src, src)

    # Appendix 3: INDX
    doc.add_page_break()
    doc.add_heading("Appendix 3: Index", level=1)
    first = True
    for ip in sorted((DATA / "indx").glob("INDX-*.json")):
        ind = load_json(ip)
        if not ind or ind.get("not_used"):
            continue
        if not first:
            doc.add_paragraph()
        first = False
        iid = f"INDX-{ind.get('indx_id')}"
        p = doc.add_heading("", level=2)
        p.add_run(f"{iid} — {ind.get('short_title','')}")
        add_bookmark(p, iid)
        returns = block_map.get(iid, [])
        if returns:
            rp = doc.add_paragraph()
            rp.add_run("Narrative references: ").italic = True
            for b in sorted(set(returns)):
                add_internal_link(rp, f" {b}", b)
        if ind.get("normalized_long"):
            doc.add_paragraph(f"Normalized long: {ind['normalized_long']}")
        if ind.get("normalized_short"):
            doc.add_paragraph(f"Normalized short: {ind['normalized_short']}")
        for term in ind.get("search_terms", []):
            doc.add_paragraph(f"Search term: {term}")
        for prop in ind.get("properties", []):
            fp = doc.add_paragraph()
            fp.add_run(f"{prop.get('label','')}: ").bold = True
            linkify_runs(fp, prop.get("value", ""), valid)
            for s in prop.get("sources", []):
                if s in valid:
                    add_internal_link(fp, f" [{s}]", s)
            for cl in prop.get("claims", []):
                if cl in valid:
                    add_internal_link(fp, f" [{cl}]", cl)

    # Appendix 4: PROV
    doc.add_page_break()
    doc.add_heading("Appendix 4: Preserved Sources", level=1)
    doc.add_paragraph("PROV proves what the system held at the time of the pull. It does not prove that an internet source still exists or is unaltered.")
    first = True
    for pp in sorted((DATA / "prov").glob("PROV-*.json")):
        prov = load_json(pp)
        if not prov or not prov.get("include_in_packet") or prov.get("not_used"):
            continue
        if not first:
            doc.add_paragraph()
        first = False
        doc.add_heading(f"PROV-{prov.get('source_id','')}", level=2)
        doc.add_paragraph(f"SHA-256: {prov.get('hash','')}")
        raw_path = ROOT / prov.get("raw_path", "")
        if raw_path.exists():
            raw = raw_path.read_text(errors="replace")
            for para in raw.split("\n\n"):
                if para.strip():
                    doc.add_paragraph(para.replace("\n", " "))

    doc.save(str(out))
    print(f"Report: {out}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 form_print_docx.py <draft.md>")
        sys.exit(1)
    form_print_docx(Path(sys.argv[1]))
