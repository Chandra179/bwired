ext:
	python extract_doc.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt

up:
	docker compose up -d

v:
	python -m markdown_chunker.cli.vectorize_cli --config vectorize.yaml --input econ_nuclear.md

s:
	python -m markdown_chunker.cli.search_cli --config search.yaml --query "employee stock purchase scheme, 267-71 global competitiveness, 251-2 history, 248-50 leadership, 267 level of government ownership, 259 liberalisation challenges, 253-9 staff benefits, 267-71 staffing, 262-3 structure, 250-2, 259-61 SINOPEC (China Petroleum &amp; Chemical Corporation), 6, 12, 69-72, 76-8, 81-4, 86, 88, 89 Shenhua Coal to Oil Company Limited"

e:
	python example_usage.py