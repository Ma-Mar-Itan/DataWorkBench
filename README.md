# Data Cleaning Workbench

**A local, human-in-the-loop Excel workbench for value standardization,
recoding, and categorical cleaning.** Built for survey teams, statistical
offices, research units, and anyone who has ever opened a spreadsheet full
of `"Male"`, `" male "`, `"MALE"`, and `"M"` and thought *there has to be
a better way*.

The app is **general-purpose**: it detects recurring values in any
language (English, Arabic, mixed), classifies them (category / missing /
numeric-like / date / free-text), and lets you write explicit rules to
transform them. Arabic → English translation is just one special case of
the broader pattern.

---

## What it does

Upload an `.xlsx` file → scan every string value → browse them in a
filterable explorer → write cleaning rules (source → target, with scope
and match mode) → preview the result on a chosen sheet → generate a
cleaned workbook → optionally save the rules as a named set for reuse.

Common use cases:

| Task                               | Rule pattern                                    |
|------------------------------------|-------------------------------------------------|
| Gender recoding                    | `male → 1`, `female → 2` in the `Gender` column |
| Yes/No coding                      | `Yes → 1`, `No → 0` (normalized match)          |
| Likert scale → numeric             | `Very poor → 1` … `Very good → 5`               |
| Missing-value standardization      | `N/A`, `-`, `.`, `missing` → blank              |
| Category spelling unification      | `Beirut`, `بيروت`, `Beyrouth` → `Beirut`        |
| Column-specific recoding           | `1` means "male" in one column, "yes" in another |

---

## What it is *not*

- Not an AI assistant. No LLMs, no auto-cleaning, no "smart" guesses.
- Not a chatbot. No prompt box. The interface is a structured tool.
- Not a cloud service. Workbook bytes stay on your machine (or, on the
  Streamlit Community Cloud demo, inside the ephemeral container).
- Not a black-box cleaner. Every replacement is a rule you wrote. Every
  rule is visible, editable, and scoped.

---

## Safety invariants

The rule engine enforces three guarantees at the lowest layer, so every
action taken by the exporter inherits them automatically.

### 1. Whole-cell matching only

A rule matches a cell only when the cell's **entire** (raw or normalized)
value equals the rule's source value. The engine never performs substring
matching.

Concretely: a rule `male → 1` will recode a cell whose value is exactly
`male` or `MALE` or `  Male  ` (under normalized mode), but will **not**
touch a cell whose value is `male student who left early`. The
free-text column stays intact.

This is proven mechanically in
[`tests/test_rules_engine.py::test_no_substring_leak`](tests/test_rules_engine.py)
and, with real Arabic, in
[`tests/test_exporter.py::test_arabic_shorter_term_does_not_replace_inside_longer_phrase`](tests/test_exporter.py).

### 2. Formula cells are never rewritten

Any cell whose type is a formula (`data_type == 'f'` or value starting
with `=`) is skipped outright by both scan and export. Its formula string
is never normalized, matched, or written. Your workbook logic survives.

### 3. Non-string cells pass through untouched

Numbers, booleans, datetimes, and empty cells are left exactly as they
were. Rules only look at string values.

---

## The rule system

A **CleaningRule** has eight relevant fields:

```python
source_value       = "male"
target_value       = "1"
action_type        = ActionType.MAP_CODE       # or REPLACE, SET_BLANK
match_mode         = MatchMode.EXACT_NORMALIZED # or EXACT_RAW
scope_type         = ScopeType.COLUMN           # or SHEET, GLOBAL
scope_sheet        = "Survey"
scope_column       = "Gender"
enabled            = True
```

### Scope priority

When multiple rules could apply to the same cell, the engine picks the
**most specific** one:

```
COLUMN (this sheet, this column)
   ↓ otherwise
SHEET  (this sheet, any column)
   ↓ otherwise
GLOBAL (anywhere)
```

Within the same scope tier, `EXACT_RAW` wins over `EXACT_NORMALIZED`.
Within identical scope *and* mode, the first rule in list order wins.

This lets you do things like:

```
# Global: blank common missing tokens
N/A → (blank)
-   → (blank)

# Column-scoped: Gender → numeric
(Survey, Gender) male   → 1
(Survey, Gender) female → 2

# Different column, different meaning for the same source value
(Survey, Response) yes → 1
(Survey, Response) no  → 0
```

