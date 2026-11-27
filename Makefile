# On Windows use mingw32-make (or call python manage.py <command> directly).
ifeq ($(OS),Windows_NT)
  PY ?= .venv/Scripts/python.exe
else
  PY ?= .venv/bin/python
endif

.PHONY: run test load-demo reload-demo make-demo verify

run:
	$(PY) manage.py run

test:
	$(PY) manage.py test

load-demo:
	$(PY) manage.py load-demo

reload-demo:
	$(PY) manage.py load-demo --fresh

make-demo:
	$(PY) manage.py make-demo

verify:
	$(PY) manage.py verify
