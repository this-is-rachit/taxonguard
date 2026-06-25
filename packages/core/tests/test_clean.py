"""Tests for the clean-my-data engine path.

Network-free: the synthetic uploads carry a provided on_land column so the realm
check runs without the Natural Earth data, and the climate model is left off (no
WorldClim in the test environment), so the tests exercise the coordinate-quality
and realm checks deterministically.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from taxonguard_core.clean.cleaner import (
    FLAGGED_COLUMN,
    INSTITUTION_POINTS,
    UploadError,
    clean_occurrences,
    cleaned_csv,
    cleaned_frame,
    flagged_records,
    read_upload_csv,
)
from taxonguard_core.engine.fusion import SUSPICION_SCORE_COLUMN

# A raw-looking upload with GBIF column names, a provided on_land column, and one
# planted error of each coordinate-quality type plus an ocean (realm) error and a
# handful of plausible inland records for a terrestrial taxon.
_NHM_LONDON = INSTITUTION_POINTS[0]

_CSV = (
    "gbifID,scientificName,decimalLatitude,decimalLongitude,on_land,year\n"
    "1,Rana temporaria,51.50,-0.12,1,2019\n"
    "2,Rana temporaria,52.20,-1.10,1,2020\n"
    "3,Rana temporaria,0.0,0.0,0,2018\n"  # null island (also ocean)
    "4,Rana temporaria,45.5,45.5,1,2017\n"  # equal coordinates
    "5,Rana temporaria,40.0,-3.0,1,2016\n"  # gridded
    "6,Rana temporaria,12.34,-40.0,0,2015\n"  # ocean (realm mismatch)
    f"7,Rana temporaria,{_NHM_LONDON[0]},{_NHM_LONDON[1]},1,2021\n"  # institution
    "8,Rana temporaria,50.10,-2.30,1,2022\n"
    "9,Rana temporaria,49.90,-1.80,1,2022\n"
    "10,Rana temporaria,48.70,-0.50,1,2023\n"
)


def test_read_upload_maps_gbif_columns() -> None:
    frame = read_upload_csv(_CSV)
    assert len(frame) == 10
    for column in ("gbif_id", "scientific_name", "decimal_latitude", "decimal_longitude"):
        assert column in frame.columns
    # A provided on_land column is preserved for the realm check.
    assert "on_land" in frame.columns


def test_read_upload_accepts_tab_delimited() -> None:
    tsv = _CSV.replace(",", "\t")
    frame = read_upload_csv(tsv)
    assert len(frame) == 10
    assert "decimal_latitude" in frame.columns


def test_read_upload_accepts_generic_lat_lon_names() -> None:
    csv = "species,latitude,longitude\nVulpes lagopus,70.1,-50.2\nVulpes lagopus,71.0,-48.0\n"
    frame = read_upload_csv(csv)
    assert len(frame) == 2
    assert frame["scientific_name"].iloc[0] == "Vulpes lagopus"


def test_read_upload_without_coordinates_raises() -> None:
    with pytest.raises(UploadError):
        read_upload_csv("name,note\nFoo,bar\n")


def test_read_upload_empty_raises() -> None:
    with pytest.raises(UploadError):
        read_upload_csv("")


def test_clean_flags_each_issue_type() -> None:
    result = clean_occurrences(read_upload_csv(_CSV), run_environmental=False)
    summary = result.summary

    assert summary.total_records == 10
    assert summary.taxa == 1
    # The realm check runs because on_land was provided.
    assert "land/sea realm" in summary.checks_run
    # Five planted issues; records 8-10 and 1-2 are plausible.
    assert summary.flagged_records == 5
    assert summary.clean_records == 5

    issue_text = " ".join(summary.issues)
    assert "null-island" in issue_text
    assert "latitude equals longitude" in issue_text
    assert "whole-degree" in issue_text
    assert "realm mismatch" in issue_text
    assert "institution" in issue_text


def test_clean_marks_flagged_column_and_sorts() -> None:
    result = clean_occurrences(read_upload_csv(_CSV), run_environmental=False)
    assert FLAGGED_COLUMN in result.frame.columns

    ranked = flagged_records(result)
    scores = ranked[SUSPICION_SCORE_COLUMN].tolist()
    assert scores == sorted(scores, reverse=True)
    # The null-island-in-ocean record trips two checks, so it ranks at the top.
    assert ranked.iloc[0][SUSPICION_SCORE_COLUMN] >= 0.95

    limited = flagged_records(result, limit=2)
    assert len(limited) == 2


def test_cleaned_output_has_verdict_columns() -> None:
    result = clean_occurrences(read_upload_csv(_CSV), run_environmental=False)
    frame = cleaned_frame(result)
    for column in (FLAGGED_COLUMN, SUSPICION_SCORE_COLUMN, "suspicion_reasons"):
        assert column in frame.columns

    text = cleaned_csv(result)
    header = text.splitlines()[0]
    assert "flagged" in header
    assert "suspicion_score" in header
    # Never drops rows: every input record is present in the output.
    assert len(text.splitlines()) == 11  # header + 10 records


def test_clean_without_on_land_skips_realm_runs_coordinate_checks(tmp_path: Path) -> None:
    # No on_land column and an empty data directory (so the Natural Earth data is
    # not found): the realm check is skipped, but the coordinate-quality checks
    # still flag the obvious artifacts. Pointing at tmp_path keeps this
    # deterministic whether or not Natural Earth is installed on the machine.
    csv = (
        "scientificName,decimalLatitude,decimalLongitude\n"
        "Made up species,0.0,0.0\n"  # null island
        "Made up species,33.3,33.3\n"  # equal
        "Made up species,10.0,20.0\n"  # gridded
        "Made up species,12.34,56.78\n"  # plausible
    )
    result = clean_occurrences(read_upload_csv(csv), run_environmental=False, data_dir=tmp_path)
    assert "land/sea realm" not in result.summary.checks_run
    assert "coordinate quality" in result.summary.checks_run
    assert result.summary.flagged_records == 3


def test_clean_empty_frame() -> None:
    empty = pd.DataFrame(
        {
            "scientific_name": pd.Series(dtype="string"),
            "decimal_latitude": pd.Series(dtype="float64"),
            "decimal_longitude": pd.Series(dtype="float64"),
        }
    )
    result = clean_occurrences(empty, run_environmental=False)
    assert result.summary.total_records == 0
    assert result.summary.flagged_records == 0
