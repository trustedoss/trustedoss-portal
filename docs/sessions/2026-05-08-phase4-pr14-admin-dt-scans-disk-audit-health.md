# Session Handoff — 2026-05-08 — Phase 4 — PR #14 Admin Panel: DT/Scans/Disk/Audit/Health

> 본 핸드오프는 본 세션에서 동시에 진행한 chore PR #8 (`docs/sessions/2026-05-08-chore-pr8-admin-security-followups.md`) 와 짝.

## 1. 무엇을 했나

`feature/phase4-pr14-admin-dt-scans-disk-audit-health` 브랜치 + **22 commit** (backend 9 + frontend 10 + main rebase merge 1 + cors fix 1 + G1 fix 1) + security-reviewer 1라운드 (PASS-with-conditions, 0 Critical / 1 High 흡수 / 4 Medium / 5 Low / 3 Info) + Phase 4 의 **두 번째 PR**. `docs/v2-execution-plan.md` §3.5 의 4.4~4.8 (Admin DT Connector + Scan Queue + Disk + Audit Log + System Health).

PR #13 (Users/Teams) 의 admin 인프라 (`require_super_admin_or_404` / AdminLayout / RFC 7807 / audit auto-emit / 하네스 패턴) 위에 **5 화면** 추가.

### 1.1 backend (9 commit + G1 fix 1)

1. `c50279c` **feat(db): audit_logs target_table/action indexes — migration 0007** — forward-only.
2. `664033b` **feat(schemas): admin_ops Pydantic v2** — `DTStatusOut`, `DTOrphanItem`, `DTOrphanListPage`, `OrphanCleanupRequest`, `OrphanCleanupEnqueued`, `HealthProbeOut`, `AdminScanListItem`, `AdminScanListPage`, `AdminDiskItem`, `AdminDiskOut`, `AuditLogItem`, `AuditLogListPage`, `AuditSearchQuery`, `HealthComponent`, `SystemHealthOut` + closed Literals (`ScanStatus`, `AuditTargetTable`, `BreakerState`, `HealthStatus`).
3. `01f9177` **feat(tasks): dt_orphan_cleanup celery task** — admin 트리거 시에만 실행되는 삭제 task. Redis SETNX lock (`dt:admin:orphan_cleanup_lock`, TTL 600s) + `DTClient.delete_project(uuid)` + 멱등성 (404 → `already_gone`).
4. `8151581` **feat(admin): DT connector status + orphan list + cleanup endpoints** — `GET /v1/admin/dt/{status,orphans}` + `POST /v1/admin/dt/{orphans/cleanup,health-check}`. circuit-breaker snapshot + DT version 캐시.
5. `abc2244` **feat(admin): scan queue list + cancel endpoints** — `GET /v1/admin/scans` (모든 팀 join) + `POST /v1/admin/scans/{id}/cancel` (`with_for_update()` row lock, Celery revoke + status='cancelled').
6. `4596215` **feat(admin): disk usage telemetry endpoint** — workspace + dt_volume + postgres + redis. 임계치 80/90%.
7. `960f03d` **feat(admin): audit log search + CSV export endpoints** — 페이지네이션 + 필터 (`actor_user_id`, `target_table`, `action`, `from`/`to`, `q`) + StreamingResponse CSV (100k row hard cap).
8. `1ef86a7` **feat(admin): system health summary endpoint + router include** — postgres + redis + celery + dt + disk + active_scans + last_24h_errors 종합.
9. `667dd2c` **test(admin): unit + integration tests for PR #14 admin ops** — 138 신규 테스트 (unit 96 + integration 42). adversarial parametrize.
10. `cfd40ab` **fix(admin): escape CSV formula prefix in audit export (CWE-1236)** *(security-reviewer G1 흡수)* — `_csv_cell` 가 dangerous prefix (`= + - @ \t \r`) 에 `'` prepend. 12 회귀 테스트.

### 1.2 frontend (10 commit)

11. `d7eba11` **feat(i18n): admin DT/scans/disk/audit/health namespaces EN+KO** — 5 신규 namespace + 6 신규 error key.
12. `37c9e06` **feat(admin-ui): DT connector page + status card + orphan cleanup** — circuit-breaker badge + 강제 health probe + 고아 list + cleanup 버튼.
13. `530f045` **feat(admin-ui): scan queue page + drawer + cancel hook** — 4 탭 + drawer + 30s polling.
14. `1d0d2a6` **feat(admin-ui): disk telemetry page + threshold visualization** — 4 카드 + progress bar + 임계치 색상.
15. `854cc6a` **feat(admin-ui): audit log page + CSV export + diff drawer** — 인라인 filter toolbar + 300ms debounce + Playwright `download` event 호환.
16. `0d41025` **feat(admin-ui): system health dashboard** — 5~6 카드 + 30s polling.
17. `90fd933` **feat(admin-ui): admin layout sidebar + router for 5 new pages** — `AdminLayout.tsx` `NAV_ITEMS` + `router.tsx` nested 5 routes.
18. `625a673` **test(admin-ui): unit coverage for DT/scans/disk/audit/health** — Vitest 102 신규.
19. `9613f40` **feat(harness): AdminDT/Scans/Disk/Audit/Health harnesses + PortalPage entries** — 5 신규 harness 클래스 (도메인 verb) + `PortalPage.gotoAdmin{DT,Scans,Disk,Audit,Health}()`.
20. `89062ed` **test(e2e): admin 5-scenario coverage** — DT health + force-probe / Scans tab + drawer / Disk cards / Audit filter + CSV download / Health components 5/5 green (21.2s).

