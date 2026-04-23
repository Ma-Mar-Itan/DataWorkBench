"""Core module __init__.py"""

from .normalizer import normalize_value, is_likely_missing, infer_value_type
from .workbook_reader import load_workbook, save_workbook
from .scanner import (
    scan_workbook,
    get_value_locations,
    filter_values_by_sheet,
    filter_values_by_column,
    search_values,
    get_repeated_values,
    get_missing_candidates,
    get_categorical_values,
)
from .type_inference import (
    infer_column_type,
    compute_numeric_stats,
    compute_categorical_stats,
    compute_column_stats,
    compute_all_column_stats,
)
from .rules_engine import (
    apply_rules,
    sort_rules_by_precedence,
    rule_matches,
    count_changes,
    get_changes_by_rule,
)
from .preview_engine import (
    generate_preview,
    find_changed_cells,
    create_highlighted_preview,
    get_change_summary,
)
from .stats_engine import (
    generate_workbook_stats,
    generate_column_stats,
    generate_before_after_stats,
    generate_full_statistics_report,
    get_missing_token_summary,
)
from .exporter import (
    export_cleaned_workbook,
    export_statistics_report,
    export_ruleset,
    load_ruleset,
    make_json_serializable,
    create_export_summary,
)
from .ruleset_store import (
    save_ruleset,
    load_ruleset as load_ruleset_from_store,
    list_rulesets,
    delete_ruleset,
    get_ruleset_preview,
)

__all__ = [
    # Normalizer
    "normalize_value",
    "is_likely_missing",
    "infer_value_type",
    # Workbook Reader
    "load_workbook",
    "save_workbook",
    # Scanner
    "scan_workbook",
    "get_value_locations",
    "filter_values_by_sheet",
    "filter_values_by_column",
    "search_values",
    "get_repeated_values",
    "get_missing_candidates",
    "get_categorical_values",
    # Type Inference
    "infer_column_type",
    "compute_numeric_stats",
    "compute_categorical_stats",
    "compute_column_stats",
    "compute_all_column_stats",
    # Rules Engine
    "apply_rules",
    "sort_rules_by_precedence",
    "rule_matches",
    "count_changes",
    "get_changes_by_rule",
    # Preview Engine
    "generate_preview",
    "find_changed_cells",
    "create_highlighted_preview",
    "get_change_summary",
    # Stats Engine
    "generate_workbook_stats",
    "generate_column_stats",
    "generate_before_after_stats",
    "generate_full_statistics_report",
    "get_missing_token_summary",
    # Exporter
    "export_cleaned_workbook",
    "export_statistics_report",
    "export_ruleset",
    "make_json_serializable",
    "create_export_summary",
    # Ruleset Store
    "save_ruleset",
    "load_ruleset_from_store",
    "list_rulesets",
    "delete_ruleset",
    "get_ruleset_preview",
]
