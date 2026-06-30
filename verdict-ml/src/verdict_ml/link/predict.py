from __future__ import annotations

from pathlib import Path

from ..base import VerdictPrediction, VerdictPredictor
from ..paths import ARTIFACTS_DIR
from .features import make_text

DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "link_verdict.joblib"

LinkVerdictPrediction = VerdictPrediction


class LinkVerdictPredictor(VerdictPredictor):
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        super().__init__(model_path, make_text)
