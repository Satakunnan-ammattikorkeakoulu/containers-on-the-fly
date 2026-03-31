---
name: test
description: Run backend and frontend test suites and report results
---

Run the offline test suites (no running app required) and report a summary.

## Steps

1. Run **backend tests** and **frontend tests** in parallel:
   - Backend: `make test-backend` (pytest — unit + integration with SQLite in-memory DB)
   - Frontend: `make test-frontend` (vitest — unit + component tests)

2. Present results as a summary table:

   | Suite | Tests | Passed | Failed | Status |
   |-------|-------|--------|--------|--------|
   | Backend | N | N | N | PASS/FAIL |
   | Frontend | N | N | N | PASS/FAIL |

3. For any **failures**, show:
   - Test name and file path
   - Brief error message or assertion that failed
   - Do NOT dump the entire stack trace — keep it concise

4. For **all passing**, just report: "All tests pass."

## Notes

- These suites run offline — they do NOT require the app stack to be running
- E2E (Playwright) and API (Bruno) tests are excluded because they need a live app
- If a test failure looks related to the current changes, mention which change likely caused it
