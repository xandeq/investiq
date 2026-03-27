# Portfolio module — Phase 2 implementation
# This module was added in Phase 1 (Plan 01-04) to prove EXT-01:
# Zero changes were required in app/core/ or app/modules/auth/ to add this module.
#
# EXT-01 satisfied: models.py imports only the shared Base (a plain DeclarativeBase),
# no auth domain logic, no core security. The module boundary is structurally enforced.
#
# EXT-03 satisfied: service.py exposes async calculate(data: dict) -> dict —
# the skill adapter interface that Phase 4 DCF/valuation/earnings skills will implement.