### 1.3 cors fix (1 commit)

21. `053f69a` **fix(cors): expose Content-Disposition for admin audit CSV export** — frontend agent 발견. axios 가 자동 파일명 읽도록.

### 1.4 main rebase merge (1 commit)

- `871cab1` **Merge remote-tracking branch 'origin/main'** — chore PR #8 (audit PII sha256, errors.py redact, frontend problem.ts zod) 흡수. PR #14 의 audit / scan / health endpoint 가 보강된 헬퍼 자동 활용.

### 1.5 security-reviewer 1라운드 결과

평결: **PASS-with-conditions** (0 Critical / 1 High → 흡수 / 4 Medium / 5 Low / 3 Info).

| ID | Severity | 요약 | 처리 |
|----|----------|------|------|
| **G1** | High | `_csv_cell` 의 CSV formula injection (CWE-1236) | **`cfd40ab` 흡수** ✅ |
| G2 | Medium | dt_orphan_cleanup_task lock 이 Celery autoretry 시 `finally` 에서 release (CWE-362) | chore PR #9 |
| G3 | Medium | admin/dt.py 의 explicit AuditLog insert 가 `request_id` / `ip` / `user_agent` 미채움 | chore PR #9 |
| G4 | Medium | `error` / `last_error` / `detail` 필드의 raw exception text 가 connection-string 누설 | chore PR #9 |
| G5 | Medium | audit `q` ILIKE 가 `%` / `_` wildcard escape 안 함 (Postgres CPU saturate 가능) | chore PR #9 |
| G6 | Low | `OrphanCleanupRequest.dt_project_uuids` 빈 리스트 = wipe-all (operational footgun) | chore PR #9 |
| G7 | Low | `DiskPathUnavailable` 예외 클래스 dead code | chore PR #9 |
| G8 | Low | audit `actor_user_id` 미존재 → 200 + empty (UX) | chore PR #9 |
| G9 | Low | `WORKSPACE_HOST_PATH` symlink → target partition 정보 leak | chore PR #9 |
| G10 | Low | `dt_orphan_cleanup` lock TTL 600s < worst-case 2500s | chore PR #9 |
| I1 | Info | `cancel_scan` revoke best-effort (intentional) | as-is |
| I2 | Info | `force_health_check` audit row 의 DT state | as-is |
| I3 | Info | CORS expose_headers 글로벌 적용 | as-is |

