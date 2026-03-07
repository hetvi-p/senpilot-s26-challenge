run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A app.workers.celery_app:celery_app worker -l INFO

test:
	pytest -q