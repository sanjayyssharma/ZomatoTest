from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """
    Minimal settings container (Phase 0).

    Uses environment variables when present, otherwise defaults.
    """

    def __init__(self) -> None:
        self.dataset_name: str = os.getenv(
            "DATASET_NAME",
            "ManikaSaini/zomato-restaurant-recommendation",
        )
        self.dataset_split: str = os.getenv("DATASET_SPLIT", "train")

        self.workspace_dir: Path = Path.cwd()
        self.artifacts_dir: Path = Path(os.getenv("ARTIFACTS_DIR", str(self.workspace_dir / "artifacts")))
        self.hf_cache_dir: Path = Path(os.getenv("HF_CACHE_DIR", str(self.workspace_dir / ".hf_cache")))

