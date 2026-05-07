# Session Handoff — 2026-05-07 — Phase 4 — PR #13 Admin Panel: Users & Teams

## 1. 무엇을 했나

`feature/phase4-pr13-admin-users-teams` 브랜치 + **14 commit** + security-reviewer 1 라운드 (PASS-with-conditions, 1 High 흡수 / 4 Medium·4 Low·3 Info follow-up) + Phase 4 의 **첫 PR**. Phase 4 = 관리자 패널 (`docs/v2-execution-plan.md` §3.5) 의 4.1/4.2/4.3 (Admin 라우트 가드 + Users 관리 + Teams 관리). 4.4~4.10 (DT/Scans/Disk/Audit/Health + 컴포넌트 승인 워크플로우) 은 PR #14/#15.

### 1.1 백엔드 (4 commit + 1 fix commit)

1. `0f94570` **feat(db): password_reset_tokens table — migration 0006**
   - Forward-only Alembic. PK uuid + user_id FK CASCADE + token_hash (bcrypt) + expires_at + used_at + invalidated_at + 2 index.
2. `fba3c25` **feat(authz): require_super_admin_or_404 — admin existence-hide**
   - 신규 dependency factory: 익명 = 401, authed 비-super-admin = **404 (existence-hide, NOT 403)**. `require_role` 은 그대로 (403 시멘틱).
3. `fd0df38` **feat(admin): users management API + service + schemas**
   - 6 endpoint (`/v1/admin/users[/{id}/role,deactivate,activate,password-reset]`). 안전장치: `last_super_admin_protected` / `cannot_modify_self` / `invalid_role_assignment`. 비밀번호 리셋 토큰: `secrets.token_urlsafe(32)` → bcrypt → 평문 폐기, 1h TTL, single-pending-token policy. RFC 7807 Problem Details + audit auto-emit (token_hash 자동 마스킹).
4. `38fed41` **feat(admin): teams management API + service + schemas**
   - 7 endpoint (`/v1/admin/teams[/{id}[/members[/{user_id}]]]`). 안전장치: `team_has_active_scans` / `last_team_admin_protected` / 409 slug conflict. 팀 삭제 = 프로젝트 archive 후 CASCADE delete (audit listener 가 archive event 캡처 후 CASCADE 가 물리 삭제).
5. `7d6ca92` **fix(admin): SELECT FOR UPDATE around last-super-admin / last-team-admin checks** *(security-reviewer F1 흡수)*
   - `_lock_and_count_active_super_admins` / `_lock_and_count_team_admins` — `with_for_update()` 로 row lock. memory `feedback_optimistic_concurrency_pattern.md` 패턴 (vulnerability_service:309 와 동일). 회귀 테스트 6건 (lock-behavior 2 + asyncio.gather concurrency 4) — 두 세션을 `asyncio.gather` 로 동시 demote/deactivate, "최소 한 건은 실패 + count 가 1 이상 유지" 인변량 검증.

### 1.2 프론트엔드 (4 commit)

6. `d52974c` **feat(i18n): admin namespace EN/KO** — `locales/{en,ko}/admin.json` (153 줄). nav / users / teams / errors / not_found / actions. `lib/i18n.ts` 에 namespace 등록.
7. `f79b875` **feat(admin-ui): users management page + drawer + hooks** — `features/admin/users/{AdminUsersPage,AdminUserDrawer}.tsx` + TanStack Query 훅 6개 (list / detail / role / deactivate / activate / password-reset). 인라인 toolbar (search 300ms debounce + role filter + active filter), 40px compact 행, Sheet drawer, 인라인 confirm strip.
8. `faa0676` **feat(admin-ui): teams management page + drawer + hooks** — `features/admin/teams/*` + 훅 7개. 새 팀 생성 인라인 폼, 멤버 추가/제거.
9. `339a846` **feat(admin-ui): admin layout + routing + 404 existence-hide** — `AdminLayout` (224px sidebar + 48px header), `AdminNotFound` (i18n), router nested `/admin/*` (`index → users` redirect + catch-all 404). `Home.tsx` 에 super-admin 만 보이는 admin 진입 링크.

### 1.3 E2E + 하네스 (4 commit)

