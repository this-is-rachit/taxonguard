"""Environmental outlier model: score occurrences against a taxon's own climate niche.

An isolation forest is fitted on the WorldClim bioclimatic columns (bio_1 to
bio_19) of a taxon's own records, so the taxon's realized climate envelope
defines what counts as normal. Each record then receives an environmental
outlier score: the further its climate sits from the taxon's typical conditions,
the higher the score. This follows the project's safety principle that each
species defines its own normal from its own data.

Records with no climate values (for example a point in the ocean, where
WorldClim has no land data) are left unscored here. They are caught instead by
the land or sea check (Phase 2, step 20), and the missing climate is itself a
signal there. The model is deterministic given a fixed random_state and learns
one taxon at a time. It is reusable: fit it on one set of records and score
another set (a future data drop, or an uploaded file) against the same envelope.

Score a cached taxon and print its most environmentally implausible records:

    uv run python -m taxonguard_core.engine.environment "Vulpes lagopus" --top 10
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..data.cache import load_cached
from ..data.worldclim import BIO_VARIABLES

# Columns added to a frame by scoring.
RAW_SCORE_COLUMN = "env_outlier_score"
NORM_SCORE_COLUMN = "env_outlier_normalized"
SCORED_COLUMN = "env_scored"

# Isolation forest defaults. n_estimators sits a little above the scikit-learn
# default for a steadier score; random_state makes every score reproducible.
DEFAULT_N_ESTIMATORS = 200
DEFAULT_RANDOM_STATE = 0


def _feature_columns(variables: tuple[int, ...]) -> list[str]:
    """Return the bio_* column names for the given WorldClim variable numbers."""
    return [f"bio_{variable}" for variable in variables]


def _feature_matrix(frame: pd.DataFrame, columns: list[str]) -> npt.NDArray[np.float64]:
    """Extract the climate columns of a frame as a float64 matrix."""
    return frame.loc[:, columns].to_numpy(dtype="float64")


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    """Raise KeyError if any required climate column is absent from the frame."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"frame is missing climate columns: {missing}")


def _add_unscored_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the three output columns with every record marked as unscored."""
    count = len(frame)
    frame[RAW_SCORE_COLUMN] = np.full(count, np.nan, dtype="float64")
    frame[NORM_SCORE_COLUMN] = np.full(count, np.nan, dtype="float64")
    frame[SCORED_COLUMN] = pd.Series(
        np.zeros(count, dtype=bool), index=frame.index, dtype="boolean"
    )
    return frame


@dataclass(frozen=True)
class EnvironmentalOutlierModel:
    """A fitted per-taxon environmental outlier model.

    Wraps an isolation forest fitted on a taxon's bioclimatic columns together
    with the training score range used to map new scores onto 0..1. Build it
    with fit_environmental_model, then call score on any frame that carries the
    same bio columns.
    """

    forest: IsolationForest
    variables: tuple[int, ...]
    train_score_min: float
    train_score_max: float

    @property
    def feature_columns(self) -> list[str]:
        """The bio_* column names this model reads."""
        return _feature_columns(self.variables)

    def _raw_scores(self, matrix: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        # score_samples is lower for more abnormal points. Negate it so that a
        # higher value means more outlying, the convention across the engine.
        return -np.asarray(self.forest.score_samples(matrix), dtype="float64")

    def _normalize(self, raw: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        spread = self.train_score_max - self.train_score_min
        if spread <= 0.0:
            return np.zeros_like(raw)
        return np.clip((raw - self.train_score_min) / spread, 0.0, 1.0)

    def score(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of frame with environmental outlier columns added.

        Adds env_outlier_score (raw, higher means more outlying),
        env_outlier_normalized (0..1 relative to the taxon the model was fitted
        on), and env_scored (False where the record had no complete climate
        data). Records with any missing climate value are left unscored.
        """
        out = frame.copy()
        _require_columns(out, self.feature_columns)
        count = len(out)

        raw = np.full(count, np.nan, dtype="float64")
        norm = np.full(count, np.nan, dtype="float64")
        scored = np.zeros(count, dtype=bool)

        if count:
            matrix = _feature_matrix(out, self.feature_columns)
            complete = ~np.isnan(matrix).any(axis=1)
            if bool(complete.any()):
                values = self._raw_scores(matrix[complete])
                raw[complete] = values
                norm[complete] = self._normalize(values)
                scored[complete] = True

        out[RAW_SCORE_COLUMN] = raw
        out[NORM_SCORE_COLUMN] = norm
        out[SCORED_COLUMN] = pd.Series(scored, index=out.index, dtype="boolean")
        return out


