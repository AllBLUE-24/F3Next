"""Backward-compatible re-exports — canonical implementation in corpus.enrich_understanding."""
from containers.implementation.corpus.enrich_understanding import (  # noqa: F401
    EnrichCorpusUnderstandingInput,
    enrich_corpus_understanding,
)
from containers.implementation.corpus.discovery_context import (  # noqa: F401
    extract_discovery_context as _extract_discovery_context,
)
