"""Runtime configuration loading for projection."""

from __future__ import annotations

import json
from pathlib import Path

from .config import ProjectionConfig


class ProjectionConfigLoader:
    """Read projection configuration from a local JSON file."""

    def load(self, config_path: str | Path | None = None) -> ProjectionConfig:
        """Return projection configuration from disk or defaults when no path is provided."""
        if config_path is None:
            return ProjectionConfig()

        path = Path(config_path)
        with path.open("r", encoding="utf-8") as file_handle:
            raw_config = json.load(file_handle)

        return ProjectionConfig.model_validate(raw_config)
