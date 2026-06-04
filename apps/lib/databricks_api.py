"""
apps/lib/databricks_api.py
--------------------------
Wrappers for the Databricks REST APIs used by DocuBricks apps.

Covered APIs
~~~~~~~~~~~~
- Files API  (``/api/2.0/fs/files``)   – upload documents to UC Volumes
- Jobs API   (``/api/2.1/jobs/run-now``) – trigger the DLT pipeline
- Jobs Runs API (``/api/2.1/jobs/runs/get``) – poll job run status

Environment variables required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``DATABRICKS_HOST``     – workspace URL (``https://…``)
``DATABRICKS_TOKEN``    – PAT or OAuth token
``PIPELINE_JOB_ID``     – Databricks Jobs ID for the main DLT pipeline
"""
from __future__ import annotations

import os

import httpx


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_VOLUME_ROOT = "/Volumes/docubricks_prod/raw_landing/documents"


def _base_url() -> str:
    return os.environ["DATABRICKS_HOST"].rstrip("/")


def _headers(content_type: str = "application/json") -> dict[str, str]:
    token = os.environ["DATABRICKS_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
    }


# ---------------------------------------------------------------------------
# Files API
# ---------------------------------------------------------------------------

def upload_to_volume(
    file_bytes: bytes,
    document_id: str,
    tenant_id: str,
    vertical: str,
    file_ext: str,
) -> str:
    """
    Upload *file_bytes* to the Unity Catalog Volume path for the given document.

    The destination path follows the convention::

        /Volumes/docubricks_prod/raw_landing/documents/{tenant_id}/{vertical}/{document_id}.{file_ext}

    Parameters
    ----------
    file_bytes:   raw file content
    document_id:  SHA-256 hex string (used as the filename)
    tenant_id:    tenant identifier
    vertical:     one of ``'fs'``, ``'healthcare'``, ``'legal'``, etc.
    file_ext:     lowercase file extension without leading dot (e.g. ``'pdf'``)

    Returns
    -------
    str
        The volume path that was written (suitable for storing in
        ``document_registry.source_path``).

    Raises
    ------
    httpx.HTTPStatusError
        If the Files API returns a non-2xx response.
    """
    volume_path = f"{_VOLUME_ROOT}/{tenant_id}/{vertical}/{document_id}.{file_ext}"
    url = f"{_base_url()}/api/2.0/fs/files{volume_path}"
    resp = httpx.put(
        url,
        headers=_headers("application/octet-stream"),
        content=file_bytes,
        timeout=120.0,
    )
    resp.raise_for_status()
    return volume_path


# ---------------------------------------------------------------------------
# Jobs API
# ---------------------------------------------------------------------------

def trigger_pipeline(document_id: str, tenant_id: str) -> str:
    """
    Trigger a "run-now" on the DocuBricks main pipeline job, passing
    *document_id* and *tenant_id* as notebook parameters.

    Returns
    -------
    str
        The Databricks ``run_id`` as a string.

    Raises
    ------
    httpx.HTTPStatusError
        If the Jobs API returns a non-2xx response.
    KeyError
        If ``PIPELINE_JOB_ID`` is not set in the environment.
    """
    job_id = int(os.environ["PIPELINE_JOB_ID"])
    url = f"{_base_url()}/api/2.1/jobs/run-now"
    resp = httpx.post(
        url,
        headers=_headers(),
        json={
            "job_id": job_id,
            "notebook_params": {
                "trigger_document_id": document_id,
                "tenant_id": tenant_id,
            },
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return str(resp.json()["run_id"])


def get_job_run_status(run_id: str) -> dict:
    """
    Fetch the current status of a job run identified by *run_id*.

    Returns
    -------
    dict
        A dict with the keys:

        ``state``
            Life-cycle state string as returned by Databricks
            (e.g. ``'RUNNING'``, ``'TERMINATED'``).
        ``result_state``
            Result state string (e.g. ``'SUCCESS'``, ``'FAILED'``), or
            ``None`` while the run is still in-progress.
        ``state_message``
            Human-readable status message, or empty string.

    Raises
    ------
    httpx.HTTPStatusError
        If the Runs API returns a non-2xx response.
    """
    url = f"{_base_url()}/api/2.1/jobs/runs/get"
    resp = httpx.get(
        url,
        headers=_headers(),
        params={"run_id": run_id},
        timeout=15.0,
    )
    resp.raise_for_status()
    body = resp.json()
    state_obj = body.get("state", {})
    return {
        "state": state_obj.get("life_cycle_state", ""),
        "result_state": state_obj.get("result_state"),
        "state_message": state_obj.get("state_message", ""),
    }
