e:
	python extract_docs.py example.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m internal.cli.vectorize_cli --config vectorize.yaml --input example.md

s:
	python -m internal.cli.search_cli --config search.yaml --query "give me tables for labor market trends"

r:
	uvicorn server:app --host 0.0.0.0 --port 8000

d:
	python download_models.py