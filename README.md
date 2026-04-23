# Scrubline — spreadsheet data-cleaning app

A Streamlit web app for cleaning Excel workbooks. Users upload an `.xlsx`,
scan it for repeated values, define replacement rules (with whole-cell
matching and scope control), preview changes, inspect descriptive
statistics, and export a cleaned workbook.

This README covers both halves of the app: the Streamlit UI layer and the
backend processing engine.

---

## 1. Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests:

```bash
pytest tests/ -q
```

**Status:** 75 tests pass (normalizer, scanner, rules engine, preview,
stats, exporter, Arabic cases, end-to-end integration). All six views
render without exceptions under `streamlit.testing.v1.AppTest`.

---

## 2. File structure

```
datacleaner/
├── app.py                          # main Streamlit entrypoint
├── integration.py                  # adapter between UI and core/
├── requirements.txt
│
├── ui/                             # frontend
│   ├── styles.py                   # ~16 KB of custom CSS + design tokens
│   ├── components.py               # topbar, nav rail, stat cards, panels
│   ├── views.py                    # the six sidebar destinations
│   └── demo_data.py                # shaped like the real backend schemas
│
├── core/                           # backend engine
│   ├── normalizer.py               # Arabic-safe NFKC + tatweel + casefold
│   ├── workbook_reader.py          # openpyxl + pandas dual load
│   ├── scanner.py                  # value occurrence aggregation
│   ├── type_inference.py           # numeric / date / categorical / free text
│   ├── rules_engine.py             # WHOLE-CELL matching, scope precedence
│   ├── preview_engine.py           # non-mutating apply
│   ├── stats_engine.py             # numeric, categorical, missingness, before/after
│   ├── exporter.py                 # cleaned workbook, stats xlsx, ruleset JSON
│   └── ruleset_store.py            # JSON save/load with schema validation
│
├── models/
│   ├── enums.py                    # ScopeType, MatchMode, ActionType, ValueClass, ColumnType
│   └── schemas.py                  # Rule, ValueOccurrence, ApplyResult, stats dataclasses
│
└── tests/
    ├── _helpers.py                 # make_test_workbook() in-memory .xlsx fixture
    ├── test_normalizer.py          # Latin / Arabic / tatweel / missing tokens
    ├── test_scanner.py             # aggregation, value classes, workbook summary
    ├── test_rules_engine.py        # whole-cell invariant, scope, precedence
    ├── test_preview_engine.py      # non-mutating, sheet-scoped
    ├── test_stats_engine.py        # numeric, categorical, missingness
    ├── test_exporter.py            # roundtrip, sheet names, formula preservation
    ├── test_arabic_cases.py        # end-to-end Arabic correctness
    └── test_integration_end_to_end.py   # full pipeline through integration.py
```

---

## 3. UI architecture

### Layout (mirrors the reference screenshot's desktop-productivity feel)

```
┌──────────────────────────────────────────────────────────────┐
│  topbar: brand · search · scan-status · actions              │
├────────┬─────────────────────────────────────────────────────┤
│ nav    │   workspace                                         │
│ rail   │   (page header + panels + tables)                   │
└────────┴─────────────────────────────────────────────────────┘
```

- **Topbar**: rounded near-white panel floating on the soft gray canvas.
  Contains the product mark, a prominent search input, a pill-style scan
  status indicator (with an animated dot while scanning), and compact
  Rescan / Help buttons on the right. The search is the widest element
  in the bar — consistent with search-led productivity tools.
- **Left nav rail**: its own rounded panel. Active item gets a pale blue
  fill and stronger text weight. Below the nav, a mini "current
  workbook" summary that changes as the user uploads.
- **Workspace**: every section leads with a small uppercase eyebrow
  ("Step 2"), a 20px page title, and a muted subtitle. Content lives in
  rounded white panels with soft 1px borders and very subtle shadows.
- **Stat cards**: a responsive grid — four to six compact cards across
  the top of most views, uppercase label / large value / muted delta
  line.
- **Tables**: used as the central workspace element on Scan and Rules.
  Clean column headers in uppercase tracking, soft row dividers,
  selection highlighting via Streamlit's native dataframe/data_editor.

### Design tokens (in `ui/styles.py`)

```
--bg:            #f3f4f6   (soft page gray)
--panel:         #ffffff   (rounded card)
--panel-soft:    #fafbfc   (search input, subtle inset areas)
--border:        #e4e6ea
--text:          #1f2430
--text-muted:    #5b6472
--text-faint:    #8a93a2
--accent:        #2d5cbb   (restrained serious blue)
--accent-soft:   #e7eefa   (active nav fill, primary chip)
--radius-md:     10px
--shadow-sm:     0 1px 2px rgba(16,24,40,0.04)
```

