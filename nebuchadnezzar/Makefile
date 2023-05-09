STATEDIR = $(PWD)/.neb-state
BINDIR = $(STATEDIR)/env/bin

# Short descriptions for commands (var format _SHORT_DESC_<cmd>)
_SHORT_DESC_LINT := "Run linting tools on the codebase"
_SHORT_DESC_PYENV := "Set up the python environment"
_SHORT_DESC_TEST := "Run the tests"
_SHORT_DESC_CHECK_DIST := "Check the distribution files before uploading to pypi"

default : help
	@echo "You must specify a command"
	@exit 1

# ###
#  Helpers
# ###

_REQUIREMENTS_FILES = requirements/main.txt requirements/test.txt requirements/lint.txt
VENV_EXTRA_ARGS =

$(STATEDIR)/env/pyvenv.cfg : $(_REQUIREMENTS_FILES)
	# Create our Python 3 virtual environment
	rm -rf $(STATEDIR)/env
	python3 -m venv $(VENV_EXTRA_ARGS) $(STATEDIR)/env

	# Upgrade tooling requirements
	$(BINDIR)/python -m pip install --upgrade pip setuptools wheel

	# Install requirements
	$(BINDIR)/python -m pip install $(foreach req,$(_REQUIREMENTS_FILES),-r $(req))

# /Helpers

# ###
#  Help
# ###

help :
	@echo ""
	@echo "Usage: make <cmd> [<VAR>=<val>, ...]"
	@echo ""
	@echo "Where <cmd> can be:"  # alphbetical please
	@echo "  * help -- this info"
	@echo "  * help-<cmd> -- for more info"
	@echo "  * lint -- ${_SHORT_DESC_LINT}"
	@echo "  * pyenv -- ${_SHORT_DESC_PYENV}"
	@echo "  * test -- ${_SHORT_DESC_TEST}"
	@echo "  * check-dist -- ${_SHORT_DESC_CHECK_DIST}"
	@echo "  * version -- Print the version"
	@echo ""
	@echo "Where <VAR> can be:"  # alphbetical please
	@echo ""

# /Help

# ###
#  Pyenv
# ###

help-pyenv :
	@echo "${_SHORT_DESC_PYENV}"
	@echo "Usage: make pyenv"
	@echo ""
	@echo "Where <VAR> could be:"  # alphbetical please
	@echo "  * VENV_EXTRA_ARGS -- extra arguments to give venv (default: '$(VENV_EXTRA_ARGS)')"

pyenv : $(STATEDIR)/env/pyvenv.cfg

# /Pyenv

# ###
#  Test
# ###

TEST =
TEST_EXTRA_ARGS =

help-test :
	@echo "${_SHORT_DESC_TEST}"
	@echo "Usage: make test [<VAR>=<val>, ...]"
	@echo ""
	@echo "Where <VAR> could be:"  # alphbetical please
	@echo "  * TEST -- specify the test to run (default: '$(TEST)')"
	@echo "  * TEST_EXTRA_ARGS -- extra arguments to give pytest (default: '$(TEST_EXTRA_ARGS)')"
	@echo "    (see also setup.cfg's pytest configuration)"

test : $(STATEDIR)/env/pyvenv.cfg
	$(BINDIR)/python -m pytest --cov=nebu --cov-report=html --cov-report=term  $(filter-out $@, $(MAKECMDGOALS)) $(TEST_EXTRA_ARGS) $(TEST) --snapshot-update

# /Test

# ###
#  Version
# ###


curr_tag := $(shell git describe --tags $$(git rev-list --tags --max-count=1))
curr_tag_rev := $(shell git rev-parse "$(curr_tag)^0")
head_rev := $(shell git rev-parse HEAD)
head_short_rev := $(shell git rev-parse --short HEAD)
ifeq ($(curr_tag_rev),$(head_rev))
	version := $(curr_tag)
else
	version := $(curr_tag)-dev$(head_short_rev)
endif

version help-version : .git
	@echo $(version)

# /Version


# ###
#  Lint
# ###

help-lint :
	@echo "${_SHORT_DESC_LINT}"
	@echo "Usage: make lint"

lint : $(STATEDIR)/env/pyvenv.cfg setup.cfg
	$(BINDIR)/python -m flake8 --exclude=tests,templates nebu
	$(BINDIR)/python -m flake8 --max-line-length=200 --ignore=E121,F821,E123 nebu/tests nebu/templates

# /Lint

# ###
# Check dist
# ###

help-check-dist :
	@echo "${_SHORT_DESC_CHECK_DIST}"
	@echo "Usage: make check-dist"

check-dist :
	$(BINDIR)/python -m pip install twine
	$(BINDIR)/python setup.py bdist_wheel -d check-dist
	$(BINDIR)/python -m twine check check-dist/*
	rm -rf check-dist/

# ###
#  Catch-all to avoid errors when passing args to make test
# ###

%:
	@:
# /Catch-all
