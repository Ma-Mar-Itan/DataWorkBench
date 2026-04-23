"""Ruleset store for saving and loading rule configurations."""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from models.schemas import Rule


DEFAULT_RULESET_DIR = Path("./rulesets")


def save_ruleset(rules: List[Rule], 
                 name: str,
                 ruleset_dir: Optional[Path] = None) -> str:
    """
    Save a ruleset to file.
    
    Args:
        rules: List of rules to save
        name: Name for the ruleset file
        ruleset_dir: Directory to save rulesets (default: ./rulesets)
        
    Returns:
        Path to saved file
    """
    if ruleset_dir is None:
        ruleset_dir = DEFAULT_RULESET_DIR
    
    ruleset_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    filename = f"{safe_name}_{timestamp}.json" if safe_name else f"ruleset_{timestamp}.json"
    filepath = ruleset_dir / filename
    
    # Prepare ruleset data
    ruleset_data = {
        "name": name or "Untitled Ruleset",
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "rules_count": len(rules),
        "rules": [rule.to_dict() for rule in rules],
    }
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ruleset_data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def load_ruleset(filepath: str) -> List[Rule]:
    """
    Load rules from a ruleset file.
    
    Args:
        filepath: Path to ruleset file
        
    Returns:
        List of Rule objects
    """
    with open(filepath, "r", encoding="utf-8") as f:
        ruleset_data = json.load(f)
    
    rules = []
    for rule_dict in ruleset_data.get("rules", []):
        try:
            rule = Rule.from_dict(rule_dict)
            rules.append(rule)
        except (KeyError, ValueError) as e:
            # Skip invalid rules
            print(f"Warning: Skipping invalid rule: {e}")
    
    return rules


def list_rulesets(ruleset_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    List available rulesets.
    
    Args:
        ruleset_dir: Directory containing rulesets (default: ./rulesets)
        
    Returns:
        List of ruleset metadata dicts
    """
    if ruleset_dir is None:
        ruleset_dir = DEFAULT_RULESET_DIR
    
    if not ruleset_dir.exists():
        return []
    
    rulesets = []
    for filepath in sorted(ruleset_dir.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            rulesets.append({
                "filename": filepath.name,
                "filepath": str(filepath),
                "name": data.get("name", "Unknown"),
                "created_at": data.get("created_at", "Unknown"),
                "rules_count": data.get("rules_count", 0),
            })
        except (json.JSONDecodeError, IOError):
            continue
    
    return rulesets


def delete_ruleset(filepath: str) -> bool:
    """
    Delete a ruleset file.
    
    Args:
        filepath: Path to ruleset file
        
    Returns:
        True if deleted successfully
    """
    try:
        path = Path(filepath)
        if path.exists():
            path.unlink()
            return True
        return False
    except OSError:
        return False


def get_ruleset_preview(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Get a preview of a ruleset without fully loading it.
    
    Args:
        filepath: Path to ruleset file
        
    Returns:
        Dict with basic ruleset info or None if error
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            "name": data.get("name", "Unknown"),
            "created_at": data.get("created_at", "Unknown"),
            "rules_count": data.get("rules_count", 0),
            "rule_summaries": [
                {
                    "source": r.get("source_value", ""),
                    "target": r.get("target_value", ""),
                    "scope": r.get("scope_type", ""),
                }
                for r in data.get("rules", [])[:10]  # First 10 rules only
            ],
        }
    except (json.JSONDecodeError, IOError, KeyError):
        return None
