# Session Handoff — 2026-05-08 — chore PR #8 — Admin Security Follow-ups (F2~F12)

> 본 핸드오프는 본 세션에서 동시에 진행한 PR #14 (`docs/sessions/2026-05-08-phase4-pr14-admin-dt-scans-disk-audit-health.md`) 와 짝.

## 1. 무엇을 했나

`feature/chore-pr8-admin-security-followups` 브랜치 + **11 commit** + security-reviewer 1라운드 (PASS-with-conditions, 0 Critical / 0 High / 3 Medium / 4 Low / 2 Info) + GitHub PR #14 squash merge (main HEAD = `9d7bf66`). 본 PR 은 PR #13 (admin Users/Teams) 의 security-reviewer follow-up 12건 중 9건을 일괄 흡수 (F1 은 PR #13 본 PR 에서 흡수, F6 / F11 은 의도적 as-is).

### 1.1 흡수된 9 fix

1. `bfd41a8` **F2 — `_validation_exception_handler` 의 `errors[].input` redact (CWE-209)**
   - Pydantic ValidationError errors 의 `input` 필드를 `<redacted>` 로 치환. PII echo 차단.
   - 회귀 테스트 14 case (oversized, CRLF, null byte, RTL override, SQL keyword, javascript:, plaintext credential 등 adversarial parametrize).
2. `fdd8926` **F3 — `/v1/admin/users` 의 `role` query strict (`Literal[...]`)**
   - 미정의 enum 값 silently 무시 → 422 fail closed. adversarial parametrize 18 case.
3. `bf8c21c` **F4 — audit `_PII_COLUMNS` sha256 hashing (CWE-359)**
   - `email` / `full_name` 변경 시 audit_logs.diff 가 평문 대신 `{"sha256": "<hex>"}` dict 저장.
   - retention purger 영향 없음. 기존 `_SENSITIVE_COLUMNS` (`password_hash` / `token_hash`) 는 `<redacted>` 유지.
4. `a3cc75b` **F5 — admin password-reset 404-on-miss vs Phase 6 public flow 분리 명시**
   - `initiate_password_reset` docstring + `docs/v2-execution-plan.md` §3.7 보강 노트 (Phase 6 public flow 는 uniform 204 의무).
5. `3ef91ae` **F7 — `delete_team` 의 `with_for_update()` (CWE-367)**
   - team 행 lock + active scan 체크 + cascade delete. PR #13 의 last-X-admin lock 패턴 일관.
   - 회귀 테스트: `lock_timeout` SQLSTATE 55P03 가 deterministic 하게 발화되는 lock-load-bearing 테스트.
6. `222c552` **F8 — `seed_e2e_user.py --super-admin` 의 APP_ENV guard (CWE-489)**
   - `APP_ENV in {dev, test, ci}` 만 super-admin 생성 허용. 외 환경 → `sys.exit(1)` + stderr.
7. `e63eb21` **F9 — `update_user_role` 의 IntegrityError → 422 + `team-not-found`**
   - preflight check + IntegrityError 2-layer guard. user-facing detail 에 "violates" / "fk_" / "constraint" 누설 안 함.
8. `ae9640e` **F10 — `lib/problem.ts` zod schema 강화**
   - 알려진 도메인 코드 whitelist + nested-shape 자동 차단 (sensitive 확장 키 미래 누설 방지). 20 회귀 테스트.
9. `3a4b6dd` **F12 — `_problem_for_admin_user_error` PII echo 경고 코멘트**
   - 미래 contributor 에게 `detail = str(exc)` 의 PII 위험 명시 + Phase 6 public flow 의 sanitize 필요 분리.

추가 commit 2건 (CI fix):
- `7e59390` `chore(scripts): make scripts/ an importable package` — F8 의 test import 가능하도록 `__init__.py` 추가.
- `a6c9ec3` `fix(tests): tighten F3 substring assertion + F4 dict type-arg`.

### 1.2 security-reviewer 1라운드 결과

평결: **PASS-with-conditions** (0 Critical / 0 High / 3 Medium / 4 Low / 2 Info).

