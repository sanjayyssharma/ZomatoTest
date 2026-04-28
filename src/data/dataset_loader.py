from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def load_raw_dataset(
    *,
    dataset_name: str,
    split: str,
    hf_cache_dir: Path,
    allow_download: bool,
) -> "Dataset":
    """
    Load the raw Hugging Face dataset (Phase 0).

    If allow_download is False, this will fail unless the dataset is already present in cache_dir.
    """
    hf_cache_dir.mkdir(parents=True, exist_ok=True)

    # Force Hugging Face hub + datasets caches into the workspace to avoid permission
    # issues writing to ~/.cache on locked-down environments.
    os.environ["HF_HOME"] = str(hf_cache_dir)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_cache_dir / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(hf_cache_dir / "datasets")
    os.environ["XDG_CACHE_HOME"] = str(hf_cache_dir / "xdg_cache")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    # Import after env vars are set so huggingface_hub picks up our cache paths.
    from datasets import Dataset, load_dataset  # type: ignore

    download_mode: Any | None = None
    if not allow_download:
        # In datasets, "reuse_dataset_if_exists" avoids downloading when already cached.
        # If not cached, it will raise.
        download_mode = "reuse_dataset_if_exists"

    return load_dataset(
        path=dataset_name,
        split=split,
        cache_dir=str(hf_cache_dir),
        download_mode=download_mode,
    )

