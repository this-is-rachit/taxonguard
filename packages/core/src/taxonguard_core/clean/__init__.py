"""Clean my data: run the detection engine on an uploaded occurrence file (Phase 8).

The same engine that flags GBIF records is applied to a file a user uploads (a
GBIF download or their own export). Every record is checked for coordinate-quality
problems and, where the data allows, for land/sea realm mismatch and climate
outliers; the suspect records are flagged with plain reasons and a suspicion
score, and an annotated, cleaned file is returned. Nothing is deleted: TaxonGuard
flags, it does not silently drop records.

    from taxonguard_core.clean.cleaner import clean_occurrences, read_upload_csv
"""
