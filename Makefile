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

run3:
	python -m markdown_chunker.cli \
	--input econ_nuclear.md \
	--collection-name econ_nuclear \
	--document-title "Economy Report"

run4:
	python -m markdown_chunker.cli \
	--search "whats the cause of the politican tension between china and india" \
	--search-limit 10 \
	--collection-name econ_nuclear

ex:
	python example_usage.py

	