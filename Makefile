req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

r:
	uvicorn internal.server:app --host 0.0.0.0 --port 8000