.PHONY: build capture-session test report clean

# Rebuild the container image.
# Only needed when Containerfile, package.json, playwright.config.ts, or scripts/ change.
# Test files (tests/) are bind-mounted — editing them takes effect on next 'make test' without rebuild.
build:
	podman-compose --profile capture --profile test build

capture-session: build
	@echo "Starting session capture — open http://localhost:6080 in your browser"
	podman-compose --profile capture run --rm --service-ports capture

test:
	@podman volume inspect e2e_e2e-session >/dev/null 2>&1 || \
	  (echo "ERROR: No session found. Run 'make capture-session' first." && exit 1)
	podman-compose --profile test run --rm test

report:
	@echo "Opening HTML report..."
	xdg-open reports/index.html 2>/dev/null || open reports/index.html 2>/dev/null || \
	  echo "Report at: $(PWD)/reports/index.html"

clean:
	podman-compose --profile capture --profile test down -v
	find reports/ -mindepth 1 -delete 2>/dev/null || true