**Positive findings (P1~P6)**:
- 4-role auth 매트릭스 (anonymous=401 / developer=404 / team_admin=404 / super_admin=200) 모든 endpoint cover.
- SQLAlchemy parameterized queries — `text(f"...")` interpolation 0건.
- Pydantic 폐쇄 Literal whitelist (`ScanStatus` / `AuditTargetTable` / `BreakerState` / `HealthStatus`) + UUID 입력 검증 + `dt_project_uuids` 500 entry cap.
- `parseProblemBody` whitelist 6 신규 도메인 코드 + 미지 코드 graceful fallback (chore PR #8 F10 의 nested-shape 차단).
- `cancel_scan` 의 `with_for_update()` row lock — TOCTOU race 차단 (PR #11 패턴 일관).
- `AdminAuditDrawer.tsx` 의 sha256 dict 표시 — React text node only, no `dangerouslySetInnerHTML`.

## 2. 결정 사항 / 변경된 가정

- **G1 본 PR 흡수**: reviewer 가 "10-line fix + 회귀 parametrize, single-file change" 권고. operator-controlled 입력 (X-Request-ID 헤더) 가 audit row 에 들어와 super-admin 워크스테이션 RCE 가능 → 즉시 흡수.
- **chore PR #8 의 main rebase**: PR #14 backend 작업 시점에 chore PR #8 가 main 머지 안 된 상태였으나, 동시 세션에 chore PR #8 squash merge → PR #14 가 main rebase merge 로 흡수. backend agent 의 138 테스트는 sha256 hashing 적용 전 작성됐으나 sha256 적용 후 모두 pass (PII 컬럼 평문 매칭 의존 없음).
- **CSV `Content-Disposition` expose**: CORS expose_headers 글로벌 적용. 다른 endpoint 에 의도치 않게 expose 위험 negligible (Content-Disposition 은 메타데이터, 값은 server-controlled).
- **Audit `q` 검색의 PII 미매칭**: chore PR #8 F4 의 sha256 dict 때문에 평문 검색 시 PII 컬럼 (`email` / `full_name`) 매칭 0. UI 미안내. chore PR #9 G5 follow-up.
- **DT orphan cleanup task**: Read-only `dt_orphan_cleaner` (PR #5, 6h Beat) 와 별개. 본 PR 의 `dt_orphan_cleanup_task` 는 admin 트리거 전용 + Redis SETNX lock + 멱등.
- **frontend-dev 가 harness/E2E 모두 작성**: 본래 test-writer 분담이었으나 frontend-dev 에이전트가 흡수. test-writer 별도 spawn 불필요.

## 3. 현재 상태

- **GitHub PR**: https://github.com/trustedoss/trustedoss-portal/pull/15 → CI 9/9 wait + squash merge (본 세션에서 처리).
- **Commit**: 22건 (backend 10 + frontend 10 + cors fix 1 + main rebase merge 1).
- **테스트**:
  - backend: 1158 + 138 신규 = 1296 pass (단, 12 pre-existing flake — `test_project_detail_service.py` PURL 충돌, main HEAD 에서도 재현, 본 PR 무관).
  - frontend Vitest: 287 → 389 pass (102 신규). 91.74% lines / 83.42% branches.
  - Playwright E2E: 5 신규 (DT/Scans/Disk/Audit/Health) 5/5 green (21.2s) + PR #13 admin_users_teams 4/4 회귀 pass.
  - backend coverage ≥ 80% (84% ~ 100% per module).
- **DoD 충족**:
  - lint / typecheck / test green ✅
  - alembic upgrade head → 0007 ✅
  - 신규 backend coverage ≥ 80% ✅
  - 신규 frontend coverage ≥ 80% ✅ (91.74% / 83.42%)
  - E2E 5 시나리오 green ✅
  - Playwright 하네스 5개 + PortalPage 5 entry ✅
  - EN/KO 동시 5 namespace ✅
  - audit 이벤트 기록 검증 ✅ (단 G3 의 request_id/ip/user_agent 누락 backlog)
  - security-reviewer PASS (High 흡수, M/L/I follow-up 등재) ✅
  - PR #14 머지 후 admin 7 화면 모두 (Users/Teams + DT/Scans/Disk/Audit/Health) 동작 ✅

## 4. 다음 세션이 할 일

본 PR 종결. 다음:

- **chore PR #9 (admin follow-ups)** — 본 PR G2~G10 + chore PR #8 M1~M3, L1/L2 일괄. backlog memory `project_phase4_admin_followup_pr.md`. ~250 LoC 예상.
- **Phase 4 PR #15 (컴포넌트 승인 워크플로우)** — `docs/v2-execution-plan.md` §3.5 의 4.9~4.10. `/approvals` 페이지 + Pending → Under Review → Approved/Rejected 워크플로우. `_next-session-prompt-phase4-pr15-component-approval-workflow.md`.

권고 순서: PR #15 우선 (Phase 4 마무리) → chore PR #9 병렬 또는 후속.

핵심 라우팅 (PR #15):
- **db-designer**: `component_approvals` 테이블 + 상태 enum + Alembic 0008.
- **backend-developer**: `/v1/approvals` endpoint (list / approve / reject / delegate) + service.
- **frontend-dev**: `/approvals` 페이지 + drawer + 사이드바 navigation (admin 외부 모든 user 가시).
- **test-writer**: 단위 + 통합 + e2e + 하네스.
- **security-reviewer**: 1라운드.

## 5. 주의·블로커

- **chore PR #9 M1 의 audit search PII 누락**: 사용자가 audit `q` 로 email 평문 검색 시 0 결과. chore PR #9 에서 hash-on-search wrapper 또는 UI 안내 추가.
- **G2 lock release race**: `dt_orphan_cleanup_task` 의 autoretry 시 lock 이 release 되어 두 admin click 이 race. 발생 빈도 낮으나 chore PR #9 우선 처리 권고.
- **G4 connection-string leak**: `admin_disk` / `admin_health` / `admin_dt` 의 raw exception text 가 super-admin response 에 노출. asyncpg `OperationalError` 가 user/host/port 포함 가능. chore PR #9 에서 credential strip.
- **adversarial input parametrize**: PR #14 의 5 신규 도메인 (DT URL / scan filter / audit search query / disk env / orphan uuids) 모두 cover. 단 G5 (Postgres ILIKE wildcard) 는 추가 cover 권고.
- **Pre-existing flakes 12건**: test_project_detail_service.py / test_license_service.py / test_obligation_service.py / test_vulnerability_service.py 의 PURL fixture 충돌. main 에서도 재현, 본 PR 무관. chore PR #9 또는 별도 cleanup 으로 처리.
- **dev backend hot-reload stuck**: file watcher 가 가끔 stuck. `docker-compose stop --timeout 1 + up -d` 로 복구. 본 세션 중 1회 발생.

## 6. 다음 세션 시작 지시문 (복붙용)

`docs/sessions/_next-session-prompt-phase4-pr15-component-approval-workflow.md` 작성 — 본 핸드오프와 짝.
