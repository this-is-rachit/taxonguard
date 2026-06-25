# Data sources and licenses

Every data source TaxonGuard uses is free and openly licensed. This file records
each source, how it is accessed, and its license, to satisfy the Challenge
requirement to abide by data licenses and to cite sources.

## GBIF occurrence data

- What: species occurrence records.
- Access: two paths. The public GBIF REST API (https://api.gbif.org/v1), keyless,
  is used for development and iteration (`taxonguard_core.data.gbif`). The
  reproducible, citable evaluation set is fetched through the GBIF **download API**
  (`taxonguard_core.data.download`), which runs an asynchronous query against the
  full GBIF index over HTTP Basic Auth and mints a **DOI** for the result.
- Download query: an `and` predicate on `TAXON_KEY` (the backbone key for the
  taxon) AND `HAS_COORDINATE=true`, plus a `COUNTRY` (ISO 3166-1 alpha-2) or WKT
  geometry filter to cap the set to a few thousand records. The result is fetched
  in the `SIMPLE_CSV` format and mapped onto the tidy schema.
- Evaluation download (to be run live): the held-out real-data benchmark uses
  *Rana temporaria* (the canonical "frog in the ocean") restricted to one or a few
  countries. Run it with:

  ```
  uv run python -m taxonguard_core.data.download "Rana temporaria" \
      --country GB --username ACCOUNT --password SECRET --build
  ```

  This writes `data/real/rana_temporaria.parquet` plus a JSON sidecar carrying the
  assigned DOI and the exact predicate.
- License: individual datasets carry their own licenses (commonly CC0, CC BY, or
  CC BY-NC). A GBIF download bundles the constituent dataset citations and a DOI.
- Citation: GBIF.org (2026) GBIF Occurrence Download, **DOI:
  https://doi.org/10.15468/dl.bpfzpj** (*Rana temporaria*, Great Britain, with
  coordinates). The enrichment applies a small coastal buffer (about 5 km) to the
  land/sea flag so near-shore records are not misread as the open ocean.

## WorldClim 2.1 (climate)

- What: 19 bioclimatic variables (BIO1 to BIO19), 10 arc-minute resolution,
  GeoTIFF.
- Access: downloaded via `taxonguard_core.data.worldclim` from
  https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_bio.zip into a
  data directory kept out of Git.
- License: free for academic and other non-commercial use.
- Citation: Fick, S.E. and Hijmans, R.J. (2017) WorldClim 2: new 1-km spatial
  resolution climate surfaces for global land areas. International Journal of
  Climatology 37(12): 4302-4315.

## Natural Earth (land and sea)

- What: land polygons (50 m resolution) for the land or sea check.
- Access: downloaded via `taxonguard_core.data.naturalearth` from the
  natural-earth-vector repository into a data directory kept out of Git.
- License: public domain.
- Citation: Natural Earth, naturalearthdata.com.

## Notes

- No data is committed to Git. The `data/` directory is ignored. Each source is
  reacquired by its documented script or API call, which keeps the repository
  small and the pipeline reproducible.
