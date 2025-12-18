ext:
	python extract_doc.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m markdown_chunker.vectorize --config vectorize.yaml --input econ_nuclear.md

s:
	python -m markdown_chunker.search --config search.yaml --query "what is the current political situation between india and china"

e:
	python example_usage.py