### Match modes

- **`EXACT_RAW`** — the cell's raw string must be byte-identical to the
  rule's source value. Strictest mode. Useful when you care about case and
  whitespace (for example, to distinguish `"1"` from `" 1"`).

- **`EXACT_NORMALIZED`** — both sides go through a normalization pipeline
  (NFKC → remove tatweel → collapse whitespace → trim → casefold) before
  comparison. Case, whitespace variants, and Unicode compatibility forms
  all match a single rule. This is the mode you'll want 95% of the time.

Neither mode ever does substring matching.

### Action types

- **`REPLACE`** — write `target_value` to the matching cell.
- **`MAP_CODE`** — same mechanism as REPLACE; the separate name lets the
  UI group categorical recodings visually. Preset templates use MAP_CODE.
- **`SET_BLANK`** — clear the matching cell (writes `None`, producing a
  true empty cell, not the string `""`).

---

## Workbook preservation

Because the exporter mutates the workbook in place via `openpyxl` rather
than rebuilding it from a DataFrame, the output keeps:

- sheet order and names (including hidden sheets)
- formulas and cached results
- merged cells
- column widths and freeze panes
- most cell formatting

Pandas is used only for preview tables, never for export.

---

## Value Explorer

After scanning, every unique string value appears in a filterable table:

| Filter         | What it does                                  |
|----------------|-----------------------------------------------|
| Search         | substring match on raw or normalized text     |
| Sheet          | restrict to one sheet                         |
| Column         | restrict to one column (by header name)       |
| Class          | category / missing / numeric / header / …     |
| Missing only   | only values flagged as likely missing tokens  |
| Min frequency  | hide one-off values                           |

Each value is classified into one of:

- **Category** — repeated short text, likely a category label
- **Numeric-like** — `"1"`, `"2.5"` stored as string
- **Mixed alnum** — codes like `"A1"`, `"Q3-2024"`
- **Missing token** — `N/A`, `-`, `.`, `missing`, `unknown`, …
- **Header label** — appeared in the first row of a sheet
- **Date-like** — recognized date patterns
- **Free text** — long strings, don't batch-recode
- **Low frequency** — seen only once

The classification is **never** used to trigger automatic replacement. It
only helps you prioritize cleaning work.

You can select values in the explorer and seed draft rules in one click
(Replace or Set-blank), ready to refine in the Rules card.

---

## Presets

Five starter templates are included. They populate editable draft rules;
nothing applies automatically.

| Preset                                  | Generates                                          |
|-----------------------------------------|----------------------------------------------------|
| Gender coding                           | `male → 1`, `female → 2` (normalized)              |
| Yes / No coding                         | `yes → 1`, `no → 0` (normalized)                   |
| 5-point Likert                          | `Very poor → 1` … `Very good → 5`                  |
| Missing value cleanup                   | 17 common tokens → blank                           |
| Marital status                          | `Single → 1`, `Married → 2`, `Divorced → 3`, …     |

Scoped presets (Gender, Yes/No) let you pick a sheet/column on insert.

---

## Rule sets

Save a collection of rules as a named set under `rulesets/<slug>.json`,
then load it on the next workbook. One file per set. Human-editable JSON.

```json
{
  "name": "Survey 2024 standard recoding",
  "description": "Gender, yes/no, and missing-value cleanup.",
  "rules": [
    {
      "rule_id": "ab12cd34ef56",
      "source_value": "male",
      "normalized_source_value": "male",
      "target_value": "1",
      "action_type": "map_code",
      "match_mode": "exact_normalized",
      "scope_type": "column",
      "scope_sheet": "Survey",
      "scope_column": "Gender",
      "enabled": true,
      ...
    }
  ]
}
```

---

## Project layout

