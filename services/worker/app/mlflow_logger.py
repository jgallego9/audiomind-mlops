"""Inference metrics logger — persists per-job metrics to MLflow.

Each completed (or failed) inference job logs a run under the configured
experiment.  The run is tagged with the model name and version so that
runs can be filtered by model in the MLflow UI.

All MLflow calls are synchronous (mlflow SDK is not async-aware), so they
are executed in the default executor to avoid blocking the event loop.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import mlflow

from app.config import Settings

logger = logging.getLogger(__name__)

# Single-thread executor: MLflow tracking calls must be serialised to avoid
# concurrent run context conflicts inside the SDK.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlflow-logger")


def _log_run_sync(
    settings: Settings,
    job_id: str,
    duration_seconds: float,
    status: str,
    *,
    tokens_per_second: float | None = None,
    error_type: str | None = None,
) -> None:
    """Synchronous MLflow logging — runs inside the thread executor."""
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        with mlflow.start_run(run_name=f"job-{job_id}"):
            mlflow.set_tags(
                {
                    "model.name": settings.mlflow_model_name,
                    "model.version": settings.mlflow_model_version,
                    "job.id": job_id,
                    "job.status": status,
                }
            )
            mlflow.log_metric("duration_seconds", duration_seconds)
            mlflow.log_metric("success", 1.0 if status == "completed" else 0.0)
            if tokens_per_second is not None:
                mlflow.log_metric("tokens_per_second", tokens_per_second)
            if error_type:
                mlflow.log_param("error_type", error_type)
    except Exception:  # noqa: BLE001
        # MLflow logging is best-effort — never fail the inference job.
        logger.warning("mlflow_log_failed job_id=%s", job_id, exc_info=True)


async def log_inference_metrics(
    settings: Settings,
    job_id: str,
    duration_seconds: float,
    status: str,
    *,
    tokens_per_second: float | None = None,
    error_type: str | None = None,
) -> None:
    """Async wrapper — offloads the sync MLflow call to the thread executor.

    :param settings: Application settings (tracking URI, model name/version).
    :param job_id: Unique identifier of the inference job.
    :param duration_seconds: Wall-clock time for the job.
    :param status: ``"completed"`` or ``"failed"``.
    :param tokens_per_second: Optional throughput estimate from the processor.
    :param error_type: Exception class name when *status* is ``"failed"``.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        _executor,
        lambda: _log_run_sync(
            settings,
            job_id,
            duration_seconds,
            status,
            tokens_per_second=tokens_per_second,
            error_type=error_type,
        ),
    )