def fit_environmental_model(
    frame: pd.DataFrame,
    *,
    variables: tuple[int, ...] = BIO_VARIABLES,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    random_state: int = DEFAULT_RANDOM_STATE,
    contamination: float | str = "auto",
) -> EnvironmentalOutlierModel:
    """Fit an isolation forest on the complete-climate rows of frame.

    Rows with any missing bioclimatic value are excluded from fitting. Raises
    KeyError if the climate columns are absent, and ValueError if no row has a
    complete set of climate values, since there is then no niche to learn.
    """
    columns = _feature_columns(variables)
    _require_columns(frame, columns)

    matrix = _feature_matrix(frame, columns)
    complete = ~np.isnan(matrix).any(axis=1) if len(frame) else np.zeros(0, dtype=bool)
    if not bool(complete.any()):
        raise ValueError("no records with complete climate values to fit on")

    forest = IsolationForest(
        n_estimators=n_estimators,
        random_state=random_state,
        contamination=contamination,
    )
    forest.fit(matrix[complete])

    train_raw = -np.asarray(forest.score_samples(matrix[complete]), dtype="float64")
    return EnvironmentalOutlierModel(
        forest=forest,
        variables=variables,
        train_score_min=float(train_raw.min()),
        train_score_max=float(train_raw.max()),
    )


def score_environmental_outliers(
    frame: pd.DataFrame,
    *,
    variables: tuple[int, ...] = BIO_VARIABLES,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    random_state: int = DEFAULT_RANDOM_STATE,
    contamination: float | str = "auto",
) -> pd.DataFrame:
    """Fit a per-taxon model on frame and score the same frame.

    This is the common path for one cached taxon: the taxon's own records define
    its climate niche, and every record is scored against it. Returns a copy of
    frame with the environmental outlier columns added. A frame with no
    complete-climate records (for example only ocean points) is returned with
    the columns present and every record unscored, rather than raising.
    """
    columns = _feature_columns(variables)
    _require_columns(frame, columns)

    out = frame.copy()
    matrix = _feature_matrix(out, columns)
    complete = ~np.isnan(matrix).any(axis=1) if len(out) else np.zeros(0, dtype=bool)
    if not bool(complete.any()):
        return _add_unscored_columns(out)

    model = fit_environmental_model(
        out,
        variables=variables,
        n_estimators=n_estimators,
        random_state=random_state,
        contamination=contamination,
    )
    return model.score(out)


def _format_top(frame: pd.DataFrame, top: int) -> str:
    scored = frame[frame[SCORED_COLUMN].fillna(False).to_numpy(dtype=bool)]
    ranked = scored.sort_values(RAW_SCORE_COLUMN, ascending=False).head(top)
    preferred = [
        "gbif_id",
        "scientific_name",
        "decimal_latitude",
        "decimal_longitude",
        RAW_SCORE_COLUMN,
        NORM_SCORE_COLUMN,
    ]
    present = [column for column in preferred if column in ranked.columns]
    return ranked.loc[:, present].to_string(index=False)


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a cached taxon for environmental (climate) outliers."
    )
    parser.add_argument("taxon", help="Scientific name of a cached taxon.")
    parser.add_argument("--top", type=int, default=10, help="How many top outliers to show.")
    parser.add_argument(
        "--random-state", type=int, default=DEFAULT_RANDOM_STATE, help="Seed for the forest."
    )
    args = parser.parse_args()

    frame = load_cached(args.taxon)
    if frame is None:
        raise SystemExit(
            f"No cached dataset for {args.taxon!r}. Build it first with: "
            f'uv run python -m taxonguard_core.data.cache "{args.taxon}"'
        )

    scored = score_environmental_outliers(frame, random_state=args.random_state)
    n_scored = int(scored[SCORED_COLUMN].fillna(False).sum())
    print(f"{args.taxon}: {len(scored)} records, {n_scored} scored on climate")
    if n_scored:
        print(_format_top(scored, args.top))


if __name__ == "__main__":
    _main()
