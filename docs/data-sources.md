# Data sources and licenses

Every data source TaxonGuard uses is free and openly licensed. This file records
each source, how it is accessed, and its license, to satisfy the Challenge
requirement to abide by data licenses and to cite sources.

## GBIF occurrence data

- What: species occurrence records.
- Access: the public GBIF REST API (https://api.gbif.org/v1), keyless, for
  development and iteration. For the final reproducible dataset the GBIF download
  or SQL API will be used, which yields a citable DOI.
- License: individual datasets carry their own licenses (commonly CC0, CC BY, or
  CC BY-NC). A GBIF download bundles the constituent dataset citations and a DOI.
  The DOI and citation will be recorded here when the evaluation dataset is
  locked.
- Citation: GBIF.org occurrence download DOI (to be added).

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

## Natural Earth (land and sea, planned)

- What: land and ocean polygons for the land or sea and habitat check.
- Access: to be added in the next step.
- License: public domain.
- Citation: Natural Earth, naturalearthdata.com.

## Notes

- No data is committed to Git. The `data/` directory is ignored. Each source is
  reacquired by its documented script or API call, which keeps the repository
  small and the pipeline reproducible.
