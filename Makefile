# Allow linting on specific filepaths if needed
FILEPATH := 

# Issues to ignore while linting 
LINT_IGNORE :=

.PHONY: lint
lint:
	@echo "Linting using flake8"
	@flake8 --ignore=$(LINT_IGNORE) $(FILEPATH)

.PHONY: format
format: 
	@echo "Formatting all files using autopep8"
	@autopep8 --in-place --recursive --aggressive --aggressive .

.PHONY: test
test:
	@echo "Running pytest on all files"
	@pytest
	