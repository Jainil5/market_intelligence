.PHONY: bootstrap verify test run smoke cron-help

bootstrap:
	@chmod +x scripts/*.sh 2>/dev/null || true
	@./scripts/bootstrap.sh

verify:
	@python scripts/verify_setup.py

test:
	@pytest -q

run:
	@uvicorn main:app --host 0.0.0.0 --port 8000 --reload

smoke:
	@./scripts/smoke_test.sh

cron-help:
	@echo "Railway Cron: schedule scripts/cron_update.sh with env BASE_URL + API_KEY"
	@echo "Suggested: 0 12 * * 1-5 UTC (~5:30 PM IST Mon-Fri, adjust for DST)"
