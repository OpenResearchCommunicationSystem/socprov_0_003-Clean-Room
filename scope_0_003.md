# SOCProv 0.003 — Scope Note

Status: draft for review  
Supersedes: SOCProv 0.002 (locked)  
Date: 2026-11-09

## 1. Purpose

Version 0.003 tightens the form-print product into a single document with a five-way internal reference system. It does not change the four JSON object shapes. It adds a draft-owned narrative marker and moves the preserved-source packet into the main product as Appendix 4.

## 2. Five linkable units

| Unit | Owner | Role | Visible in narrative? |
|---|---|---|---|
| BLOCK | Locked draft | Narrative location | No — marker is structural; used only as a back-reference target |
| XREF | JSON | Citation container | Appendix 1 |
| QUOTE | JSON (inside XREF) | Atomic extract (`SOURCE_ID`-`QUOTE_ID`) | Rendered inside XREF; linked from CLAIM and INDX |
| CLAIM | JSON | Edge-like statement | Appendix 2; back-reference to BLOCK |
| INDX | JSON | Node-like card | Appendix 3; back-reference to BLOCK |
| PROV | JSON | Preservation of what the system held | Appendix 4 |

Authorship markers (LLM, USER, DET) remain available on lightweight fields. They are not link targets.

## 3. BLOCK

A BLOCK is declared in the locked draft by a structural marker at the end of a Markdown heading:

```markdown
## Heading Title {#BLOCK-001}
```

Form-print:
- creates a local bookmark `BLOCK-001`
- suppresses the marker from the visible heading
- derives return links from CLAIM and INDX objects that are referenced inside the BLOCK scope
- does not store BLOCK identifiers in any JSON object

The reader sees the heading. The marker exists only so an appendix object can return to the narrative location that used it.

## 4. QUOTE

The atomic citation unit remains `XREF-<SOURCE_ID>-<QUOTE_ID>`.

QUOTE text and translation live only in the XREF excerpts array. CLAIM and INDX may display the quote text, but the link always resolves to the XREF entry. No separate QUOTE object is stored.

## 5. PROV (Appendix 4)

PROV proves what the system held at the time of the pull. It does not prove that an internet source still exists or is unaltered.

Valid intake types for PROV:
- user paste
- user upload
- API return
- web scrape

The preserved text is the largest contiguous body text obtained. It is hashed. It is never modified, annotated, or WikiLinked.

Appendix 4 renders every PROV marked `include_in_packet: true`, in SOURCE ID order, with:
- `PROV-<SOURCE_ID>`
- SHA-256 hash
- raw text
- full-document translation, if present

## 6. Product structure

A single document contains:

```text
Locked draft narrative
Appendix 1: Extracted References (XREF + QUOTE)
Appendix 2: Claims
Appendix 3: Index
Appendix 4: Preserved Sources (PROV)
```

Clear line breaks (blank paragraph or page break) separate objects within each appendix.

## 7. What does not change

- JSON object shapes for XREF, CLAIM, INDX, and PROV
- CLAIM wording rule
- Core prohibitions (no confidence language, no source scoring, no legal characterizations)
- Form-print contract (zero synthesis, same inputs, UTC stamp)
- Word as primary product; PDF optional
- `index_to` not rendered by default; properties carry the structured links

## 8. Out of scope for 0.003

- Classification handling
- Lifecycle directory and draft-lock SHA-256 (noted as future-forward)
- Canonical Markdown/HTML intermediate format
- Historical/not-used rendering profile
