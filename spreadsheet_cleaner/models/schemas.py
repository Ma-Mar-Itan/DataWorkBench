"""Schema definitions for the spreadsheet cleaner application."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime


@dataclass
class Rule:
    """A cleaning rule definition."""
    rule_id: str
    source_value: str
    target_value: str
    action_type: str  # "replace" or "set_blank"
    match_mode: str  # "exact_raw" or "exact_normalized"
    scope_type: str  # "workbook", "sheet", or "column"
    scope_sheet: Optional[str] = None
    scope_column: Optional[str] = None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for JSON serialization."""
        return {
            "rule_id": self.rule_id,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "action_type": self.action_type,
            "match_mode": self.match_mode,
            "scope_type": self.scope_type,
            "scope_sheet": self.scope_sheet,
            "scope_column": self.scope_column,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create a Rule from a dictionary."""
        return cls(
            rule_id=data["rule_id"],
            source_value=data["source_value"],
            target_value=data["target_value"],
            action_type=data["action_type"],
            match_mode=data["match_mode"],
            scope_type=data["scope_type"],
            scope_sheet=data.get("scope_sheet"),
            scope_column=data.get("scope_column"),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class ValueLocation:
    """Tracks where a value appears in the workbook."""
    sheet: str
    column: str
    row_index: int
    cell_value: Any


@dataclass
class ValueFrequency:
    """Frequency information for a unique value."""
    raw_value: str
    normalized_value: str
    total_count: int
    locations: List[ValueLocation] = field(default_factory=list)
    sheets: set = field(default_factory=set)
    columns: set = field(default_factory=set)
    is_likely_missing: bool = False
    inferred_type: str = "unknown"
    
    def __post_init__(self):
        if isinstance(self.sheets, list):
            self.sheets = set(self.sheets)
        if isinstance(self.columns, list):
            self.columns = set(self.columns)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "total_count": self.total_count,
            "sheets": list(self.sheets),
            "columns": list(self.columns),
            "is_likely_missing": self.is_likely_missing,
            "inferred_type": self.inferred_type,
            "sample_locations": [
                {"sheet": loc.sheet, "column": loc.column, "row": loc.row_index}
                for loc in self.locations[:5]  # Only include first 5 as samples
            ],
        }


@dataclass
class WorkbookMetadata:
    """Metadata about the uploaded workbook."""
    file_name: str
    num_sheets: int
    sheet_names: List[str]
    rows_per_sheet: Dict[str, int]
    columns_per_sheet: Dict[str, int]
    total_unique_values: int
    total_cells: int
    missing_token_count: int


@dataclass
class ColumnStats:
    """Statistics for a single column."""
    sheet: str
    column: str
    inferred_type: str
    count: int
    missing_count: int
    unique_count: int
    numeric_stats: Optional[Dict[str, float]] = None
    categorical_stats: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sheet": self.sheet,
            "column": self.column,
            "inferred_type": self.inferred_type,
            "count": self.count,
            "missing_count": self.missing_count,
            "unique_count": self.unique_count,
            "numeric_stats": self.numeric_stats,
            "categorical_stats": self.categorical_stats,
        }


@dataclass
class CleaningResult:
    """Results from applying cleaning rules."""
    total_changes: int
    affected_sheets: set
    affected_columns: set
    changes_by_rule: Dict[str, int]
    before_stats: Dict[str, Any]
    after_stats: Dict[str, Any]
    
    def __post_init__(self):
        if isinstance(self.affected_sheets, list):
            self.affected_sheets = set(self.affected_sheets)
        if isinstance(self.affected_columns, list):
            self.affected_columns = set(self.affected_columns)


@dataclass
class PreviewData:
    """Preview data for before/after comparison."""
    sheet: str
    original_df: Any  # pandas DataFrame
    cleaned_df: Any   # pandas DataFrame
    changed_cells: List[tuple]  # List of (row, col) tuples
    applied_rules: List[str]
