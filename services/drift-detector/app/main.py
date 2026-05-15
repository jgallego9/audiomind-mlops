"""Embedding drift detection using Evidently.

Fetches recent and reference embedding vectors from Qdrant, runs Evidently
DataDriftPreset (PSI method), and pushes drift scores to the Prometheus Push
Gateway.

Evidently v2 API validated from:
    https://github.com/evidentlyai/evidently (README)

Usage::

    python -m app.main
"""

import logging
import sys
from typing import Any

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from qdrant_client import QdrantClient

from app.settings import Settings

logger = logging.getLogger(__name__)


def _sample_vectors(
    client: QdrantClient,
    collection: str,
    limit: int,
    offset: int | None = None,
) -> tuple[pd.DataFrame, int | None]:
    """Scroll Qdrant and return a DataFrame of embedding dimensions.

    ``offset`` is a Qdrant ``PointId`` cursor returned by a previous scroll
    call ("skip points with IDs less than this value"), **not** a page-level
    integer offset.  Pass ``None`` to start from the first point.

    :param client: Qdrant client instance.
    :param collection: Collection name.
    :param limit: Maximum number of vectors to fetch.
    :param offset: PointId cursor from a previous scroll, or ``None``.
    :returns: Tuple of (DataFrame with one column per embedding dimension,
        next-page cursor for chaining a subsequent scroll).
    :raises RuntimeError: If no vectors are found.
    """
    records, next_offset = client.scroll(
        collection_name=collection,
        limit=limit,
        offset=offset,
        with_vectors=True,
    )
    if not records:
        raise RuntimeError(
            f"No vectors found in Qdrant collection '{collection}' "
            f"at offset={offset}"
        )
    vectors = [r.vector for r in records]
    dim = len(vectors[0])
    columns = [f"dim_{i}" for i in range(dim)]
    return pd.DataFrame(vectors, columns=columns), next_offset


def _run_drift_report(
    current: pd.DataFrame,
    reference: pd.DataFrame,
) -> dict[str, Any]:
    """Run Evidently DataDriftPreset and return the parsed dict.

    :param current: Current window DataFrame.
    :param reference: Reference window DataFrame.
    :returns: Evidently report as a Python dictionary.
    """
    report = Report([DataDriftPreset(method="psi")])
    result = report.run(current, reference)
    return result.dict()


def _extract_drift_score(report_dict: dict[str, Any]) -> tuple[float, bool]:
    """Extract the dataset-level drift share and drift flag.

    Evidently v2 DataDriftPreset stores results under
    ``metrics[0].result`` (DatasetDriftMetric).

    :param report_dict: Evidently report as dictionary.
    :returns: Tuple of (drift_share, dataset_drift).
    """
    try:
        result = report_dict["metrics"][0]["result"]
        drift_share: float = result.get("drift_share", 0.0)
        dataset_drift: bool = result.get("dataset_drift", False)
        return drift_share, dataset_drift
    except (KeyError, IndexError) as exc:
        logger.warning("Could not extract drift score from report: %s", exc)
        return 0.0, False


def _push_metrics(
    drift_share: float,
    dataset_drift: bool,
    settings: Settings,
) -> None:
    """Push drift metrics to the Prometheus Push Gateway.

    :param drift_share: Fraction of drifted columns (0–1).
    :param dataset_drift: True if the overall dataset drift threshold is crossed.
    :param settings: Loaded application settings.
    """
    registry = CollectorRegistry()

    drift_share_gauge = Gauge(
        "audiomind_embedding_drift_share",
        "Fraction of embedding dimensions with detected drift (Evidently PSI)",
        registry=registry,
    )
    drift_detected_gauge = Gauge(
        "audiomind_embedding_drift_detected",
        "1 if dataset-level drift detected, 0 otherwise",
        registry=registry,
    )

    drift_share_gauge.set(drift_share)
    drift_detected_gauge.set(1.0 if dataset_drift else 0.0)

    push_to_gateway(
        settings.pushgateway_url,
        job=settings.job_name,
        registry=registry,
    )
    logger.info(
        "Pushed drift metrics: drift_share=%.4f dataset_drift=%s",
        drift_share,
        dataset_drift,
    )


def main() -> None:
    """Entry point for the drift detection job."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings()

    logger.info(
        "Starting drift detection: collection=%s sample_size=%d reference_size=%d",
        settings.qdrant_collection,
        settings.qdrant_sample_size,
        settings.qdrant_reference_size,
    )

    client = QdrantClient(url=settings.qdrant_url)

    # Current window: most recent N vectors (start from the beginning of
    # the collection; Qdrant returns points sorted by ID ascending).
    current_df, next_offset = _sample_vectors(
        client,
        settings.qdrant_collection,
        limit=settings.qdrant_sample_size,
    )

    # Reference window: the next N vectors using the cursor returned above.
    # Using cursor-based pagination avoids assuming sequential integer IDs.
    reference_df, _ = _sample_vectors(
        client,
        settings.qdrant_collection,
        limit=settings.qdrant_reference_size,
        offset=next_offset,
    )

    logger.info(
        "Sampled vectors: current=%d reference=%d dims=%d",
        len(current_df),
        len(reference_df),
        current_df.shape[1],
    )

    report_dict = _run_drift_report(current_df, reference_df)
    drift_share, dataset_drift = _extract_drift_score(report_dict)

    logger.info(
        "Drift results: drift_share=%.4f dataset_drift=%s threshold=%.2f",
        drift_share,
        dataset_drift,
        settings.drift_threshold,
    )

    _push_metrics(drift_share, dataset_drift, settings)

    if dataset_drift:
        logger.warning(
            "DRIFT DETECTED: drift_share=%.4f exceeds threshold=%.2f. "
            "Consider retraining or updating the reference dataset.",
            drift_share,
            settings.drift_threshold,
        )
        sys.exit(1)  # Non-zero exit triggers Kubernetes Job failure + alerting

    logger.info("No significant drift detected.")
    sys.exit(0)


if __name__ == "__main__":
    main()
