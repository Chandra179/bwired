req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

b:
	docker compose up --build -d

r:
	uvicorn internal.server:app --host 0.0.0.0 --port 8000

sec:
	openssl rand -hex 32