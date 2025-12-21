e:
	python extract_docs.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m internal.cli.vectorize_cli --config vectorize.yaml --input econ_nuclear.md

s:
	python -m internal.cli.search_cli --config search.yaml --query "what is the current political situation between china and india"