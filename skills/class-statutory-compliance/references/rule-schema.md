# Rule-clause database schema (v0 draft)

One JSON object per clause, encoded from the SUPPLIED rule document — never from memory.

```json
{
  "clause_id": "CSR-BC Pt.1 Ch.3 Sec.4.2",
  "source": "IACS CSR Bulk Carriers",
  "edition": "January 2024 + Corr.1 — CONFIRM against the copy in force at contract date",
  "document_hash": "sha256:…",
  "applies_to": {
    "ship_type": ["bulk carrier"],
    "length_range_m": [90, null],
    "keel_date_min": "2006-04-01",
    "notation": null
  },
  "requirement_text": "verbatim quote (with permission/redistribution checks) or a paraphrase flagged as such",
  "formula": "Z_req = (|M_sw| + |M_vw|) / sigma_allow",
  "symbols": {"sigma_allow": {"value_or_ref": "Table 3.4", "units": "MPa"}},
  "limit": {"op": ">=", "value": null, "units": null},
  "verification": "scantlings-midship:utilisation_deck",
  "evidence_target": "structural calculation report",
  "interpretations": ["IACS UI S-xx (as supplied)"],
  "status": "encoded | needs-review | paraphrase-only"
}
```

## Encoding rules

1. `document_hash` pins the exact source file; a clause without it is `needs-review`.
2. Formulas are transcribed verbatim and **unit-tested against a worked example from the
   rule's own guidance** before first use (this is what was missing for the wave-BM formula —
   see docs/DEFECT-LOG.md #36–38).
3. `paraphrase-only` clauses may inform the design but may NOT drive a compliance verdict.
4. Editions are dated; a rule-change notice invalidates affected clauses to `needs-review`
   automatically (version the database, diff on update).
5. Redistribution: quoting rule text is usually fine for engineering use under class society
   terms, but check before publishing verbatim text in a public repo — link + clause ID is
   the safe default.

## Loader contract

The compliance matrix generator (`class-statutory-compliance`) reads this database, evaluates
`applies_to` against the ship data, and binds `verification` to pipeline outputs. A clause
whose verification target does not exist in the stack becomes an OPEN item with the external
tool or class interaction named — never silently "satisfied".
