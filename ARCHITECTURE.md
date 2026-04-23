# Spreadsheet Cleaner - Architecture Summary

## Overview
A production-quality Streamlit web application for cleaning Excel spreadsheet data with professional desktop-style UI.

## Architecture Layers

### 1. Core Engine Layer (`core/`)
- **workbook_reader.py**: Handles file I/O for .xlsx/.csv files using openpyxl
- **scanner.py**: Scans workbooks and builds value-frequency index with location tracking
- **normalizer.py**: Conservative Unicode normalization (NFKC) with Arabic support
- **type_inference.py**: Infers column types (numeric, categorical, text, date, mixed)
- **rules_engine.py**: Applies cleaning rules with proper scope and match mode handling
- **preview_engine.py**: Generates before/after previews with change highlighting
- **stats_engine.py**: Computes descriptive statistics (workbook-level, per-column, before/after)
- **exporter.py**: Exports cleaned workbooks, statistics reports, and rulesets
- **ruleset_store.py**: Saves/loads rule configurations as JSON

### 2. Models Layer (`models/`)
- **schemas.py**: Pydantic/dataclass models for Rule, WorkbookMetadata, ColumnStats, etc.
- **enums.py**: Enum definitions for MatchMode, ScopeType, ActionType, ColumnType

### 3. UI Layer (`ui/`)
- **theme.py**: Custom CSS styling for premium desktop feel
- **layout.py**: Main layout components (top bar, left nav rail, workspace container)
- **upload_view.py**: File upload interface with drag-and-drop
- **scan_view.py**: Scan results with repeated values table and filters
- **rules_view.py**: Inline rule editor with scope/match mode controls
- **preview_view.py**: Before/after data preview with change highlighting
- **stats_view.py**: Descriptive statistics panels
- **export_view.py**: Export controls for workbook, stats, and rulesets

### 4. Tests Layer (`tests/`)
- Comprehensive test suite for matching safety, scope correctness, Arabic handling, statistics, and export

## Data Flow
1. User uploads file → workbook_reader loads into memory
2. scanner builds value-frequency index with location metadata
3. type_inference analyzes columns for statistics
4. User creates rules via rules_view → stored in session_state
5. rules_engine applies rules with proper precedence
6. preview_engine shows before/after comparison
7. stats_engine computes before/after statistics
8. exporter generates output files

## Key Design Decisions
- Whole-cell matching only (no substring replacement)
- Exact normalized matching by default
- Conservative Arabic normalization (no stemming/transliteration)
- Rule precedence: column > sheet > workbook scope
- Session-based state management for rules and previews
- Modular separation of UI and business logic
