ext:
	python extract_doc.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m markdown_chunker.vectorize --config vectorize.yaml --input sample_document.md

s:
	python -m markdown_chunker.search --config search.yaml --query "quarter 3 finance report summary"

e:
	python example_usage.py