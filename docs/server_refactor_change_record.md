# Server Refactor Change Record

## 2026-06-27 00:38:12 +08:00

- Change content:
  - Applied conservative marking for the nested duplicate `server/` copy.
  - Added a smoke test proving `server/main.py` is ignored by Git.
  - Updated the server boundary map with the conservative marking decision and
    duplicate data snapshot.
- Changed files:
  - `.gitignore`
  - `tests/test_server_contract_static.py`
  - `docs/server_boundary_refactor_map.md`
  - `docs/server_refactor_change_record.md`
- Purpose or development-flow note:
  - Reduce the risk of future edits targeting the wrong server implementation
    without moving files or changing runtime behavior.

## 2026-06-26 23:27:29 +08:00

- Change content:
  - Added dependency-free static server smoke tests.
  - Added server boundary and refactor map documentation.
  - Documented why the nested `blind-glasse-server/server/` copy is not the
    active runtime target.
- Changed files:
  - `tests/test_server_contract_static.py`
  - `docs/server_boundary_refactor_map.md`
  - `docs/server_refactor_change_record.md`
- Purpose or development-flow note:
  - Freeze the current API and repository boundary before refactoring the
    server monolith.
  - Avoid deleting or moving duplicated code before tests and explicit user
    approval.
