from pathlib import Path

import pytest

from verdict_ml.base import load_bundle


def test_load_bundle_reports_missing_artifact(tmp_path: Path):
    missing = tmp_path / "missing.joblib"

    with pytest.raises(FileNotFoundError, match="Verdict model artifact not found"):
        load_bundle(missing)
