.PHONY: default
default: help

.PHONY: help
help:
	@echo "make help		Show this help message"
	@echo "make clean-pyc	Clean pyc files from every directory"
	@echo "install_main_requirements	Install core app dependencies"
	@echo "install_dev_requirements	Install developer dependencies"

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: install_main_requirements
install_main_requirements:
	pip install --exists-action=w -r requirements/main.txt

.PHONY: install_dev_requirements
install_dev_requirements:
	pip install --exists-action=w -r requirements/dev.txt
