Phase 4 PR #14 — 관리자 패널 (5 화면): DT Connector + Scan Queue + Disk + Audit Log + System Health.

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <Phase 4 PR #13 squash merge SHA, 본 세션 시작 시 `gh pr list --state merged --limit 3` 으로 확인>. 누적 머지: PR #1~#13 + chore CI fix 4건 + chore PR #1~#7. **Phase 4 PR #13 (관리자 Users/Teams) 완료**. 본 세션은 Phase 4 의 **두 번째 PR**.

## 0. 라벨링 단일 진실 (PR #13 에서 정정 완료)

- v2-execution-plan §3.5 = Phase 4 = **관리자 패널** (Users/Teams/DT/Scans/Disk/Audit/Health 7 화면 + 컴포넌트 승인 워크플로우)
- v2-execution-plan §3.7 = Phase 6 = **다국어 + 알림 + 안정성**

본 세션 = §3.5 의 4.4 ~ 4.8 (5 화면). 4.9~4.10 (컴포넌트 승인) 은 PR #15.

## 1. 이번 세션 = Phase 4 PR #14

| § | 작업 | 산출물 |
|---|------|--------|
| 4.4 | DT Connector 화면 | DT health 상태 / circuit-breaker open/close / 고아 정리 트리거 + Celery Beat 6h 주기 |
| 4.5 | Scan Queue 화면 | 실행중/대기/실패/강제종료 + WebSocket live progress |
| 4.6 | Disk 사용량 대시보드 | workspace + DT volume + DB 디스크 + 임계치 알림 |
| 4.7 | Audit Log 화면 | 검색/필터/CSV export, time-range + actor + target_table |
| 4.8 | System Health 대시보드 | postgres / redis / celery worker / DT / disk 한 화면 요약 |

PR #13 가 admin 인프라 (라우터 가드 / AdminLayout / i18n namespace / 하네스) 를 갖춰뒀으므로 본 PR 은 **그 위에 5 화면 추가** 만.

## 2. 직전 핸드오프 (반드시 시작 시 읽기)

- `docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md` — **본 PR 의 직전 PR**. admin 인프라 + 14 commit + security-reviewer 결과 + chore PR #8 backlog (F2~F12). 본 세션의 admin 화면은 동일 패턴 (`require_super_admin_or_404` + RFC 7807 + audit auto-emit + `with_for_update` for last-X-admin) 따라야.
- `docs/v2-execution-plan.md §3.5` — 4.4~4.8 단일 진실.
- `CLAUDE.md` "주요 기능 / 관리자" + "DT 연동 전략".

## 3. 시작 시 검증 (반드시)

```
docker-compose -f docker-compose.dev.yml ps               # 6/6 healthy (backend hot-reload stuck 시 stop --timeout 1 + up -d)
docker-compose -f docker-compose.dev.yml -f docker-compose.dt.yml ps  # +dtrack-api healthy
gh run list --limit 3                                      # main 최신 success
git status                                                 # working tree
```

main 의 working tree 잔여:
- `.claude/scheduled_tasks.lock` — 무시.
- `docs/review-binaryanalysis-ng.md` — 사용자 작업 중 doc, 무시.
- 본 prompt (`_next-session-prompt-phase4-pr14-...`) — 세션 종료 시 archive.

브랜치: `feature/phase4-pr14-admin-dt-scans-disk-audit-health` 신규 생성.

## 4. 작업 절차

### 4.4 DT Connector 화면

**백엔드** `apps/backend/api/v1/admin/dt.py`:
- `GET /v1/admin/dt/status` — DT health (last_check_at, ok/degraded/down), circuit-breaker state, last_error, version.
- `GET /v1/admin/dt/orphans` — 포털에 없는데 DT 에 있는 project 목록.
- `POST /v1/admin/dt/orphans/cleanup` — 고아 일괄 정리 (Celery task 트리거).
- `POST /v1/admin/dt/health-check` — 강제 health probe.

**Celery**: `apps/backend/tasks/dt_orphans.py` (또는 기존 dt_resync 확장) — Celery Beat 6h 주기 + 수동 트리거 endpoint.

**서비스**: `apps/backend/services/admin_dt_service.py` — DT client (이미 존재) 호출 + 상태 캐싱.

