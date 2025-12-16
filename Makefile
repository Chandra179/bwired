ext:
	python extract_doc.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

run:
	python -m markdown_chunker.cli --input econ_nuclear.md --qdrant-url http://localhost:6333

run2:
	python -m econ_nuclear.cli \
	--input document.md \
	--dry-run

ex:
	python example_usage.py