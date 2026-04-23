"""Exporter for cleaned workbooks, statistics, and rulesets."""

import json
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from models.schemas import Rule


def export_cleaned_workbook(sheets: Dict[str, pd.DataFrame], 
                            output_path: str) -> str:
    """
    Export cleaned data to Excel file.
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        output_path: Path for output file
        
    Returns:
        Path to exported file
    """
    output = Path(output_path)
    
    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to Excel
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            # Excel sheet names have 31 character limit
            safe_name = str(sheet_name)[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    
    return str(output)


def export_statistics_report(stats: Dict[str, Any], 
                             output_path: str,
                             format: str = "json") -> str:
    """
    Export statistics report to file.
    
    Args:
        stats: Statistics dict
        output_path: Path for output file
        format: Output format ("json" or "csv")
        
    Returns:
        Path to exported file
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "json":
        # Ensure JSON serializable
        clean_stats = make_json_serializable(stats)
        
        with open(output, "w", encoding="utf-8") as f:
            json.dump(clean_stats, f, indent=2, ensure_ascii=False)
    
    elif format == "csv":
        # Export column stats as CSV
        if "columns" in stats:
            df = pd.DataFrame(stats["columns"])
            df.to_csv(output, index=False, encoding="utf-8-sig")
        else:
            # Fallback: write JSON anyway
            clean_stats = make_json_serializable(stats)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(clean_stats, f, indent=2, ensure_ascii=False)
    
    return str(output)


def export_ruleset(rules: List[Rule], output_path: str) -> str:
    """
    Export cleaning rules to JSON file.
    
    Args:
        rules: List of Rule objects
        output_path: Path for output file
        
    Returns:
        Path to exported file
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    rules_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "rules_count": len(rules),
        "rules": [rule.to_dict() for rule in rules],
    }
    
    with open(output, "w", encoding="utf-8") as f:
        json.dump(rules_data, f, indent=2, ensure_ascii=False)
    
    return str(output)


def load_ruleset(input_path: str) -> List[Rule]:
    """
    Load cleaning rules from JSON file.
    
    Args:
        input_path: Path to ruleset file
        
    Returns:
        List of Rule objects
    """
    with open(input_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)
    
    rules = []
    for rule_dict in rules_data.get("rules", []):
        rules.append(Rule.from_dict(rule_dict))
    
    return rules


def make_json_serializable(obj: Any) -> Any:
    """
    Convert object to JSON-serializable form.
    
    Handles:
    - Sets -> lists
    - Non-serializable types -> strings
    - NaN/Inf -> None
    """
    import math
    
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    else:
        try:
            # Test if JSON serializable
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


def create_export_summary(sheets: Dict[str, pd.DataFrame],
                          rules: List[Rule],
                          stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of what will be exported.
    
    Args:
        sheets: Cleaned data
        rules: Applied rules
        stats: Statistics
        
    Returns:
        Summary dict
    """
    total_rows = sum(len(df) for df in sheets.values())
    total_columns = sum(len(df.columns) for df in sheets.values())
    
    return {
        "sheets_exported": list(sheets.keys()),
        "total_rows": total_rows,
        "total_columns": total_columns,
        "rules_applied": len([r for r in rules if r.enabled]),
        "statistics_generated": bool(stats),
        "export_timestamp": datetime.now().isoformat(),
    }