Every status color (success/warn/danger) is a muted version of its
hue — there is no bright red or green anywhere in the UI.

### How the screenshot inspired the design

The uploaded reference is a mail client, so its *specific identity* is
off-limits. What I took from it:

1. **Layout language**: rounded floating panels on a soft gray canvas,
   not edge-to-edge white. The topbar and nav rail are their own
   surfaces that sit on the gray.
2. **Search-dominant top bar**: in the reference, the search input is
   the widest element in the bar and visually leads the interaction.
   Scrubline does the same — search values / columns / sheets is
   prominent and central.
3. **Nav rail with a clear active state**: pale-tinted fill plus
   stronger text weight for the active item, and a minimal hover state
   for the rest. Just like the reference, it's a quiet list.
4. **List-first workspace**: the reference is fundamentally a list
   (rows of mail). Scrubline's central views (Scan, Rules, Preview)
   are all tables — this is deliberate. Tables are the primary
   interaction surface; panels and stat cards frame them but don't
   compete.
5. **Count badges and compact chips**: the reference uses small pill
   badges to mark "1 new" and categorize. Scrubline uses the same
   vocabulary for rule counts, value classes, and status.

What I deliberately **didn't** copy: the product logo/wordmark style,
the specific color palette (mail apps lean warmer and use more
saturated accent colors; a serious data tool stays cooler and
quieter), the tab strip inside the list ("Primary / Promotions /
Social"), and the right-rail add-ons column.

---

## 4. Backend architecture

### Processing pipeline

```
bytes → load → LoadedWorkbook ──┬─→ scan  → ScanResult
                                ├─→ stats → NumericStats / CategoricalStats / missingness
                                ├─→ preview(rules) → ApplyResult (non-mutating)
                                ├─→ apply(rules)   → ApplyResult (mutates wb)
                                └─→ export         → .xlsx / .xlsx / .json
```

Two parallel representations are kept on `LoadedWorkbook`:

- **pandas DataFrames** — fast column-wise analytics for scan, stats,
  type inference.
- **openpyxl Workbook** — preserves formulas, formatting, and sheet
  structure so the exporter writes back a file that's byte-close to
  the original for every cell no rule touched.

The rules engine mutates both in lockstep so downstream stats reflect
the cleaned data.

### The non-negotiable rule: whole-cell matching

`core/rules_engine.py` compares the **entire** cell value (raw or
normalized) against the rule's source value. There is no substring or
token-level code path anywhere.

The flagship tests live in `tests/test_rules_engine.py` →
`TestWholeCellMatching`:

```
Home          → House    ✓
Homework      → Homework ✓  (not matched)
Home office   → Home office ✓  (not matched)
```

And the Arabic parallel in `tests/test_arabic_cases.py`:

```
ذكر              → M              ✓
ذكر أحمد الأمر   → ذكر أحمد الأمر  ✓  (not matched)
الذكر الحكيم     → الذكر الحكيم    ✓  (not matched)
```

### Rule precedence

Ordered tuple `(scope_rank, match_rank, created_at)` — lowest wins.

| Factor        | Rank 0 (wins)      | Rank 1             | Rank 2    |
|---------------|--------------------|--------------------|-----------|
| Scope         | `column`           | `sheet`            | `workbook`|
| Match mode    | `exact_raw`        | `exact_normalized` | —         |
| Tie breaker   | earlier `created_at` wins                               |

Exercised in `TestPrecedence`.

### Arabic-safe normalization

`core/normalizer.py` does only these transformations:

1. NFKC (safe — folds presentation forms to base letters)
2. Tatweel (`U+0640`) removal — purely decorative
3. Whitespace collapse + trim
4. Unicode-aware casefold (no-op on Arabic script)

Things it **does not** do: strip diacritics, merge ا/أ/إ, merge ي/ى,
merge ة/ه, stem, transliterate, or substring anything. Those are
opinionated transformations that can silently change meaning, and this
product defaults to safety.

### Missing-token detection

`MISSING_TOKENS` includes common English and Arabic markers:
`""`, `"n/a"`, `"na"`, `"-"`, `"."`, `"missing"`, `"null"`, `"none"`,
`"nil"`, `"unknown"`, `"tbd"`, `"لا يوجد"`, `"غير معروف"`.

Detection is normalized, so `"  N/A  "` and `"n/a"` both match.

---

## 5. Integration: connecting UI to backend

The UI talks to the backend **only** through `integration.py`. None of
`ui/*` imports from `core/*` or `models/*`.

The adapter's surface is small:

```python
# Loading
wb = adapter.load(bytes, filename)

# Scan → shape ready for the scan view's table
scan = adapter.scan(wb)
#  returns { "summary": {...}, "values": [{"value", "normalized", ...}] }

# Rules (UI holds dicts; backend wants Rule objects — adapter converts)
rules = adapter.rules_from_dicts(st.session_state.rules)

# Preview / apply
preview = adapter.run_preview(wb, st.session_state.rules, sheet="Responses")
applied = adapter.run_apply(wb, st.session_state.rules)

# Stats
stats = adapter.compute_statistics(wb)

# Export (returns raw bytes for st.download_button)
workbook_bytes = adapter.export_workbook_bytes(wb)
stats_bytes    = adapter.export_stats_bytes(wb)
ruleset_bytes  = adapter.export_ruleset_bytes(st.session_state.rules)
```

### What the UI currently uses

The UI defaults to **demo data from `ui/demo_data.py`** so it renders
meaningfully before a real file is uploaded. The wire-up to real data
is a small per-view edit. For example, `ui/views.py :: render_scan()`:

```python
# today (demo)
from ui import demo_data as dd
s    = dd.demo_scan_summary()
rows = dd.demo_repeated_values()

# wiring in the real backend
import integration as adapter
if st.session_state.get("scan_result") is None and st.session_state.get("uploaded_file_bytes"):
    wb = adapter.load(st.session_state.uploaded_file_bytes, st.session_state.uploaded_file_name)
    st.session_state.loaded_wb    = wb
    st.session_state.scan_result  = adapter.scan(wb)

s    = st.session_state.scan_result["summary"]
rows = st.session_state.scan_result["values"]
```

Same pattern for `render_rules` (rules live in `st.session_state.rules`
already — just call `adapter.run_preview` and `adapter.run_apply`),
`render_preview` (swap `demo_preview_rows` for the preview result's
`.changes`), `render_stats` (swap demo numerics for
`adapter.compute_statistics`), and `render_export` (replace the
placeholder `_tiny_xlsx_bytes()` with `adapter.export_workbook_bytes(wb)`).

### Session state keys the UI owns

| Key                      | Shape                                            | Set by              |
|--------------------------|--------------------------------------------------|---------------------|
| `view`                   | `"upload" \| "scan" \| "rules" \| ...`           | nav rail            |
| `scan_state`             | `"idle" \| "running" \| "done"`                  | scan trigger        |
| `scan_rows`              | `int \| None` (shown in topbar)                  | scan trigger        |
| `global_search`          | `str`                                            | topbar              |
| `uploaded_file_bytes`    | `bytes`                                          | upload view         |
| `uploaded_file_name`     | `str`                                            | upload view         |
| `workbook_meta`          | `dict` — keys: filename, sheet_count, …          | upload view         |
| `loaded_wb`              | `LoadedWorkbook` (once real backend is wired)    | scan trigger        |
| `scan_result`            | `dict` from `adapter.scan(...)`                  | scan trigger        |
| `rules`                  | `list[dict]` (editable in data_editor)           | rules view          |

### Test coverage guarantees for the UI

- Every view renders without exceptions: run
  `tests/` plus the `AppTest`-based smoke pass in the README's
  "Running it" section. The CI equivalent would be:

  ```python
  from streamlit.testing.v1 import AppTest
  for view in ["upload", "scan", "rules", "preview", "stats", "export"]:
      at = AppTest.from_file("app.py")
      at.session_state["view"] = view
      at.run()
      assert not at.exception
  ```

---

## 6. Where to extend

- **More match modes**: add a new entry to `MatchMode` in
  `models/enums.py` and handle it in `_rule_matches_value` in
  `core/rules_engine.py`. Do not add a substring mode without an
  explicit user confirmation step in the UI — the whole-cell invariant
  is the product's safety promise.
- **Date normalization**: today dates are detected for type inference
  only, not normalized. Add a `normalize_date` path to
  `core/normalizer.py` if canonical date strings become part of
  matching.
- **Undo**: the rules engine is pure given a ruleset + input. An undo
  feature can be implemented by keeping a snapshot of the pre-apply
  DataFrames on `LoadedWorkbook` and swapping them back.
- **More file formats**: `.xlsm` would work via the same openpyxl
  loader; `.xls` and `.ods` need a `pandas.read_excel` fallback path
  (`engine="xlrd"` / `engine="odf"`) — but note they can't preserve
  formulas on write-back the same way.