10. `abf6785` **chore(seed): super-admin + extra-members flags for admin e2e** — `seed_e2e_user.py` 에 `--super-admin` / `--extra-members N` / `--extra-team-admin` 플래그. JSON output 에 `is_super_admin` + `extra_members[]` 추가. `tests/_harness/seed.ts` `SeedSummary` / `SeedOptions` 미러 갱신.
11. `b926ee6` **feat(admin-ui): locale-agnostic toast keys + Problem extension passthrough** — `parseProblemBody` 가 RFC 7807 §3.2 extension 보존 (이전엔 silent drop). `ProblemDetails` 에 `[extension: string]: unknown` index signature. `AdminToast` 가 `data-toast-key`, error alert 가 `data-extension`. row 들에 `data-email` / `data-role` / `data-team-name`.
12. `20a9f5c` **test(harness): AdminUsersHarness + AdminTeamsHarness + PortalPage entries** — 도메인 verb (changeRoleTo / deactivate / addMember / removeMember / createTeam / deleteTeam 등). `PortalPage.gotoAdminUsers()` / `gotoAdminTeams()` 편의 진입.
13. `a642ddd` **test(e2e): admin users/teams 4-scenario coverage** — §6.3 의 4 시나리오 모두 green:
    - super_admin role-change + reload (4.8s) — extra team_admin → developer 로 demote.
    - 비-super-admin 의 `/admin/users` + `/admin/teams` 접근 시 404 existence-hide (3.4s) — `admin-not-found` rendered, URL unchanged.
    - super_admin team create → addMember → removeMember (4.8s).
    - last super_admin protection — `cannot_modify_self` 변종 채택 (단일-DB 결정성). `last_super_admin_protected` 본 case 는 backend integration 으로 cover.

### 1.4 추가 작업