```
cleaner/
├── app.py                       Streamlit entry point
├── requirements.txt
├── README.md
├── rulesets/                    JSON rule sets, created on first save
├── core/                        Pure logic, fully tested
│   ├── normalizer.py            NFKC + whitespace + tatweel + casefold
│   ├── classifier.py            Value-class heuristics
│   ├── extractor.py             Workbook scan → ExtractedValue + ColumnProfile
│   ├── rules_engine.py          RuleIndex: scope-aware, no-substring matching
│   ├── exporter.py              Workbook-safe application of a rule set
│   ├── preview.py               (original, cleaned, changed_mask) DataFrames
│   ├── ruleset_store.py         JSON persistence
│   └── presets.py               Starter templates
├── models/
│   └── schemas.py               ExtractedValue, CleaningRule, RuleSet + enums
├── ui/                          Streamlit rendering
│   ├── layout.py                Shell primitives: appbar, band, cards, panel
│   ├── theme/
│   │   └── styles.css           Design system
│   ├── upload_section.py        Card 1
│   ├── scan_section.py          Card 2
│   ├── explorer_section.py      Card 3 — Value Explorer
│   ├── rules_section.py         Card 4 — Cleaning Rules (preset + quick-add + grid)
│   ├── preview_section.py       Card 5 — with change highlighting
│   ├── export_section.py        Card 6 — generate + download
│   └── rulesets_section.py      Library — load/save/delete rule sets
└── tests/                       77 tests, ~4 seconds
    ├── conftest.py              Fixtures inc. Arabic test vocabulary
    ├── test_normalizer.py
    ├── test_classifier.py
    ├── test_extractor.py
    ├── test_rules_engine.py     ← safety proofs live here
    ├── test_exporter.py         ← Arabic Home/Homework proof + realistic scenarios
    ├── test_preview.py
    ├── test_ruleset_store.py
    └── test_presets.py
```

---

## Running locally

```bash
git clone <this-repo>
cd cleaner
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ recommended.

For confidential workbooks, **always run locally**. Hosted Streamlit
Community Cloud reads files into the hosting container's memory, which
may be outside your institutional boundary.

---

## Running the tests

```bash
pip install pytest
pytest -v
```

77 tests, runs in about 4 seconds. The ones most worth reading before
trusting the tool in production:

- `test_rules_engine.py::test_no_substring_leak` — the master safety proof.
- `test_exporter.py::test_arabic_shorter_term_does_not_replace_inside_longer_phrase` —
  the same property, end-to-end with a real Arabic workbook.
- `test_exporter.py::test_column_scoped_rules_do_not_corrupt_free_text` —
  a realistic survey scenario where column scoping prevents the Gender
  rule from touching the free-text Note column.
- `test_exporter.py::test_formulas_are_never_translated` — proof that
  formulas survive the export pass.

---

## UI design

The interface is deliberately institutional:

- **Typography** — Source Serif 4 for headings and metric values, Inter
  for UI copy, IBM Plex Mono for numeric figures and rule source/target.
- **Color** — warm off-white page (`#f4f2ee`), white cards, a muted
  burgundy (`#7a1f2b`) as the single accent. No gradients, no neon.
- **Structure** — top app bar, dark contextual band beneath it, sticky
  left workflow panel showing stage state (idle / active / done), and
  six numbered cards in the main column plus a Library card for rule sets.
- **Streamlit suppression** — a single stylesheet hides the default
  toolbar, hamburger, deploy button, and restyles every widget
  (inputs, buttons, uploader, data editor, tabs, expanders, progress) to
  match the design system.

---

## Known limitations (v1)

- Whole-cell matching only. Values embedded inside paragraph text can't
  be touched by default — that's a safety feature, not a bug.
- No OCR. Text inside images is invisible.
- No `.xls` support — legacy files must be resaved as `.xlsx` first.
- No fuzzy-match suggestions yet. Candidates like `Beirut` / `beirut` /
  `Beyrouth` must currently be mapped individually (or use `EXACT_NORMALIZED`
  to fold case and whitespace variants into one rule).
- Header is assumed to be the first row of each sheet.
- Single user, single machine. No collaboration layer.

---

## Roadmap

- Fuzzy similarity suggestions via `rapidfuzz` — cluster near-duplicates
  for bulk recoding.
- Bulk mapping import/export (CSV of source → target pairs).
- Per-sheet, per-rule audit log of every replacement.
- Toggle for whether to include hidden sheets.
- Header-row translation (currently headers are scanned but not cleaned
  by default).
- Advanced token-aware phrase mode — opt-in only, with longest-match-first
  and non-overlapping span locking. The whole-cell safety invariant must
  still hold on this path.