| ID | Severity | 요약 | 처리 |
|----|----------|------|------|
| **M1** | Medium | F2 의 `_redact_validation_errors` 가 `msg` / `ctx` 미 sanitize | chore PR #9 |
| **M2** | Medium | F8 의 `_seed(super_admin=True)` 가 APP_ENV guard 우회 가능 (`main()` 외부 import) | chore PR #9 |
| **M3** | Medium | F12 가 `_problem_for_admin_team_error` 에는 미적용 (asymmetric) | chore PR #9 |
| L1 | Low | `validation_error` / `invalid_role_assignment` whitelist 가 backend 미발행 | chore PR #9 |
| L2 | Low | `_is_team_fk_violation` text-match heuristic → `IntegrityError.orig.diag.constraint_name` | chore PR #9 |
| L3 | Low | Phase 6 OAuth 컬럼 추가 시 `_PII_COLUMNS` 갱신 backlog | Phase 6 |
| L4 | Low | F4 sha256 unsalted dictionary attack | Phase 8 SaaS hardening |
| I1 | Info | F3 case-sensitive Literal — backend snake_case 컨벤션이라 OK | as-is |
| I2 | Info | F7 lock-order convention 일관성 검증됨 | as-is (positive) |

**Positive findings (P1~P4)**:
- F7 concurrency 테스트가 `lock_timeout` SQLSTATE 55P03 deterministic 발화 — load-bearing 회귀.
- F2 단위 테스트 parametrize 가 adversarial-input 체크리스트 완전 cover.
- F10 zod schema 가 nested object extension key 자동 차단 (sensitive shape leakage 차단).
- F9 preflight + IntegrityError 2-layer guard 가 detail leak 핀.

## 2. 결정 사항 / 변경된 가정

- **F4 PII sha256**: deterministic hash (unsalted). super-admin gated 라 dictionary attack threat-model 안. Phase 8 SaaS hardening 시 pepper 추가 검토 (L4).
- **F8 sys.exit guard 위치**: `main()` 내부에서만 — `_seed` 직접 import 시 우회 가능 (M2). chore PR #9 에서 `_seed` 내부로 이동.
- **F9 IntegrityError 식별**: text-match heuristic — 현재 schema 의 단일 FK 만 매칭하므로 false-positive 위험 0. 미래 schema 확장 시 `constraint_name` 사용 (L2).
- **CI fix**: `apps/backend/scripts/__init__.py` 신설은 mypy/ruff/import 영향 없음 — `scripts.seed_e2e_user` 모듈 import 가능해진 부수 효과만.

## 3. 현재 상태

- **GitHub PR**: https://github.com/trustedoss/trustedoss-portal/pull/14 → squash merged into main (`9d7bf66`).
- **Commit**: 11건 (9 fix + 2 CI/test fix).
- **테스트**:
  - 신규 unit: 64 pass (errors handler 14 + audit PII 10 + seed env guard 24 + admin_user team-not-found 9 + audit existing 5 + concurrency 2).
  - 신규 integration: F3 adversarial 18 case + 기존 admin_users/teams 통합 회귀 모두 pass.
  - 신규 frontend Vitest: 20 (problem.ts schema).
  - Pre-existing 287 frontend + 1158 backend tests 모두 pass.
- **DoD 충족**:
  - lint/typecheck/test green ✅
  - 신규 코드 line coverage ≥ 80% ✅
  - security-reviewer PASS (High 흡수 0, M/L/I follow-up 등재) ✅
  - PR #8 머지 후 PR #14 가 보강된 헬퍼 (errors.py redact + audit.py PII sha256 + frontend problem.ts zod) 자동 활용 ✅

## 4. 다음 세션이 할 일

본 PR (chore PR #8) 은 종결. 다음:

- **PR #14 머지** — 본 세션에서 동시 진행. `docs/sessions/2026-05-08-phase4-pr14-admin-dt-scans-disk-audit-health.md` 참조.
- **chore PR #9 (admin chore follow-ups)** — 본 PR 의 M1/M2/M3 + L1/L2 + PR #14 의 G2~G10 일괄. backlog memory `project_phase4_admin_followup_pr.md`.
- **Phase 4 PR #15 (컴포넌트 승인 워크플로우)** — `docs/v2-execution-plan.md` §3.5 의 4.9~4.10. `_next-session-prompt-phase4-pr15-component-approval-workflow.md`.

## 5. 주의 / 후속

- **F4 sha256 cross-PR 영향**: PR #14 의 audit search `q` 필터가 평문 매칭 — PII 컬럼 (email/full_name) 은 sha256 dict 라 매칭 안 됨. UI 안내 필요 (PR #14 가 미흡수).
- **F3 frontend 컨벤션**: backend 가 case-sensitive Literal 이라 frontend 가 항상 snake_case role 보내야. 회귀 시 422.
- **memory 신규**:
  - `feedback_admin_existence_hide_pattern.md` — `require_super_admin_or_404` 패턴 (PR #13 권고됐지만 본 세션에 신설).
  - `project_phase4_admin_followup_pr.md` — chore PR #9 backlog.
