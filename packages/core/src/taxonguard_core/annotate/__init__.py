"""Write confirmed rules back to GBIF's occurrence-annotation system (Phase 6).

A thin adapter behind one interface. The whole experimental-API surface lives in
``client.py``: an ``AnnotationClient`` protocol with two implementations, a
``GbifAnnotationClient`` that posts a confirmed rule to GBIF over HTTP Basic
Auth, and a ``NullAnnotationClient`` that produces a manual copy-and-paste
fallback when no credentials are configured. A GBIF API change touches only this
one shim.

Import from the module:

    from taxonguard_core.annotate.client import (
        AnnotationClient,
        AnnotationResult,
        GbifAnnotationClient,
        NullAnnotationClient,
    )
"""