- `4e0ee04` **chore(docs): archive mislabeled phase 4 notification prompt** — `_next-session-prompt-phase4-pr14.md` (알림으로 잘못 라벨, 실제는 Phase 6 PR #18) 를 `archive/next-session-prompts/_next-session-prompt-phase4-pr14-MISLABELED-as-notification.md` 로 이동.
- `tests/integration/test_alembic_upgrade.py` head bump (0005 → 0006) + `finally`-block restamp (chore PR #7 의 alembic 0005 stamp pollution 방지).

### 1.5 security-reviewer Producer-Reviewer 결과

평결: **PASS-with-conditions** (0 Critical / 1 High / 4 Medium / 4 Low / 3 Info).

| ID | Severity | 요약 | 처리 |
|----|----------|------|------|
| **F1** | High | 마지막 super_admin / team_admin 의 SELECT-then-mutate TOCTOU race (CWE-367) | **`7d6ca92` 흡수** ✅ |
| F2 | Medium | `_validation_exception_handler` 의 `errors[].input` 평문 reflection (CWE-209) | chore PR #8 |
| F3 | Medium | `/v1/admin/users?role=` query 가 enum 미검증 (silently 무시) | chore PR #8 |
| F4 | Medium | audit_logs.diff 가 email / full_name 평문 — `_SENSITIVE_COLUMNS` 미포함 (CWE-359) | chore PR #8 |
| F5 | Medium | admin password-reset 가 user-not-found 에 404 반환 → enumeration (단, super-admin gated 이라 trust boundary 안. Phase 6 public flow 와 분리 명시 필요) | chore PR #8 (doc 변경) |
| F6 | Low | 비활성 super-admin 이 expired 직전 JWT 로 `/admin/*` 접근 시 401 (404 아님) — 외부 probing 에는 영향 X | as-is (의도적 설계 — 문서화 only) |
| F7 | Low | `delete_team` 의 active-scan 체크와 CASCADE 사이 race | chore PR #8 (with_for_update) |
| F8 | Low | `seed_e2e_user.py --super-admin` 의 prod env guard 부재 (CWE-489) | chore PR #8 (env guard) + Phase 7 .dockerignore |
| F9 | Low | `update_user_role` 가 존재하지 않는 team_id → IntegrityError → 500 (422 아님) | chore PR #8 |
| F10 | Info | `parseProblemBody` extension passthrough — 미래 회귀 방지용 schema 강화 권고 | chore PR #8 (frontend) |
| F11 | Info | audit_context user_id 가 deactivate target 과 actor 의 구분 — 동작은 정상, doc note | as-is |
| F12 | Info | `_problem_for_admin_user_error.detail = str(exc)` — 미래 PII echo 방지 코멘트 | chore PR #8 (코멘트) |

**Threat-model 통과 (positive findings)**:
- existence-hide 가 모든 admin sub-route 에 router-level 적용 (`api/v1/admin/__init__.py:27`)
- 4-role 매트릭스 (anonymous/developer/team_admin/super_admin) 가 각 endpoint 마다 integration test 로 cover
- 비밀번호 리셋 평문이 log / response / audit 어디에도 안 닿음
- single-pending-token policy 동작 (`test_initiate_password_reset_invalidates_prior_pending`)
- deactivate 시 RefreshToken 전부 revoke (`test_deactivate_user_revokes_refresh_tokens`)
- cross-team role escalation 없음 (CWE-863) — `update_user_role` 가 명시 team_id 만 mutate
- adversarial input parametrize 충실 (RTL override / null bytes / CRLF / javascript: / oversized / SQL keywords / role coercion 모두)
- audit cascade — team delete 시 projects archive event 가 동일 transaction 에 captured
- `token_hash` `_SENSITIVE_COLUMNS` 포함
- CSRF moot — admin 모두 JWT-bearer, cookie 없음
- frontend `AdminLayout` 의 existence-hide 가 backend 와 defense-in-depth

## 2. 결정 사항 / 변경된 가정

- **`require_role` 은 그대로 (403)**, admin 만 신규 `require_super_admin_or_404` 사용 — 기존 호출자 호환 + existence-hide 시멘틱 분리. CLAUDE.md / v2-execution-plan 갱신 불필요.
- **팀 삭제 정책**: `archived_at` UPDATE → `session.delete(team)` → CASCADE 가 projects 물리 삭제. `archived_at` 의 audit row 가 보존되어 archive 의도 추적 가능. spec §4.3 의 "projects 는 archive" 를 이렇게 해석. 단일 transaction.
- **last super_admin 프로텍션**: `with_for_update()` 채택 (memory `feedback_optimistic_concurrency_pattern` 와 일치). lock order = users-then-memberships (deadlock-free convention).
- **Problem Details extension passthrough**: `parseProblemBody` 가 RFC 7807 §3.2 extension 을 보존하도록 변경 (이전엔 silent drop). 영향 평가: 모든 backend Problem-emit 사이트 검토 후 sensitive value 미노출 확인. 미래 PR 에서 sensitive extension 추가 시 frontend schema 강화 (F10 follow-up).
- **e2e 시나리오 4 (last super_admin)** = `cannot_modify_self` 채택. 공유 dev DB 에서 `last_super_admin_protected` 의 결정성을 확보하기 어려워서. backend integration 이 `last_super_admin_protected` 본 case 를 cover.
- **세션 핸드오프 prompt 라벨링 정정**: 알림 = Phase 6 PR #18 (§3.7), Phase 4 = 관리자 패널 (§3.5). v2-execution-plan §3.5 / §3.7 가 단일 진실. 잘못 라벨링된 prompt 1건 archive.
- **MEMORY 갱신 권고**: `feedback_admin_existence_hide_pattern.md` 신규 — admin endpoint 는 `require_super_admin_or_404` (404 existence-hide) 사용; `require_role("super_admin")` 은 403 시멘틱이라 admin 에 부적합.

## 3. 현재 상태

- **브랜치**: `feature/phase4-pr13-admin-users-teams` (push 후 PR open).
- **Commit**: 14건 (백엔드 5 / 프론트엔드 4 / e2e+harness 4 / docs archive 1).
- **테스트**:
  - **backend 단위/통합**: 124 admin tests (118 기존 + 6 신규 concurrency) 전부 pass. ruff clean / mypy clean (146 source + admin 모듈).
  - **frontend Vitest**: 287 / 287 pass (241 기존 + 46 admin). admin folder line coverage **91.68%**.
  - **Playwright e2e**: admin 시나리오 4건 green; 기존 11 pass / 19 skip (skip 은 pre-existing dev-DB pollution, 본 PR 무관).
- **알려진 이슈**:
  - F1 외 11 보안 발견사항은 chore PR #8 follow-up 으로 등재.
  - test-pollution 11건 (`test_component_detail_returns_drawer_payload_with_vulns` + cross-team structlog capture) 은 main 에서도 재현되는 pre-existing fixture leakage. 본 PR 영향 X.
  - dev backend container 의 hot-reload watcher 가 background task drain 시 stuck 가능 (본 세션 중 1회 발생) — `docker-compose stop --timeout 1 + up -d` 로 복구.
- **DoD 충족** (Phase 4 §3.5 의 4.1+4.2+4.3 부분):
  - lint/typecheck/test green ✅
  - 신규 코드 line coverage ≥ 80% (백엔드 95% / 프론트엔드 91.68%) ✅
  - Playwright e2e 4 시나리오 green ✅
  - Playwright 하네스 verb 추가 ✅
  - EN/KO 동시 ✅
  - audit 이벤트 기록 검증 ✅
  - security-reviewer PASS (High 흡수, M/L/I follow-up 등재) ✅
  - admin 7 화면 중 2개 (Users/Teams) 동작 ✅

## 4. 다음 세션이 할 일

옵션 A — **Phase 4 PR #14 (DT Connector + Scan Queue + Disk + Audit + Health 5 화면)**. v2-execution-plan §3.5 의 4.4~4.8.

옵션 B — **chore PR #8 (admin security follow-ups)**. F2~F12 일괄. ~200 LoC. 간단하므로 PR #14 와 병렬 가능 (다른 브랜치).

옵션 C — **Phase 4 PR #15 (컴포넌트 승인 워크플로우)**. v2-execution-plan §3.5 의 4.9~4.10. PR #14 머지 후 권고.

권고 순서: **옵션 A (Phase 4 PR #14) → 옵션 B (chore PR #8 병렬) → 옵션 C (Phase 4 PR #15)**.

핵심 라우팅 (PR #14):
- **frontend-dev**: 5 신규 admin 화면 + 사이드바 navigation 항목 추가.
- **backend-developer**: DT health/circuit-breaker 상태 endpoint, Scan Queue 모니터 endpoint, Disk usage endpoint, Audit log search endpoint, System Health summary endpoint.
- **scan-pipeline-specialist** (선택): DT health monitor 주기 + 고아 정리 (CLAUDE.md "DT 연동 전략").
- **test-writer**: e2e admin 5 화면 시나리오 + harness 확장.
- **security-reviewer**: Producer-Reviewer 1 라운드.

## 5. 주의·블로커

- **memory 신규 추가 권고**:
  - `feedback_admin_existence_hide_pattern.md` — admin endpoint 의 404 existence-hide 패턴 (`require_super_admin_or_404`). 401/403 분리 시멘틱.
  - `project_phase4_admin_followup_pr.md` — chore PR #8 의 12 follow-up 발견사항 인덱스.
- **F1 의 회귀 테스트 패턴**: `tests/unit/services/test_admin_concurrency.py` — 두 `AsyncSession` 을 `asyncio.gather` 로 동시 demote 후 "최소 한 건 실패 + count ≥ floor" 인변량 검증. 향후 last-X-admin 류 보호 추가 시 동일 패턴 재사용.
- **adversarial input parametrize** (memory `feedback_adversarial_input_parametrize`): admin 모듈은 충실히 cover 됐음 (RTL / null / CRLF / javascript: / oversized / SQL kw). PR #14 의 새 untrusted input (DT URL / scan filter / audit search query) 도 동일 표준 적용.
- **dev backend hot-reload stuck** — file watcher 가 test 파일 변경 감지 시 `--reload` 가 background task drain 대기 중 멈출 수 있음. 회귀 발생 시 `docker-compose stop --timeout 1 + up -d` 로 복구. PR #14 진입 시 상태 확인 권고.
- **PR description body** 에 follow-up 12건을 명시해서 reviewer 가 chore PR #8 backlog 를 인지하도록.

## 6. 다음 세션 시작 지시문 (복붙용)

### 옵션 A — Phase 4 PR #14 (DT/Scan/Disk/Audit/Health 5 화면)

```
TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <Phase 4 PR #13 squash merge SHA>. 누적 머지: PR #1~#13 + chore CI fix 4건 + chore PR #1~#7. Phase 4 PR #13 (관리자 Users/Teams) 완료. Phase 4 의 두 번째 PR 시작.

이번 세션 = Phase 4 PR #14 — Admin DT Connector + Scan Queue + Disk + Audit + System Health 5 화면.

직전 핸드오프(반드시 시작 시 읽기):
  - docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md — 본 세션 (PR #13). admin 인프라 (라우터 가드, AdminLayout, i18n namespace, 하네스) 가 이미 갖춰져 있음. PR #14 는 그 위에 5 화면 추가.
  - docs/v2-execution-plan.md §3.5 의 4.4~4.8 — 단일 진실.
  - CLAUDE.md "주요 기능 / 관리자" 절 + "DT 연동 전략".

시작 시 검증 (반드시):
  ```
  docker-compose -f docker-compose.dev.yml ps               # 6/6 healthy
  docker-compose -f docker-compose.dev.yml -f docker-compose.dt.yml ps  # +dtrack-api healthy
  gh run list --limit 3                                      # main 최신 success
  git status                                                 # working tree
  ```

작업 내용:
  - 4.4 DT Connector 화면 (health 상태 / circuit-breaker / 고아 정리 트리거)
  - 4.5 Scan Queue 화면 (실행중/대기/실패/강제종료 + WebSocket live)
  - 4.6 Disk 사용량 대시보드 (workspace + DT volume + DB)
  - 4.7 Audit Log 화면 (검색/필터/CSV export)
  - 4.8 System Health 대시보드

핵심 라우팅:
  - **backend-developer** (필수): 5 endpoint + audit search + Disk telemetry.
  - **scan-pipeline-specialist** (필수): DT health + 고아 정리 (Celery Beat 6h).
  - **frontend-dev** (필수): 5 admin 화면 + 사이드바 navigation 확장.
  - **i18n-specialist** (선택 — frontend-dev 가 EN/KO 동시 처리 가능).
  - **test-writer** (필수): e2e 5 화면 + harness.
  - **security-reviewer** (필수): Producer-Reviewer 1 라운드.

설계 제약 (PR #13 와 동일):
  - 모든 admin endpoint = `require_super_admin_or_404` (404 existence-hide).
  - RFC 7807 Problem Details + audit auto-emit.
  - PostgreSQL only / Alembic forward-only / docker-compose V1.
  - adversarial input parametrize 필수.
  - last-X-admin 류 보호 시 `with_for_update()` row lock (PR #13 의 `_lock_and_count_*` 패턴 참조).
  - 신규 코드 line coverage ≥ 80%.

DoD: lint/typecheck/test green, e2e 5 시나리오 green, EN/KO 동시, security-reviewer PASS, PR open + CI 9/9 + squash merge, 핸드오프 작성. PR #14 머지 후 admin 7 화면 중 7개 모두 (Users/Teams + DT/Scans/Disk/Audit/Health) 가 동작.
```

### 옵션 B — chore PR #8 (admin security follow-ups, ~200 LoC)

```
TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <Phase 4 PR #13 squash merge SHA>. 본 세션 = chore PR #8 — security-reviewer F2~F12 일괄 흡수. 새 endpoint 0건 / schema 0건.

직전 핸드오프:
  - docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md §1.5 의 12 발견사항 표 + §5 의 후속 등재 — 본 PR scope 단일 진실.

작업 (chore PR #5 / #7 패턴 따라 단일 PR 로 묶기):
  1. F2 — `core/errors.py:_validation_exception_handler` 의 `errors[].input` redact (CWE-209).
  2. F3 — `/v1/admin/users` 의 `role` query 를 `Literal[...]` 로 strict 화 (422 fail closed).
  3. F4 — `core/audit.py:_SENSITIVE_COLUMNS` 에 `email` / `full_name` 추가 (또는 `_PII_COLUMNS` 신설 + sha256 hash). audit retention purger task 영향 검토.
  4. F5 — `api/v1/admin/users.py` password_reset_endpoint 에 doc 코멘트 (admin 의 404-on-miss vs 미래 public flow 의 uniform 204 분리). docs/v2-execution-plan §3.6 보강.
  5. F7 — `services/admin_team_service.py:delete_team` 에 `with_for_update()` (team 행 + scans 체크).
  6. F8 — `scripts/seed_e2e_user.py` 에 `APP_ENV not in {dev,test,ci}` 가드.
  7. F9 — `services/admin_user_service.py:update_user_role` 에 team_id 존재 검증 (FK violation → 422 변환).
  8. F10 — frontend `lib/problem.ts` 의 extension passthrough 에 unit test (sensitive-shape key 차단 회귀 핀).
  9. F12 — admin router 에 doc 코멘트 (PII echo 금지).

핵심 라우팅:
  - **backend-developer** (필수): F2/F3/F4/F5/F7/F8/F9/F12.
  - **frontend-dev** (선택): F10.
  - **security-reviewer** (필수): Producer-Reviewer 1 라운드 (F4 의 hashing 정책 + F2 의 redact 완전성).

설계 제약: 새 endpoint 0건. 단위 + 통합 회귀 핀. ruff/mypy clean. PR #14 와 병렬 가능 (다른 브랜치 / 충돌 없음).

DoD: 모든 F2~F12 흡수 또는 명시적 deferral, security-reviewer PASS, PR open + 9/9 + squash merge, 핸드오프.
```

본 작업 예상 시간: PR #14 = 10~14 시간 / chore PR #8 = 3~5 시간.
