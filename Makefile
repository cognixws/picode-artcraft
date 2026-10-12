.PHONY: web check ci-scoped close close-summary
web:
	node --check ui/apps.js
	node --check ui/domain.js
	python3 scripts/check.py
check: web
	python3 -m unittest discover -s tests -v
	node --test tests/domain.test.cjs
ci-scoped: check
close: ci-scoped
	git diff --check main
	@echo "Extension gates passed; visual and native receipts are separate in docs/validation-office-gui.md."
close-summary:
	@git status --short --branch
	@git diff --stat
	@git log -1 --oneline
