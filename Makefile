ext:
	python extract_doc.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

r:
	python -m markdown_chunker.vectorize --config vectorize.yaml --input document.md

s:
	python -m markdown_chunker.search --config search.yaml --query "what is the political situation"