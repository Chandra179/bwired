run:
	python main.py econ.pdf

req:
	pipreqs . --force

i:
	pip install -r requirements.txt