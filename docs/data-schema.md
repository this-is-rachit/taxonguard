# Cached per-taxon dataset schema

Each taxon dataset is built by `taxonguard_core.data.cache` and written to a
versioned parquet file under `data/cache/v{SCHEMA_VERSION}/<taxon_slug>.parquet`,
with a JSON metadata sidecar alongside it. The current `SCHEMA_VERSION` is 1.

## Columns

| Column | Type | Source | Meaning |
|---|---|---|---|
| `gbif_id` | Int64 | GBIF `key` | The GBIF occurrence id. |
| `scientific_name` | string | GBIF `scientificName` | Name as recorded. |
| `decimal_latitude` | float64 | GBIF | Latitude, validated to -90..90. |
| `decimal_longitude` | float64 | GBIF | Longitude, validated to -180..180. |
| `year` | Int64 | GBIF | Year of the record, may be missing. |
| `basis_of_record` | string | GBIF | For example HUMAN_OBSERVATION. |
| `country_code` | string | GBIF | ISO country code, may be missing. |
| `coordinate_uncertainty_m` | float64 | GBIF | Coordinate uncertainty in metres, may be missing. |
| `bio_1` ... `bio_19` | float64 | WorldClim 2.1 | The 19 bioclimatic variables, sampled at the point. NaN where there is no land climate (for example a point in the ocean). |
| `on_land` | boolean | Natural Earth | True if the point falls on land. |

Records without usable coordinates are dropped during ingestion, so every row has
a valid latitude and longitude. Duplicate `gbif_id` values are removed.

## Bioclimatic variables (WorldClim)

`bio_1` mean annual temperature, `bio_2` mean diurnal range, `bio_3`
isothermality, `bio_4` temperature seasonality, `bio_5` max temperature of
warmest month, `bio_6` min temperature of coldest month, `bio_7` temperature
annual range, `bio_8` to `bio_11` temperature of wettest, driest, warmest, and
coldest quarters, `bio_12` annual precipitation, `bio_13` to `bio_14`
precipitation of wettest and driest month, `bio_15` precipitation seasonality,
`bio_16` to `bio_19` precipitation of wettest, driest, warmest, and coldest
quarters. Temperatures are in degrees Celsius (WorldClim 2.1, sampled as stored).

## Metadata sidecar

The JSON sidecar records: `name`, `schema_version`, `record_count`,
`on_land_count`, `climate_variables`, `gbif_source`, `worldclim_resolution`, and
`created_utc`. When the GBIF download API is used for the final evaluation set,
the citable DOI will be added here.
