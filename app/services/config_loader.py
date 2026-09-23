import json
from pathlib import Path
from typing import List, Dict, Any
from app.config import settings
from app.utils.logger import logger


def load_all_sources(config_path: Path = None) -> List[Dict[str, Any]]:
    """Load the entire source repository JSON file."""
    target_path = config_path or settings.CONFIG_PATH
    if not target_path.exists():
        logger.error(f"Source repository configuration not found at: {target_path}")
        raise FileNotFoundError(f"Configuration file not found at: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError("Invalid source_repository.json structure. Must be a JSON array or object.")


def get_source_by_id(source_id: str, config_path: Path = None) -> Dict[str, Any]:
    """Retrieve a single source configuration by source_id."""
    sources = load_all_sources(config_path)
    for src in sources:
        if src.get("source_id") == source_id:
            return src
    raise ValueError(f"Source ID '{source_id}' not found in configuration repository.")