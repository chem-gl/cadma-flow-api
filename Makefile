PYTHON ?= python
DJANGO_SETTINGS_MODULE ?= cadmaflow.settings
MYPY_TARGET ?= cadmaflow

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make mypy             -> Run mypy on full project ($(MYPY_TARGET))"
	@echo "  make mypy-exec        -> Run mypy on execution model only"
	@echo "  make mypy FILE=path   -> Run mypy on arbitrary file (make mypy FILE=cadmaflow/models/execution.py)"

.PHONY: mypy
mypy:
ifndef FILE
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(PYTHON) -m mypy $(MYPY_TARGET)
else
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(PYTHON) -m mypy $(FILE)
endif

.PHONY: mypy-exec
mypy-exec:
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(PYTHON) -m mypy cadmaflow/models/execution.py
