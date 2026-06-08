---
name: code-review
description: Review code changes for consistency with project patterns and conventions
---

Review all unstaged changes (`git diff`) against the project's established patterns. Check each of the following areas and report findings as a numbered list with PASS/WARN/FAIL per item.

## Backend (Python/FastAPI) Checks

1. **Naming conventions**: Functions use camelCase, classes and DB table names use PascalCase. Variables use camelCase.
2. **Response wrapper**: All endpoint response functions return via `Response(status, message, data)` from `helpers.server`. No raw dict returns.
3. **Authentication**: Every non-public endpoint has `ForceAuthentication(token)` or `ForceAuthentication(token, "admin")`. The only public endpoint is `/api/app/config`.
4. **Session management**: Database access uses `with Session() as session:` context manager. No `session.close()` inside `with` blocks. ORM objects are not accessed after the session scope ends.
5. **Pydantic models**: POST endpoints with JSON bodies have a corresponding model in `endpoints/models/`. Model fields use camelCase matching the frontend's expectations.
6. **Settings access**: Settings are accessed via `settings_handler.getSetting("category.settingName")`. New settings are defined in `settings_schema.py`.
7. **Docstrings**: New functions have docstrings with purpose, parameters, and return description.

## Frontend (Vue 2/Vuetify) Checks

8. **Vue 2 Options API**: Components use `data()`, `methods`, `computed`, `watch`, `mounted` etc. No Composition API (`setup()`, `ref()`, `reactive()`). No Vue 3 syntax.
9. **Vuetify 2 components**: UI uses Vuetify 2 components (`v-data-table`, `v-btn`, `v-card`, etc.). No raw HTML elements where Vuetify components exist. No Vuetify 3 syntax.
10. **Date handling**: All date formatting uses Day.js via `helpers/time.js` (`DisplayTime`, `TimestampToLocalTimeZone`). No raw `new Date()` or `moment`.
11. **API URLs**: All endpoint URLs come from `AppUrls.js`. No hardcoded API paths in components.
12. **State management**: Shared state goes through Vuex store (`src/store/store.js`). No component-to-component direct data passing for global state.
13. **ESLint**: Run `cd webapp/frontend && npm run lint` and report any errors.

## General Checks

14. **No hardcoded values**: Ports, IPs, and environment-specific values come from settings, not hardcoded.
15. **Existing patterns respected**: New code follows the same structure and conventions as adjacent existing code in the same file/directory.

Present results as a checklist. For any WARN or FAIL items, show the specific file and line with a brief explanation of what needs to change.