**프론트** `apps/frontend/src/features/admin/dt/AdminDTPage.tsx`:
- 상단 카드 (status badge / circuit-breaker / version).
- 하단 고아 정리 테이블 + "정리 실행" 버튼 (확인 다이얼로그).

### 4.5 Scan Queue 화면

**백엔드** `apps/backend/api/v1/admin/scans.py`:
- `GET /v1/admin/scans` — 페이지네이션 + status 필터 + project/team join. 모든 팀 가시.
- `POST /v1/admin/scans/{scan_id}/cancel` — 강제 종료 (Celery revoke + status='cancelled').

**프론트** `AdminScansPage.tsx`: 4 탭 (실행중 / 대기 / 실패 / 전체) + 행 클릭 = drawer (project / team / 진행률 / 에러). WebSocket subscribe (기존 `useScanWebSocket`).

### 4.6 Disk 사용량 대시보드

**백엔드** `apps/backend/api/v1/admin/disk.py`:
- `GET /v1/admin/disk` — workspace dir 사용량 (host filesystem) / DT volume / postgres DB size / redis. 임계치 (80% / 90%) 함께 반환.
- `os.statvfs` 또는 `shutil.disk_usage` 사용 (런타임 호출, CLAUDE.md 규칙 #11).
- DT volume / postgres 는 docker-compose volume mount path 기반 — `WORKSPACE_HOST_PATH` env (`.env.example`) 활용.

**프론트** `AdminDiskPage.tsx`: 4 카드 (workspace/DT/postgres/redis) + 게이지 + 임계치 위반 시 빨강 강조.

### 4.7 Audit Log 화면

**백엔드** `apps/backend/api/v1/admin/audit.py`:
- `GET /v1/admin/audit` — 페이지네이션 + 필터 (`actor_user_id`, `target_table`, `action`, `from`/`to`, `q` 텍스트 search on diff JSONB).
- `GET /v1/admin/audit/export.csv` — 동일 필터 + streaming response (큰 dataset 대비).

**서비스** `services/admin_audit_service.py` — `audit_logs` 테이블 (이미 존재) 쿼리. `target_table` enum 값 다양 (users, teams, projects, scans, components, license_findings, vuln_findings, ...).

**프론트** `AdminAuditPage.tsx`: 인라인 필터 + 컴팩트 테이블 + CSV 다운로드 버튼.

**중요**: chore PR #8 의 F4 (audit_logs.diff 의 email/full_name PII 마스킹) 가 본 PR 머지 *전*에 들어오면 좋다. 들어오기 전이면 본 PR audit 테이블이 평문 PII 표시 — 스크린샷 / 데모 시 주의. PR #14 가 chore PR #8 와 병렬이면 머지 순서 조율 필요.

### 4.8 System Health 대시보드

**백엔드** `apps/backend/api/v1/admin/health.py`:
- `GET /v1/admin/health` — postgres / redis / celery worker / DT / workspace disk / 활성 스캔 수 / 최근 24h 오류 수.
- 각 컴포넌트 = green/yellow/red.

**프론트** `AdminHealthPage.tsx`: 5~6 카드 한 화면 + 30 초 polling (TanStack Query refetchInterval).

### 4.9 사이드바 navigation 확장

`AdminLayout.tsx` (PR #13) 의 사이드바 항목 5개 추가: DT / Scans / Disk / Audit / Health. 5 신규 i18n 키 (`nav.admin.dt` 등) EN/KO 동시.

## 5. RFC 7807 + 에러 응답

PR #13 와 동일. 도메인 확장 필드:
- `dt_unreachable` (503)
- `dt_orphan_cleanup_in_progress` (409)
- `scan_already_cancelled` (409)
- `disk_threshold_exceeded` (200, body 의 warning 으로 — 4xx 아님)

## 6. 단위 + 통합 + E2E

### 6.1 단위 (pytest)

- `test_admin_dt_service.py` — DT client mock + circuit-breaker 상태 → 각 endpoint 응답 핀.
- `test_admin_scans_service.py` — 페이지네이션 / status filter / cancel 의 멱등성 (이미 cancelled 면 409).
- `test_admin_disk_service.py` — `shutil.disk_usage` mock + 임계치 경계.
- `test_admin_audit_service.py` — 필터 조합 / CSV streaming 형식 / `target_table` enum.
- `test_admin_health_service.py` — 각 컴포넌트 down/up 시 종합 status.
- adversarial input parametrize (chore PR #7 교훈): audit search query / disk path / DT URL 등.

### 6.2 통합

- 4-role 매트릭스 (anonymous=401 / developer=404 / team_admin=404 / super_admin=200) 5 endpoint 모두.
- audit log 자동 기록 (DT cleanup / scan cancel).

### 6.3 E2E (Playwright)

`apps/frontend/tests/e2e/admin_dt_scans_disk_audit_health.spec.ts`:
- 시나리오 1 — DT health 조회 + 고아 정리 트리거 + audit row 검증.
- 시나리오 2 — Scan Queue 진입 + 실행 중 스캔 강제 종료 + 상태 변화 핀.
- 시나리오 3 — Disk 임계치 mock 후 빨강 카드 렌더 핀.
- 시나리오 4 — Audit log 검색 + CSV 다운로드 (Playwright `download` event).
- 시나리오 5 — System Health 5 컴포넌트 모두 green.

`tests/_harness/` 신규 5 harness 클래스 (각 화면당 1개, PR #13 패턴).

## 7. i18n (EN / KO 동시)

`apps/frontend/src/locales/{en,ko}/admin.json` 확장 (PR #13 의 namespace 그대로 사용):
- `nav.admin.{dt,scans,disk,audit,health}`
- `admin.dt.*` / `admin.scans.*` / `admin.disk.*` / `admin.audit.*` / `admin.health.*`

## 8. 핵심 라우팅

- **backend-developer** (필수): 5 endpoint + audit search + Disk telemetry + DT 상태/고아 endpoint.
- **scan-pipeline-specialist** (필수): DT health monitor + 고아 정리 Celery task (CLAUDE.md "DT 연동 전략" + chore PR #5 의 dt_resync 패턴 확장).
- **frontend-dev** (필수): 5 admin 화면 + 사이드바 확장 + EN/KO i18n.
- **test-writer** (필수): 단위 + 통합 + e2e 5 시나리오 + harness 5개.
- **security-reviewer** (필수): Producer-Reviewer 1 라운드 — RBAC / IDOR / DT URL 검증 / disk path traversal / audit search SQL injection / CSV streaming size cap.

## 9. 설계 제약

- PR #13 의 모든 제약 동일.
- **Disk endpoint 은 host filesystem 정보 노출** — 경로 정규화 + path traversal 차단 필수.
- **Audit search 의 JSONB `q` 필터** — adversarial input parametrize (memory `feedback_adversarial_input_parametrize`). SQL injection / `jsonb_path_query` 의 prepared statement 검증.
- **CSV streaming** — 대용량 (10만 행+) 가능. response chunking + 메모리 캡.
- **Scan cancel** — Celery revoke 의 race (이미 종료된 task) 를 422 / 409 로 변환.
- DT Celery 고아 정리 task 는 멱등 (반복 실행 안전).
- 모든 admin endpoint = `require_super_admin_or_404` (PR #13 패턴).

## 10. DoD

- main CI 9/9 success.
- ruff / mypy / npm lint / npm typecheck clean.
- 신규 코드 backend coverage ≥ 80%, frontend coverage ≥ 80%.
- E2E 5 시나리오 green.
- Playwright 하네스 verb 추가.
- EN/KO 번역 동시.
- audit 이벤트 기록 검증.
- security-reviewer PASS.
- PR #14 squash merge 후 admin 7 화면 모두 (Users/Teams + DT/Scans/Disk/Audit/Health) 동작.

## 11. 비주문 (PR #14 scope 외)

- 컴포넌트 승인 워크플로우 → **PR #15**.
- 알림 (이메일/Slack/Teams) → **Phase 6 PR #18**.
- chore PR #8 (PR #13 의 F2~F12 follow-up) → **별도 chore PR**.

## 12. 세션 종료 시

- `docs/sessions/2026-05-XX-phase4-pr14-admin-dt-scans-disk-audit-health.md` 핸드오프.
- 본 prompt → `docs/sessions/archive/next-session-prompts/`.
- 다음 세션 prompt: `_next-session-prompt-phase4-pr15-component-approval-workflow.md` 작성.

본 작업 예상 시간: 10~14 시간.
