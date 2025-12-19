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
	python -m markdown_chunker.search --config search.yaml --query "national champions' (China), 6, 70 operation of, 140-7 political influence, 9-11 profits (China), 6"

e:
	python example_usage.py