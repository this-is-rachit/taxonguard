from __future__ import annotations

import pandas as pd

from taxonguard_core.engine.deterministic import (
    DET_FLAG_COLUMN,
    DET_REASONS_COLUMN,
    DETERMINISTIC_FLAG_COLUMNS,
    EQUAL_COORDINATES,
    GRIDDED_COORDINATES,
    INSTITUTION_COORDINATES,
    REALM_MISMATCH,
    ZERO_COORDINATES,
    add_deterministic_flags,
    realm_for,
)


def _frame(lats: list[float], lons: list[float], on_land: list[bool] | None = None) -> pd.DataFrame:
    data: dict[str, object] = {
        "gbif_id": list(range(1, len(lats) + 1)),
        "decimal_latitude": lats,
        "decimal_longitude": lons,
    }
    if on_land is not None:
        data["on_land"] = pd.array(on_land, dtype="boolean")
    return pd.DataFrame(data)


def test_realm_mismatch_for_land_taxon_in_the_sea() -> None:
    frame = _frame([10.0, 11.0], [20.0, 21.0], on_land=[True, False])
    out = add_deterministic_flags(frame, expected_realm="terrestrial")
    flags = out[f"det_{REALM_MISMATCH}"].tolist()
    assert flags == [False, True]  # the off-land land animal is flagged


def test_freshwater_in_ocean_is_flagged() -> None:
    frame = _frame([5.0], [5.0001], on_land=[False])
    out = add_deterministic_flags(frame, expected_realm="freshwater")
    assert bool(out.loc[0, f"det_{REALM_MISMATCH}"])


def test_marine_taxon_on_land_is_flagged() -> None:
    frame = _frame([1.0], [2.0], on_land=[True])
    out = add_deterministic_flags(frame, expected_realm="marine")
    assert bool(out.loc[0, f"det_{REALM_MISMATCH}"])


def test_realm_check_skipped_without_realm_or_on_land() -> None:
    # No realm given.
    frame = _frame([1.0], [2.0], on_land=[False])
    out = add_deterministic_flags(frame)
    assert not bool(out.loc[0, f"det_{REALM_MISMATCH}"])
    # Realm given but no on_land column.
    frame2 = _frame([1.0], [2.0])
    out2 = add_deterministic_flags(frame2, expected_realm="terrestrial")
    assert not bool(out2.loc[0, f"det_{REALM_MISMATCH}"])


def test_zero_coordinates_flagged_alone() -> None:
    out = add_deterministic_flags(_frame([0.0], [0.0]))
    assert bool(out.loc[0, f"det_{ZERO_COORDINATES}"])
    # Null island must not also count as equal or gridded.
    assert not bool(out.loc[0, f"det_{EQUAL_COORDINATES}"])
    assert not bool(out.loc[0, f"det_{GRIDDED_COORDINATES}"])
    assert out.loc[0, DET_REASONS_COLUMN] == ZERO_COORDINATES


def test_equal_coordinates_flagged() -> None:
    out = add_deterministic_flags(_frame([12.34], [12.34]))
    assert bool(out.loc[0, f"det_{EQUAL_COORDINATES}"])
    assert not bool(out.loc[0, f"det_{GRIDDED_COORDINATES}"])


def test_gridded_coordinates_flagged() -> None:
    out = add_deterministic_flags(_frame([3.0, 3.14], [7.0, 7.2]))
    assert bool(out.loc[0, f"det_{GRIDDED_COORDINATES}"])  # whole degrees
    assert not bool(out.loc[1, f"det_{GRIDDED_COORDINATES}"])  # real precision


def test_institution_coordinates_flagged_within_tolerance() -> None:
    # First point sits on the reference, second is far away.
    frame = _frame([48.8566, 10.0], [2.3522, 50.0])
    out = add_deterministic_flags(
        frame,
        institution_points=[(48.8566, 2.3522)],
        institution_tolerance_deg=0.01,
    )
    assert bool(out.loc[0, f"det_{INSTITUTION_COORDINATES}"])
    assert not bool(out.loc[1, f"det_{INSTITUTION_COORDINATES}"])


def test_aggregate_flag_and_reasons() -> None:
    # Row 0: clean. Row 1: gridded. Row 2: zero.
    out = add_deterministic_flags(_frame([10.27, 4.0, 0.0], [33.41, 9.0, 0.0]))
    assert out[DET_FLAG_COLUMN].tolist() == [False, True, True]
    assert out.loc[0, DET_REASONS_COLUMN] == ""
    assert GRIDDED_COORDINATES in out.loc[1, DET_REASONS_COLUMN]
    assert out.loc[2, DET_REASONS_COLUMN] == ZERO_COORDINATES


def test_flag_columns_are_boolean_and_reasons_string() -> None:
    out = add_deterministic_flags(_frame([1.0], [2.0]))
    for column in DETERMINISTIC_FLAG_COLUMNS:
        assert str(out[column].dtype) == "boolean"
    assert str(out[DET_FLAG_COLUMN].dtype) == "boolean"
    assert str(out[DET_REASONS_COLUMN].dtype) == "string"


def test_empty_frame_gets_columns() -> None:
    frame = pd.DataFrame(
        {
            "gbif_id": pd.Series([], dtype="Int64"),
            "decimal_latitude": pd.Series([], dtype="float64"),
            "decimal_longitude": pd.Series([], dtype="float64"),
        }
    )
    out = add_deterministic_flags(frame, expected_realm="terrestrial")
    assert len(out) == 0
    for column in (*DETERMINISTIC_FLAG_COLUMNS, DET_FLAG_COLUMN, DET_REASONS_COLUMN):
        assert column in out.columns


def test_realm_for_known_and_unknown() -> None:
    assert realm_for("Rana temporaria") == "freshwater"
    assert realm_for("Panthera leo") == "terrestrial"
    assert realm_for("Notataxon notaname") is None
