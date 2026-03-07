from __future__ import annotations

from app.services.pipeline import run_inbound_email_pipeline
from app.workers.celery_app import celery_app


@celery_app.task(
    name="process_inbound_email",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def process_inbound_email(self, payload: dict) -> dict:
    """
    Orchestrates the inbound email workflow after webhook auth + parsing.
    """
    result = run_inbound_email_pipeline(
        payload=payload,
        task_id=self.request.id,
    )
    return result