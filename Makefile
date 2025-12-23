e:
	python extract_docs.py consum.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m internal.cli.vectorize_cli --config vectorize.yaml --input example.md

s:
	python -m internal.cli.search_cli --config search.yaml --query "labor market trends"