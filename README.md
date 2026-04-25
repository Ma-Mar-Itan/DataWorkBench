# [Currently Broken] Spreadsheet Cleaner

A professional Streamlit web application for cleaning Excel spreadsheet data with a premium desktop-style UI.

## Features

- **Upload Workbooks**: Support for `.xlsx` and `.csv` files
- **Scan & Analyze**: Automatic scanning of all sheets with value frequency analysis
- **Inline Cleaning Rules**: Create replacement rules with workbook/sheet/column scope
- **Safe Matching**: Whole-cell matching only (no substring replacement)
- **Arabic Support**: Full Unicode support with proper Arabic text handling
- **Descriptive Statistics**: Automatic generation of workbook and column statistics
- **Before/After Preview**: Review changes before exporting
- **Export Options**: Export cleaned workbook, statistics report, and rulesets

## Installation

```bash
cd spreadsheet_cleaner
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

## Project Structure

```
spreadsheet_cleaner/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── core/                 # Business logic modules
│   ├── __init__.py
│   ├── normalizer.py     # Unicode normalization with Arabic support
│   ├── workbook_reader.py # File I/O for Excel/CSV
│   ├── scanner.py        # Value frequency scanning
│   ├── type_inference.py # Column type detection
│   ├── rules_engine.py   # Rule application logic
│   ├── preview_engine.py # Before/after preview generation
│   ├── stats_engine.py   # Statistics generation
│   ├── exporter.py       # Export functionality
│   └── ruleset_store.py  # Ruleset save/load
├── models/               # Data models
│   ├── __init__.py
│   ├── enums.py          # Enum definitions
│   └── schemas.py        # Data classes
├── ui/                   # User interface components
│   ├── __init__.py
│   ├── theme.py          # Custom CSS styling
│   ├── layout.py         # Layout components
│   ├── upload_view.py    # Upload page
│   ├── scan_view.py      # Scan results page
│   ├── rules_view.py     # Rules editor page
│   ├── preview_view.py   # Preview page
│   ├── stats_view.py     # Statistics page
│   └── export_view.py    # Export page
└── tests/                # Test suite
    ├── __init__.py
    ├── test_normalizer.py
    ├── test_rules_engine.py
    └── test_arabic_cases.py
```

## Usage Guide

### 1. Upload Workbook
- Navigate to the "Upload" section
- Drag and drop or select an `.xlsx` or `.csv` file
- The workbook will be automatically scanned

### 2. Review Scan Results
- View unique values and their frequencies
- Filter by sheet or search for specific values
- Identify missing token variants

### 3. Create Cleaning Rules
- Select a value to replace from the dropdown
- Enter the replacement value
- Choose scope: Workbook, Sheet, or Column
- Select match mode: Normalized (recommended) or Raw
- Add multiple rules as needed

### 4. Preview Changes
- Review before/after comparison
- See highlighted changed cells
- Verify rules are working correctly

### 5. View Statistics
- Workbook-level summary
- Per-column statistics
- Missing token analysis
- Before/after comparison

### 6. Export
- Download cleaned workbook (.xlsx)
- Export statistics report (JSON or CSV)
- Save ruleset for reuse

## Design Philosophy

The UI is inspired by modern productivity applications with:
- Clean, professional aesthetic
- Soft gray backgrounds with white panels
- Subtle borders and shadows
- Clear visual hierarchy
- Responsive layout with left navigation rail
- Premium desktop-tool feel

## Key Technical Decisions

### Safe Matching
- **Whole-cell matching only**: Replacing "Home" will NOT affect "Homework"
- **Normalized matching by default**: Case-insensitive for Latin, preserves Arabic
- **No substring replacement**: Prevents accidental data corruption

### Arabic Support
- Unicode NFKC normalization
- Tatweel (elongation) removal
- Whitespace normalization
- Preservation of Arabic letters
- Proper RTL display support

### Rule Precedence
1. Column scope (highest priority)
2. Sheet scope
3. Workbook scope (lowest priority)

Within same scope:
1. Exact raw match
2. Exact normalized match

## Running Tests

```bash
pytest tests/ -v
```

## Requirements

- Python 3.9+
- Streamlit 1.32.0
- pandas 2.2.0
- openpyxl 3.1.2
- pydantic 2.6.0
- numpy 1.26.3

## License

MIT License
