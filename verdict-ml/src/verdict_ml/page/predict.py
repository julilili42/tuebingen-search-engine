from __future__ import annotations

from pathlib import Path

from ..base import VerdictPrediction, VerdictPredictor
from ..paths import ARTIFACTS_DIR
from .features import make_text

DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "page_verdict.joblib"

PageVerdictPrediction = VerdictPrediction


class PageVerdictPredictor(VerdictPredictor):
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        super().__init__(model_path, make_text)


_DEFAULT_PREDICTOR: PageVerdictPredictor | None = None


def get_default_predictor() -> PageVerdictPredictor:
    global _DEFAULT_PREDICTOR
    if _DEFAULT_PREDICTOR is None:
        _DEFAULT_PREDICTOR = PageVerdictPredictor()
    return _DEFAULT_PREDICTOR
