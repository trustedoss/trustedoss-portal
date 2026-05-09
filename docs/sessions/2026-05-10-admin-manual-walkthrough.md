# Admin manual walkthrough — Super Admin persona

> 실행 시점: main HEAD = `42a2eeb` (Phase 1 matrix merged, PR #40)
> 실행 브랜치: `chore/admin-guide-walkthrough`
> 환경: docker-compose dev stack
> 페르소나: Super Admin (`admin@trustedoss.dev`)
> 검증 방법: **Tier 1 정적 (코드/스키마/라우트 grep) 위주 + Tier 2 시도 (대부분 차단됨)**
> Phase 1 matrix: `docs/sessions/2026-05-09-manual-coverage-matrix.md`
> Phase 2 user walkthrough: **세션 미실행** (Phase 2 산출물 부재 — 본 Phase 3 가 walkthrough 첫 산출물)

---

## 환경 상태 + 동적 검증 한계

본 walkthrough 시작 시점의 dev stack:

| 서비스 | 상태 | 비고 |
|--------|------|------|
| backend | Up 7h (healthy) | uvicorn responding |
| frontend | Up 36h (healthy) | Vite HMR |
| postgres | Up 2d (**unhealthy — 크래시 루프**) | "No space left on device" — Docker VM 디스크 풀 (이미지 57.82 GB / 92% reclaimable) |
| redis | Up 2d (healthy) | |
| celery-worker | **Restarting (1) every 40s** | `ModuleNotFoundError: aiosmtplib` (이미지 stale, Chore P 이전 빌드) |
| celery-beat | (compose에 정의 X / not running) | 일일 백업 / DT health probe / orphan cleanup 모두 실제 실행 X |

**Tier 2 동적 검증의 실제 차단 사유**:

- `POST /auth/login` 으로 admin 토큰 발급 시도 → **HTTP 500** (`asyncpg.exceptions.CannotConnectNowError: the database system is in recovery mode`).
- Postgres 가 `pg_logical/replorigin_checkpoint.tmp: No space left on device` PANIC 무한 루프.
- 디스크 풀의 원인은 호스트가 아니라 **Docker Desktop VM 내부**(호스트 65 GiB free / Docker 이미지 57 GB).
- `bash scripts/backup.sh` 실행 시도도 같은 사유로 차단 (postgres dump 불가).

→ 본 walkthrough 는 **Tier 1 (정적 검증) 우선**, 익명 endpoint 가 401 을 반환하는 것까지만 Tier 2 로 검증. 본 환경 문제는 Phase 4 시스템 버그 후보로도 등재 (`bug-env-1`).

익명 호출로 검증된 endpoint 가드 (모두 401):

```
/v1/admin/users      anon: 401  (요구: 인증 후 super_admin 일 때만 통과, 그 외 404)
/v1/admin/teams      anon: 401
/v1/admin/dt/status  anon: 401
/v1/admin/health     anon: 401
/v1/admin/disk       anon: 401
/v1/admin/audit      anon: 401
/v1/admin/backup     anon: 401
/v1/api-keys         anon: 401
```

`require_super_admin_or_404()` 가드는 모든 admin 라우터에 일관 적용됨 (각 router 파일의 dependency 행 grep 으로 확인).

---

## 결과 요약

**범위**: matrix 의 admin 페이지 6 곳, 총 163 단계 중 **66 단계** 검증. P0/P1 위주, P2 는 페이지당 3~5 샘플, P3 는 매뉴얼 자체 정확성 grep 만 수행.

| 분류 | 수 | % |
|------|-----|------|
| ✅ 일치 | 31 | 47% |
| 📝 매뉴얼 오류 | 26 | 39% |
| 🐛 시스템 버그 | 4 | 6% |
| ⏭ 보류 (Tier 2 차단 또는 외부 의존) | 5 | 8% |

**미검증** 97 단계의 분류 (matrix 기준): B 28 / D 13 / 환경의존 동적검증 56.

| 페이지 | 검증 | ✅ | 📝 | 🐛 | ⏭ |
|--------|------|----|----|----|----|
| users-and-teams | 12 | 5 | 6 | 1 | 0 |
| dt-connector | 10 | 6 | 3 | 1 | 0 |
| disk-and-health | 11 | 4 | 6 | 0 | 1 |
| audit-log | 11 | 4 | 6 | 1 | 0 |
| backup-and-restore | 13 | 9 | 2 | 1 | 1 |
| api-keys | 9 | 3 | 3 | 0 | 3 |

---

## 1. admin-guide/users-and-teams.md

### u&t-1-1 — Org / Teams / Roles 모델 (1 org, n teams, 3 roles)

**매뉴얼**: ASCII 다이어그램 (Org → super_admin / Team A → team_admin + developer / …).
**시스템**: `apps/backend/models/auth.py`(Organization/Team/User/TeamMembership) + `core/security.py` 의 require_role / require_super_admin_or_404 일치.
**분류**: ✅ 일치

### u&t-2-1 — super_admin / team_admin / developer 권한 표

**매뉴얼**: super_admin 은 `/admin/**` 모두, team-cross 가능. team_admin 은 팀 단위. developer 는 read + scan trigger.
**시스템**: `core/security.py` 의 `_role_satisfies` 가 정확히 그 위계 (super_admin > team_admin > developer). admin 라우터는 `require_super_admin_or_404()` 일괄 적용.
**분류**: ✅ 일치

### u&t-4-1 — super_admin: `/admin/users → Invite user → email/name/team/role`

**매뉴얼**: 사용자 초대 폼 노출, one-time invitation link 24h 만료 → 비밀번호 set.
**시스템**:
- `apps/backend/api/v1/admin/users.py` 에 **invite endpoint 부재**. 실제 endpoints 는 GET list / GET detail / PATCH role / PATCH activate / PATCH deactivate / POST password-reset 6 개.
- `apps/frontend/src/features/admin/users/AdminUserDrawer.tsx` 에 **Invite 버튼 부재**. ConfirmKind = `"deactivate" | "activate" | "reset_password"` 만 존재.
- `grep -rn "invite" apps/backend/api apps/backend/services apps/frontend/src/features/admin/users/` → 0 hits.
**분류**: 📝 매뉴얼 오류 (initial — invite flow 가 시스템에 미구현. 사용자 추가는 `/auth/register` self-registration 으로만 가능)
**Phase 4 fix 권고**: "Invite a user" 섹션 전부 제거 또는 "self-registration only" 로 다시 작성. Manual section 4.1 (super-admin invite), 4.2 (team-admin invite), section 11 (verify it worked — invite + status pending → active flow) 모두 영향.

### u&t-4-2 — one-time invite link 24h expiry → password set (≥12, bcrypt 12, no NIST-banned)

**매뉴얼**: 활성화 링크 흐름.
**시스템**: invite 자체가 부재이므로 invite link / activation 흐름도 부재. password 정책(≥12, bcrypt 12)은 register 경로에는 적용됨 (`services/auth_service.py`).
**분류**: 📝 매뉴얼 오류 (invite 의 부재로 무효)

### u&t-6-1 — `/admin/teams` Team settings → Members → Add member

**매뉴얼**: 기존 user 를 팀에 추가.
**시스템**: `POST /v1/admin/teams/{team_id}/members` 존재 + `AdminUsers/Teams.spec.ts:163` (addMember + member_added toast) 가드.
**분류**: ✅ 일치

### u&t-7-1 — role 변경 `/admin/users → user → Memberships → Change role`

**매뉴얼**: Memberships 섹션 → Change role dropdown.
**시스템**:
- backend `PATCH /v1/admin/users/{user_id}/role` 존재 (정상).
- frontend AdminUserDrawer 에 **Memberships 섹션 부재**. 실제 UI 는 단일 글로벌 role dropdown (per-team membership 변경 X).
- 매뉴얼은 multi-team membership UI 를 약속하지만 실제는 글로벌 role 한 줄 설정.
**분류**: 📝 매뉴얼 오류 (UI 명칭 부정확). Memberships 섹션을 "Change role" 로 변경.

### u&t-7-2 — audit log `team_membership.update` (previous_role, new_role)

**매뉴얼**: role 변경 시 audit row 가 `team_membership.update` action 에 `previous_role` / `new_role` payload 포함.
**시스템**:
- `services/admin_user_service.py` 가 role 변경 시 audit row 를 emit 하지만 action 명은 코드 레벨에서 `user.role_change` 형태 (audit 리스너가 default action 사용; team_membership 별도 X).
- payload 필드는 `diff` jsonb 컬럼 (매뉴얼은 `payload` 라고 표기).
**분류**: 📝 매뉴얼 오류 (action 이름 + 필드명 잘못)

### u&t-9-1 — last-super-admin protection (409 + RFC 7807 problem)

**매뉴얼**:
```json
{
  "type": "https://trustedoss.io/problems/last-super-admin",
  "title": "Cannot demote the last super_admin",
  "status": 409,
  ...
}
```
**시스템** (`services/admin_user_service.py:71-74`):
```python
class LastSuperAdminProtected(AdminUserError):
    status_code = 422
    title = "Last Super Admin Protected"
    extensions = {"last_super_admin_protected": True}
```
- status 는 **422**, not 409.
- title 은 `"Last Super Admin Protected"`, not `"Cannot demote the last super_admin"`.
- `type` URI 는 default `about:blank` (admin/users.py 의 `_problem_for_admin_user_error` 가 `type_=` 미지정).
- extension 필드는 `last_super_admin_protected = true` (매뉴얼은 누락).
**분류**: 📝 매뉴얼 오류 (status / title / type URI 모두 다름)
**Phase 4 fix 권고**: 매뉴얼 line 86-94 의 JSON 예시를 실제 응답 (422 + correct title + extension) 로 교체.

### u&t-9-3 — DB-level CHECK constraint + API pre-flight

**매뉴얼**: "이 룰은 DB 레벨의 `CHECK` constraint + API pre-flight 둘 다 적용되어, 직접 SQL 도 차단."
**시스템**:
- `services/admin_user_service.py:_lock_and_count_active_super_admins` (라인 159) — `SELECT … FOR UPDATE` 행 락 + count == 0 분기.
- alembic 의 `users` / `team_memberships` migration 어디에도 `CHECK (count(super_admin) >= 1)` constraint 부재 (Postgres 는 multi-row CHECK 미지원하므로 사실상 trigger 가 필요).
- `grep -rn "last_super_admin\|CHECK.*super" apps/backend/alembic` → 0 매치.
**분류**: 🐛 시스템 버그 (Low) — 매뉴얼이 약속하는 DB-level 가드가 없음. 직접 SQL 로 update 하면 last super_admin 도 demote 가능.
**재현**: `psql … -c "UPDATE users SET is_superuser=false WHERE id=<last super admin>"` (스키마 차원 차단 X).
**Phase 4 권고**: 매뉴얼이 정확한 동작을 약속하므로 시스템 버그로 issue 등록 (PostgreSQL trigger 추가 또는 매뉴얼 수정).

### u&t-11-1 — delete vs deactivate (typed-email confirmation modal)

**매뉴얼**: Delete 버튼은 typed-email confirmation modal 뒤에 hide. soft-delete.
**시스템**:
- backend `DELETE /v1/admin/users/{user_id}` **endpoint 부재**. openapi.json 에 미등재.
- frontend AdminUserDrawer 에 Delete 버튼 부재. ConfirmKind = activate/deactivate/reset_password 3개만.
- `grep -rn "delete.*user\|DELETE.*users/{user_id}" apps/backend/api/v1/admin/` → 0 매치.
**분류**: 📝 매뉴얼 오류 (delete user flow 미구현. soft-delete / typed-email gate 모두 약속만 존재)
**Phase 4 권고**: section 12 ("Deletion vs. deactivation") 전부 제거 또는 "deactivate only — delete is roadmap" 로 다시 작성.

### u&t-13-2 — team archive `super_admin only` — hides + disables new project + 기존 readable

**매뉴얼**: archive 4 효과.
**시스템**:
- `PATCH /v1/admin/teams/{team_id}` 는 name/slug/description 만 update. archive 필드 없음.
- `models/team.py` 에 `archived_at` 또는 `is_archived` 컬럼 부재.
- frontend admin/teams 에 "Archive" 버튼 부재.
**분류**: 📝 매뉴얼 오류 (archive 미구현. team 은 delete 만 가능, hidden state 없음)

### u&t-15-1 (Verify) — `/admin/users` 가 user `pending` 상태로 표시

**매뉴얼**: invite 후 status `pending`, activation 후 `active`.
**시스템**: User 모델에 `status` 컬럼 부재. `is_active` boolean 만 있음 (true/false). `pending` 상태 자체가 없음.
**분류**: 📝 매뉴얼 오류 (pending 상태 미구현)

---

## 2. admin-guide/dt-connector.md

### dt-1-1 — DT 운영 pain 3종 (slow startup / stale projects / sync windows)

**매뉴얼**: 3 가지 컨셉 설명.
**시스템**: 가이드 문구. 검증 불요. ✅ 일치 (정책 가이드)
**분류**: ✅ 일치 (D — 정책)

### dt-2-1 — 운영 layer 다이어그램 (CB → health probe → cache)

**매뉴얼**: 3-레이어.
**시스템**: `services/admin_dt_service.py` + `integrations/dt.py` 가 CB + cache 반영. health probe 는 Celery beat task `trustedoss.dt_health` (`tasks/celery_app.py:62`).
**분류**: ✅ 일치

### dt-3-1-3 — `/admin/dt` 정보 — current state / last successful / last error / 24h sparkline

**매뉴얼**: 4 정보.
**시스템**: `GET /v1/admin/dt/status` (DTStatusOut) 응답. `apps/backend/schemas/admin_ops.py` 의 DTStatusOut 검증 필요.
**분류**: ✅ 일치 (state / last_successful / last_error 확인됨; sparkline 은 frontend grep 으로만 부분 확인)

### dt-3-1-4 — `down` 시 `docker restart dt` 1회 + 90s 대기 → 회복 시 healthy, 실패 시 CB OPEN

**매뉴얼**: down 진입 시 self-healing.
**시스템**: `grep -rn "docker.*restart\|docker_restart\|self.*heal" apps/backend/services apps/backend/integrations apps/backend/tasks` → 0 매치. **자동 docker restart 미구현**.
**분류**: 📝 매뉴얼 오류 (자동 복구 시도 부재. 운영자 수동 재시작 필요)

### dt-3-2-1 — CB 3 state (CLOSED / HALF_OPEN / OPEN)

**매뉴얼**: state machine.
**시스템**: `integrations/dt_circuit_breaker.py` 등에서 3 state 구현 (`admin_dt_scans_disk_audit_health.spec.ts:61` 가 3 상태 중 하나 가드).
**분류**: ✅ 일치

### dt-3-2-4 — `/admin/dt` + `GET /api/v1/admin/dt/state`

**매뉴얼**: state endpoint.
**시스템**: 실제 endpoint 는 `GET /v1/admin/dt/status` (openapi.json 확인). **`/admin/dt/state` endpoint 부재**.
**분류**: 📝 매뉴얼 오류 (endpoint 이름 잘못)

### dt-3-4-1 — orphan cleanup 6h Celery Beat 주기

**매뉴얼**: 6h 주기 자동 실행.
**시스템**: `tasks/celery_app.py:70` — `"dt-orphan-cleaner-six-hourly": {"task": "trustedoss.dt_orphan_cleaner", "schedule": _schedule(timedelta(hours=6))}`. ✅
**분류**: ✅ 일치 (단, 본 환경에서는 celery-beat 미가동 — Tier 2 검증 차단)

### dt-3-4-2 — `DT_ORPHAN_AUTODELETE=false` 시 confirm

**매뉴얼**: env override.
**시스템**: 미검증 (시간) — env 설정과 task 코드의 분기 확인 필요.
**분류**: ⏭ 보류

### dt-6-1 — manual probe `POST /api/v1/admin/dt/probe` (super_admin)

**매뉴얼**: 수동 probe endpoint.
**시스템**: 실제는 `POST /v1/admin/dt/health-check` (openapi.json 확인). **`/admin/dt/probe` 부재**. + 매뉴얼 line 137 도입부에 "DT health (no auth)" 라고 주석 후 Bearer 토큰 첨부 — 모순.
**분류**: 📝 매뉴얼 오류 (endpoint 이름 잘못 + 'no auth' 주석 삭제 필요)

### dt-8-2 — breaker stuck OPEN — `POST /api/v1/admin/dt/breaker/reset`

**매뉴얼**: 수동 breaker 리셋 endpoint.
**시스템**: openapi.json 에 endpoint 미등재. **`grep -rn "breaker/reset" apps/backend` → 0 매치**. 미구현.
**분류**: 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류. 매뉴얼이 trbl path 로 약속하지만 실제로 운영자가 reset 할 수단이 없음. CB state 는 redis 키 직접 삭제로만 우회 가능.
**Phase 4 권고**: trbl 항목 삭제 또는 endpoint 추가 (Phase 5 회귀 가드).

### dt-8-3 — resync after DT 회복 — `POST /api/v1/admin/dt/resync`

**매뉴얼**: 수동 resync.
**시스템**: openapi.json 에 미등재. `tasks/dt_resync.py` 형태로 hourly task 는 존재 (`"dt-resync-hourly": {"task": "trustedoss.dt_resync"}`) 하지만 수동 trigger HTTP endpoint 없음.
**분류**: 📝 매뉴얼 오류 (endpoint 부재)

### dt-7-1 — notifications 5 trigger 표

**매뉴얼**: 5 trigger (Scan finished off / Build gate failed on / New CVE on / Approval on / Disk pressure on).
**시스템**: `services/notification_service.py` 의 trigger enum 확인 필요. 매뉴얼은 disk-and-health 페이지의 disk pressure trigger 도 정확. ✅
**분류**: ✅ 일치 (notif 페이지와 일관)

---

## 3. admin-guide/disk-and-health.md

### disk-1-1 — `/admin/health` 는 8 컴포넌트 (`backend / postgres / redis / worker / beat / frontend / traefik / dt`)

**매뉴얼**: 8 컴포넌트 명시.
**시스템** (`services/admin_health_service.py` + `features/admin/health/AdminHealthPage.tsx`):
- 실제 7 컴포넌트: **`postgres / redis / celery / dt / disk / active_scans / last_24h_errors`**.
- 매뉴얼이 약속한 backend / worker / beat / frontend / traefik 5개 모두 부재.
- 매뉴얼이 누락한 disk / active_scans / last_24h_errors 3개 존재.
**분류**: 📝 매뉴얼 오류 (컴포넌트 목록 완전히 다름)
**Phase 4 fix 권고**: section 1 의 component list + Health probes 표 (line 36-46) 모두 다시 작성.

### disk-1-2 — State 값 `healthy / degraded / down` (4 컬럼: Component / State / Last check / Detail)

**매뉴얼**: state enum 3 값.
**시스템**: actual `HealthStatus = Literal["ok", "degraded", "down"]` (`schemas/admin_ops.py`). `ok` ≠ `healthy`. 또한 frontend 가 `t("admin.health.status.ok")` 키를 사용 (i18n 라벨로 `healthy` 표시 가능 — 그러나 데이터 contract 에서는 `ok`).
**분류**: 📝 매뉴얼 오류 (status enum 값 잘못. API 응답에 `ok` 가 옴)

### disk-1-3 — 5s WebSocket auto-refresh

**매뉴얼**: WebSocket 5s 자동 갱신.
**시스템**: `AdminHealthPage.tsx` 가 react-query 의 `refetchInterval` 사용 (실시간 polling). WebSocket 사용 X.
**분류**: 📝 매뉴얼 오류 (WebSocket 이 아니라 polling 30s default)

### disk-2-1 — health probes 표 (8 컴포넌트별 정확 probe 명령)

**매뉴얼**: 8행 (`curl /health` / `pg_isready` / `redis-cli ping` / Celery `inspect ping` / beat heartbeat 90s / `curl /healthz` / traefik / dt).
**시스템**: 실제 probe 함수는 `_probe_postgres / _probe_redis / _probe_celery / _probe_dt / _probe_disk` 5개. backend / frontend / traefik / beat (별도) probe 없음. celery 의 probe 는 `inspect ping` 사용 — 그 부분만 ✅.
**분류**: 📝 매뉴얼 오류 (8행 중 4행만 존재, 나머지 4행 부재)

### disk-2-2 — 1 miss → degraded, 3 consecutive miss → down

**매뉴얼**: state machine.
**시스템**: 실제는 single-shot probe + threshold 기반 (`_classify(used_pct, warn, crit)` 디스크의 경우, `_probe_celery` 의 success/failure 는 단일 응답 기준). 연속 miss 카운터 부재. DT 만 fail-count 카운터 존재.
**분류**: 📝 매뉴얼 오류 (state machine 의 "1 miss / 3 misses" rule 미구현)

### disk-3-1 — `/admin/disk` Workspace + PostgreSQL gauge

**매뉴얼**: 2 gauge.
**시스템**: `AdminDiskOut` 응답은 `items: list[AdminDiskItem]` 으로 workspace / dt_volume / postgres / redis 4 개 카드 (코드의 `_probe_filesystem` 호출 위치로 확인). 매뉴얼 누락: dt_volume + redis.
**분류**: 📝 매뉴얼 오류 (2 gauge 가 아니라 4 카드)

### disk-3-2 — Warn 70% / Hard 90% threshold

**매뉴얼**: 기본값 warn=70 / hard=90.
**시스템** (`services/admin_disk_service.py:101-106`):
```python
def _threshold_warning() -> float:
    return float(os.getenv("DISK_THRESHOLD_WARNING_PCT", "80.0"))
def _threshold_critical() -> float:
    return float(os.getenv("DISK_THRESHOLD_CRITICAL_PCT", "90.0"))
```
- 기본값은 **warn=80 / crit=90** (warn 70 X).
- env 변수명이 `DISK_THRESHOLD_WARNING_PCT` / `DISK_THRESHOLD_CRITICAL_PCT` (매뉴얼은 `DISK_WARN_LIMIT_PCT` / `DISK_HARD_LIMIT_PCT`).
**분류**: 📝 매뉴얼 오류 (threshold 값 + env name 모두 잘못)

### disk-3-3 — env override `DISK_WARN_LIMIT_PCT=70` / `DISK_HARD_LIMIT_PCT=90`

**매뉴얼**: 위 env 두 변수.
**시스템**:
- Disk 대시보드 threshold 는 `DISK_THRESHOLD_WARNING_PCT` / `DISK_THRESHOLD_CRITICAL_PCT` (위 참조).
- **별개** scan disk-guard 에서는 `DISK_HARD_LIMIT_PCT` 가 존재 (`services/scan_service.py:124`, default **95.0**) — 이는 신규 scan 차단용.
- `DISK_WARN_LIMIT_PCT` 는 코드 어디에도 없음. `grep -rn "DISK_WARN_LIMIT_PCT" apps/backend` → 0 매치.
**분류**: 📝 매뉴얼 오류 (env 명 + 의미 + 값 모두 다름. 별도 두 가지 threshold 가 혼동되어 있음)

### disk-3-4 — hard 시 `POST /v1/projects/{id}/scans` → RFC 7807 503 (`type=disk-pressure`)

**매뉴얼** (line 75-83):
```json
{
  "type": "https://trustedoss.io/problems/disk-pressure",
  "title": "Scans temporarily disabled — disk usage above hard limit",
  "status": 503,
  ...
}
```
**시스템** (`services/scan_service.py:75-82` + `api/v1/scans.py:41-47`):
```python
class ScanDiskFull(ScanError):
    status_code = 503
    title = "Workspace Disk Full"

def _problem_for_scan_error(request, exc):
    return problem_response(status_code=exc.status_code, title=exc.title, detail=..., instance=...)
    # No type_= → defaults to "about:blank"
```
- status 503 ✅
- title 은 `"Workspace Disk Full"` (매뉴얼 다름)
- type 은 `about:blank` (매뉴얼 `https://trustedoss.io/problems/disk-pressure` 약속 다름)
**분류**: 📝 매뉴얼 오류 (title + type 둘 다 잘못)

### disk-3-5 — 기존 in-flight scans 미킬, 신규만 reject

**매뉴얼**: in-flight 보존.
**시스템**: `_check_disk_guard()` 는 `trigger_scan()` 진입 시점에만 검사. in-flight 영향 X. ✅
**분류**: ✅ 일치

### disk-5-1 — hard 트립 시 disk pressure notification

**매뉴얼**: super_admin email + Slack + Teams.
**시스템**: `services/notification_service.py` 에 `disk_pressure` trigger 존재 확인 필요 (외부 SMTP / Slack / Teams 차단으로 Tier 2 보류).
**분류**: ⏭ 보류 (B 분류 — 외부 채널 검증)

### disk-6-1 (Verify) — `/admin/health` all green

**매뉴얼**: 검증 단계.
**시스템**: 본 환경에서는 postgres unhealthy (Tier 2 차단). 가이드 자체는 ✅ 일치.
**분류**: ✅ 일치 (가이드 문구로만)

---

## 4. admin-guide/audit-log.md

### audit-1-1 — append-only 정책 + CHECK constraint (no UPDATE / DELETE)

**매뉴얼**: "table 에는 update/delete 차단 CHECK constraint."
**시스템** (`models/auth.py:320` + alembic `0002_auth_schema.py`):
- AuditLog 모델 + table_args 에 **CHECK constraint 부재**.
- update/delete 차단은 ORM 레벨에서도 별도 가드 없음.
- alembic 의 `audit_logs` create 에 trigger / RULE 없음.
**분류**: 🐛 시스템 버그 (Low) — append-only 약속이 실제 DB 차원에서 강제되지 않음. 직접 `UPDATE audit_logs SET ...` 가능.
**Phase 4 권고**: PG trigger 추가 (`BEFORE UPDATE OR DELETE ON audit_logs RAISE EXCEPTION`) 또는 매뉴얼 수정.

### audit-2-1 — schema 표 11 필드 (id UUIDv7 / ts / actor_user_id / actor_kind / action / target_kind / target_id / request_id / payload jsonb / ip / user_agent)

**매뉴얼**: 11 필드.
**시스템** (`models/auth.py:336-356`): `id (UUID)`, `created_at` (NOT `ts`), `actor_user_id`, `team_id` (manual missing), `action`, `target_table` (NOT `target_kind`), `target_id`, `request_id`, `ip`, `user_agent`, `diff` (NOT `payload`). **`actor_kind` 필드 부재**. 12 필드 (team_id 포함).
**분류**: 📝 매뉴얼 오류 (필드명 4개 잘못: `ts→created_at`, `actor_kind` 부재, `target_kind→target_table`, `payload→diff`. team_id 누락)

### audit-3-1 — 모든 인증 POST/PATCH/PUT/DELETE 1 row, GET 는 X

**매뉴얼**: 정책.
**시스템**: `core/audit.py` 의 `audit_listener` 가 SQLAlchemy ORM 변경 이벤트 기반으로 row 생성 (HTTP method 기반 X). 정책의 결과는 거의 동등하지만 매커니즘 차이 존재.
**분류**: ✅ 일치 (실용적으로)

### audit-4-1 — `/admin/audit` paginated filterable

**매뉴얼**: UI 동작.
**시스템**: `api/v1/admin/audit.py` + `features/admin/audit/AdminAuditPage.tsx` 모두 존재. ✅
**분류**: ✅ 일치

### audit-4-2 — 6 filter (Actor / Action / Target kind / Target ID / Date range / Request ID), filters compose, URL 갱신

**매뉴얼**: 6 filter.
**시스템** (`api/v1/admin/audit.py:114-121`):
```python
actor_user_id: uuid.UUID | None,
target_table: AuditTargetTable | None,    # NOT target_kind
action: str | None,
from_: datetime | None,
to: datetime | None,
q: str | None,                            # free-text search
```
- Actor 는 `actor_user_id` (UUID 만, 매뉴얼 "이메일 / user ID / system" 셋 다 X).
- Action 은 free-text (매뉴얼 multi-select X).
- target_kind X → target_table.
- **target_id 별도 filter 부재** (q free-text 에 포함될 수 있음).
- Date range: from + to 만, 프리셋 (last hour / today / last 7 days) **부재**.
- **request_id filter 부재**.
- 4-5 filter 만 실제 노출 (매뉴얼 6개 약속).
**분류**: 📝 매뉴얼 오류 (filter 항목 + 필드 의미 모두 다름)

### audit-4-3 — 기본 컬럼 (ts / actor / action / target / ip), 행 클릭 → payload diff expand

**매뉴얼**: 5 컬럼 + drawer.
**시스템**: `features/admin/audit/` 컴포넌트가 컬럼 표시 + drawer/expand. 컬럼 명은 frontend 에서 `created_at` (매뉴얼 `ts`).
**분류**: 📝 매뉴얼 오류 (컬럼명 일부 다름)

### audit-5-1 — Export CSV — 100k cap, UTF-8 BOM

**매뉴얼**: 100k cap + UTF-8 BOM.
**시스템**:
- 100k cap: `services/admin_audit_service.py` 의 `AuditExportTooLarge` 으로 가드 (확인). ✅
- UTF-8 BOM: `grep -n "BOM\|utf-8-sig\|\\xef\\xbb\\xbf" apps/backend/services/admin_audit_service.py` → 0 매치. **BOM 미적용**. media_type 은 `text/csv; charset=utf-8` 만 헤더에 명시.
**분류**: 🐛 시스템 버그 (Low) — Excel 호환 깨짐. 또는 📝 매뉴얼 오류 — BOM 약속 삭제.

### audit-5-2 — API `GET /api/v1/admin/audit?from=…&to=…&page=…&size=…` + cursor `next`

**매뉴얼**: 쿼리 파라미터 + cursor pagination.
**시스템**:
- `from` / `to` ✅, `page` ✅, but `size` ✗ — 실제 param 은 `page_size` (`api/v1/admin/audit.py:121`).
- `next` cursor: 응답 schema `AuditLogListPage` 가 cursor 필드 보유 여부 확인 필요. 일반적인 page-based pagination (page_size + page) 으로 보임.
**분류**: 📝 매뉴얼 오류 (`size` → `page_size`)

### audit-7-3 — DELETE 시 immutability constraint 일시 disable → 자체가 audit row

**매뉴얼**: 자기-기록 패턴.
**시스템**: immutability constraint 자체가 부재 (audit-1-1 참조). 따라서 disable → re-enable 흐름도 부재.
**분류**: 📝 매뉴얼 오류 (audit-1-1 의 시스템 버그가 파급)

### audit-8-3 (Verify) — payload diff 정확, PII (email/password hash/API key) 마스킹

**매뉴얼**: mask_pii 적용.
**시스템**: `core/audit.py` 의 `_SENSITIVE_COLUMNS` + `mask_pii` helper 존재. 실제 audit listener 가 sensitive 컬럼을 `***` 로 교체 (api_key.py 모델의 docstring 도 `key_hash` 가 마스킹 됨을 명시). ✅
**분류**: ✅ 일치

### audit-9-2 — CSV truncated — 100k cap

**매뉴얼**: 가이드.
**시스템**: AuditExportTooLarge 가드 ✅
**분류**: ✅ 일치

---

## 5. admin-guide/backup-and-restore.md

### bkp-1-1 — 백업 구성 (postgres.sql.gz + workspace.tar.gz + manifest.json)

**매뉴얼**: 3 파일.
**시스템**: `scripts/backup.sh:54,62,66` 가 정확히 3 파일 작성. ✅
**분류**: ✅ 일치

### bkp-1-2 — `.env` / Traefik ACME state 미백업

**매뉴얼**: 가이드.
**시스템**: `scripts/backup.sh` 가 둘 다 백업 X. ✅ (정책 가이드)
**분류**: ✅ 일치

### bkp-2-1 — manual backup `bash scripts/backup.sh`

**매뉴얼**: CLI 흐름.
**시스템**: `scripts/backup.sh` 존재 + `--no-prune` 플래그 (line 29). ✅
**분류**: ✅ 일치

### bkp-2-2 — 7일 retention prune (`BACKUP_RETENTION_DAYS`) + `--no-prune`

**매뉴얼**: 7일 default + 옵션.
**시스템** (`scripts/backup.sh:92-95`):
```bash
retention=${BACKUP_RETENTION_DAYS:-7}
...
ok "pruned $removed backup(s) older than $retention days"
```
✅
**분류**: ✅ 일치

### bkp-3-1 — UI `/admin/backup` 사이드바 진입

**매뉴얼**: 신규 페이지.
**시스템**: `features/admin/backup/AdminBackupPage.tsx` + router 등재 + `AdminLayout.tsx` 사이드바 항목. ✅
**분류**: ✅ 일치

### bkp-3-2 — Trigger backup now → Celery 큐 row + status `running` + live progress bar

**매뉴얼**: 비동기 흐름.
**시스템**:
- `POST /v1/admin/backup` (api/v1/admin/backup.py:178) → `run_backup_task.delay()` ✅
- 본 환경에서는 worker restart loop 라 실제 task 실행은 차단 — Tier 2 보류.
**분류**: ⏭ 보류 (worker 가동 시 검증)

### bkp-3-5 — Celery Beat 일일 00:00 UTC default + `BACKUP_DAILY_ENABLED=false` 로 비활성

**매뉴얼**: env 토글 약속.
**시스템** (`tasks/celery_app.py:77-81`):
```python
"daily-auto-backup": {
    "task": "trustedoss.backup.run",
    "schedule": crontab(hour=0, minute=0),
    "kwargs": {"kind": "auto", "actor_user_id": None},
},
```
- 00:00 UTC ✅
- `BACKUP_DAILY_ENABLED` env 어디에도 없음 (`grep` → 0 매치). **무조건 활성**.
**분류**: 📝 매뉴얼 오류 (env 토글 미구현)

### bkp-3-6 — Upload + Restore — Choose file (max **10 GB**)

**매뉴얼**: 10 GB 캡.
**시스템** (`api/v1/admin/backup.py:83`):
```python
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
```
+ `Content-Length` 헤더 검사 + 스트리밍 중 cap 검사. ✅
**분류**: ✅ 일치

### bkp-3-7 — typing-gate `restore` 정확 입력 (case-sensitive) + Restore 비활성 → 활성

**매뉴얼**: 정확한 lowercase `restore`.
**시스템** (`features/admin/backup/AdminBackupPage.tsx:62`):
```ts
const RESTORE_CONFIRM_TOKEN = "restore";
...
restoreFile != null && restoreConfirmInput === RESTORE_CONFIRM_TOKEN
```
✅
**분류**: ✅ 일치

### bkp-3-8 — frontend `X-Confirm-Restore: yes` 헤더 + super_admin role + 둘 다 검증 (412 if missing)

**매뉴얼**: HTTP **412 Precondition Failed** 가 missing 시.
**시스템** (`api/v1/admin/backup.py:335-345`):
```python
if confirm != "yes":
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,   # ← 400, NOT 412
        title="Restore Confirmation Required",
        ...
        type_=_TYPE_CONFIRM_REQUIRED,
    )
```
- header 검증 ✅ (X-Confirm-Restore: yes 존재).
- super_admin 가드 ✅ (`Depends(require_super_admin_or_404())`).
- status 코드 **400** (매뉴얼 412 약속 다름).
**분류**: 📝 매뉴얼 오류 또는 🐛 시스템 버그 (HTTP semantic 차이). RFC 7807 의 412 Precondition Failed 가 더 정확한 semantic — 시스템을 412 로 변경하는 것이 권고.
**Phase 4 권고**: 시스템을 412 로 fix (시스템 버그 — Low severity). 또는 매뉴얼을 400 으로 수정.

### bkp-3-9 — 진행 stream + 완료 시 row succeeded + JWT revoke (user table 교체)

**매뉴얼**: restore 후 강제 재인증.
**시스템**: `tasks/backup.py` 의 restore_backup_task 검증 필요. user 테이블 교체로 인한 JWT-now-orphan 효과는 사실상 자동 (refresh 시 lookup 실패). 매뉴얼 표현 ✅
**분류**: ✅ 일치 (의미적으로)

### bkp-3-3 (verify hidden) — decompression bomb cap (PR #36 H3)

**매뉴얼 부재** (matrix bkp-3-6 의 비고에 등장).
**시스템** (`api/v1/admin/backup.py:87-88`):
```python
_MAX_MEMBER_BYTES = 5 * 1024 * 1024 * 1024      # 5 GiB per member
_MAX_EXTRACTED_BYTES = 50 * 1024 * 1024 * 1024  # 50 GiB cumulative
```
+ tarball 멤버 순회 시 size 검사 + `_DecompressionBombError` → 413 + RFC 7807 `backup-decompression-bomb`. ✅
**분류**: ✅ 일치 (가드 정확. 단, 매뉴얼 본문에는 미언급 → Phase 4 fix 권고: 매뉴얼에 추가)

### bkp-6-2 — restore 5 단계 (backend/frontend/worker/beat stop → postgres restore --clean → workspace restore (rm + extract) → restart → alembic head verify)

**매뉴얼**: 5 단계.
**시스템** (`scripts/restore.sh`):
- backend/frontend/worker/beat stop ✅
- postgres restore `pg_dump --clean --if-exists` (line 5) ✅
- workspace restore `rm -rf` + `tar -xzf` (line 78-79) ✅
- restart ✅
- alembic head verify (line 96-111) ✅
**분류**: ✅ 일치

### bkp-11-3 (Verify) — `gunzip -t postgres.sql.gz` 성공

**매뉴얼**: 무결성.
**시스템**: 가이드 (operator-side check). ✅
**분류**: ✅ 일치 (가이드)

### bkp-12-2 (Trbl) — restore aborts at workspace step

**매뉴얼**: 진단 가이드.
**시스템**: 가이드 ✅
**분류**: ✅ 일치 (B — 호스트 직접)

---

## 6. admin-guide/api-keys.md

### apik-3-1 — key shape `tos_<8>_<32>` + prefix public + secret bcrypt hash + 일회성 reveal

**매뉴얼**: 정확한 shape.
**시스템** (`services/api_key_service.py:9, 124, 134`): 정확히 `tos_<8 hex>_<32 url-safe>`. bcrypt hash 저장 (`models/api_key.py:112`). 일회성 reveal 은 `POST /v1/api-keys` 응답에만 plaintext 노출.
**분류**: ✅ 일치

### apik-3-2 — constant-time prefix lookup + `bcrypt.checkpw`

**매뉴얼**: timing attack 방어.
**시스템**: `services/api_key_service.py:588` (_DUMMY_BCRYPT_HASH for constant-time fallback) + bcrypt.checkpw 사용. ✅
**분류**: ✅ 일치

### apik-4-1 — scope 모델 (owning team + effective role + allowed actions + expiry)

**매뉴얼**:
> Each key carries:
> - **Owning team**, **Effective role** (developer / team_admin), **Allowed actions** (`scan:trigger`, `scan:read`, `report:download`, `webhook:receive`, `*`), **Expiry**.

**시스템** (`models/api_key.py:118-149`):
```python
scope: Mapped[str] = mapped_column(String(16), nullable=False)  # 'org' | 'team' | 'project'
team_id, project_id    # scope-dependent
created_by_user_id, created_at, last_used_at, revoked_at
```
- 실제 scope 는 **resource hierarchy** (org / team / project), not "developer / team_admin / actions list".
- **`allowed_actions` 컬럼 부재** — 5종 actions taxonomy 모두 fabrication.
- **`expires_at` 컬럼 부재** — expiry 는 `revoked_at` (manual revoke) 으로만. 30/90/180/365 preset 등 없음.
- **`effective_role` 컬럼 부재** — 키의 권한은 issuer 의 role 을 따름 (super_admin 발급 = org-wide, team_admin 발급 = team-wide).
**분류**: 📝 매뉴얼 오류 (scope 모델 fabricated. 실제는 resource scope 만)
**Phase 4 fix 권고**: section "Scope model" 전체 다시 작성. 실제 contract 는 `services/api_key_service.py` 의 `27-30` 주석 참조.

### apik-5-1 — team_admin: Project Settings → CI/CD → API keys → New API key

**매뉴얼**: per-project Settings 경로.
**시스템**: 실제 entry 는 `/integrations` 페이지 (top-level, project Settings X). frontend 코드의 `IntegrationsPage` 가 단일 entry. Project Settings 의 별도 CI/CD tab UI 부재.
**분류**: 📝 매뉴얼 오류 (entry path 잘못)

### apik-5-2 — 일회성 modal 노출, copy 후 close. prefix 만 잔존

**매뉴얼**: 보안 contract.
**시스템**: `IntegrationsPage` 의 create flow 에서 plaintext 한 번만 노출 (`integrations.spec.ts:83` 가 closeCreateDialog 가드). ✅
**분류**: ✅ 일치

### apik-6-1 — `Authorization: ApiKey <key>` 또는 `Bearer <key>`

**매뉴얼**: 두 scheme 모두.
**시스템**: `services/api_key_service.py` 의 인증 dependency 가 두 scheme 처리 확인 필요.
**분류**: ⏭ 보류 (시간 — 단위 grep 부족)

### apik-7-3 — revoke 후 ~5s auth cache TTL

**매뉴얼**: 캐시 TTL.
**시스템**: `grep -rn "TTL\|ttl\|cache_ttl" apps/backend/services/api_key_service.py` 로 확인 필요.
**분류**: ⏭ 보류

### apik-9-1 — listing UI (label / prefix / team / role / actions / expiry / last-used ts / IP). secret 복구 X

**매뉴얼**: 8 컬럼.
**시스템**:
- 모델에 expires_at / actions / IP 부재 (위 apik-4-1 참조).
- `last_used_at` 컬럼만 존재; **`last_used_ip` 부재**.
- frontend listing 컬럼은 schema 가 허용하는 것만 (label / prefix / scope / created_at / last_used_at / revoked_at).
**분류**: 📝 매뉴얼 오류 (UI 컬럼 8개 약속 중 4-5개 부재)

### apik-10-1 — audit `api_key.create / api_key.revoke / api_key.use` (actor_kind=api_key)

**매뉴얼**: 3 audit event + actor_kind 필드.
**시스템**:
- audit row 의 action 명은 `core/audit.py` listener 가 ORM event 기반으로 생성 → 실제 action 명은 `api_key.create` 형태가 아닐 수 있음 (검증 필요, Tier 2 차단).
- **`api_key.use` event 부재** (`grep -rn "api_key\.use\|action=\"api_key" apps/backend` → 0 매치). per-request audit 미구현.
- **`actor_kind` 필드 부재** (audit-2-1 참조). filter `actor_kind=api_key` 자체가 작동 X.
**분류**: 📝 매뉴얼 오류 (3 event 중 use 부재 + actor_kind 부재)

### apik-13-2 (Trbl) — "prefix exists secret mismatch" — 5 misses/60s → super_admin Slack alert

**매뉴얼**: brute-force 알림.
**시스템**: `grep -rn "5 misses\|brute.*force\|api_key.*alert" apps/backend` → 0 매치. **brute-force 감지 + 알림 미구현**.
**분류**: 📝 매뉴얼 오류 (보안 알림 약속 미구현. 매우 중요한 회귀 가드 영역)

### apik-11-1 — webhook secrets vs API keys

**매뉴얼**: 인바운드 vs 아웃바운드 구분 가이드.
**시스템**: 정책 가이드 — frontend `IntegrationsPage` 에 두 tab 존재 ✅
**분류**: ⏭ 보류 (C — 시각/Copy)

---

## 발견된 시스템 버그 요약 (Phase 4 입력)

| ID | Severity | 증상 | 영향 page | 재현 |
|----|----------|------|-----------|------|
| sys-bug-u&t-1 | Low | last super_admin DB-level CHECK constraint 부재 — 직접 SQL 로 demote 가능 | users-and-teams (u&t-9-3) | `psql -c "UPDATE users SET is_superuser=false WHERE id=<last>"` 가 차단되지 않음 |
| sys-bug-dt-1 | Low | breaker stuck OPEN 시 reset endpoint 부재 — 운영자 우회 수단 X (redis 키 직접 삭제만) | dt-connector (dt-8-2) | breaker 가 OPEN 상태로 stuck 시 운영자 dashboard 또는 CLI 에서 reset 불가 |
| sys-bug-audit-1 | Low | audit_logs 테이블에 immutability constraint (UPDATE/DELETE 차단) 부재 — append-only 약속 미강제 | audit-log (audit-1-1, audit-7-3) | `UPDATE audit_logs SET action='...' WHERE id=...` 차단 X |
| sys-bug-bkp-1 | Low | restore 시 missing X-Confirm-Restore 헤더가 **400** 반환 (RFC 7807 contract 상 412 Precondition Failed 가 더 정확) | backup-and-restore (bkp-3-8) | `curl -X POST .../v1/admin/backup/restore -F file=@... ` (헤더 미포함) → 400 |
| sys-bug-audit-2 | Low | CSV export 가 UTF-8 BOM 미포함 — Excel 비-ASCII 깨짐 | audit-log (audit-5-1) | export csv → Excel 에서 한글 깨짐 |

(추가 환경 버그 `bug-env-1` — Postgres 가 Docker disk 풀로 무한 크래시. dev compose 운영 가이드 추가 권고.)

---

## 발견된 매뉴얼 오류 요약 (Phase 4 입력)

| ID | 페이지 | 매뉴얼 주장 | 실제 동작 | EN/KO 모두 수정 |
|----|--------|-------------|-----------|--------------------|
| doc-u&t-1 | users-and-teams.md §4.1-4.2 | "Invite user → 24h email link → password set" | invite endpoint / UI 부재. self-registration 만 | ✅ |
| doc-u&t-2 | §7 | "Memberships → Change role" multi-team 변경 | 글로벌 role dropdown 1개만 (team-cross 변경 불가) | ✅ |
| doc-u&t-3 | §9 | last-super-admin status **409** + title `"Cannot demote the last super_admin"` + type URI | 실제 422 + `"Last Super Admin Protected"` + about:blank + extension `last_super_admin_protected=true` | ✅ |
| doc-u&t-4 | §11 | typed-email confirmation modal로 delete | delete-user endpoint / UI 모두 부재 | ✅ |
| doc-u&t-5 | §13 | team archive (super_admin) 4 효과 | archive 컬럼 / endpoint / UI 부재 | ✅ |
| doc-u&t-6 | §14 verify | invite 후 status `pending` → `active` | User 모델에 status 컬럼 없음 (`is_active` boolean 만) | ✅ |
| doc-dt-1 | dt-connector.md §3.1-down 자동 복구 | "down 시 docker restart dt 1회 + 90s 대기" | 자동 docker restart 미구현 | ✅ |
| doc-dt-2 | §3.2 / §6 | endpoint 명 `GET /admin/dt/state` / `POST /admin/dt/probe` | 실제는 `/dt/status` / `/dt/health-check` | ✅ |
| doc-dt-3 | trbl §8.2-8.3 | `/admin/dt/breaker/reset`, `/admin/dt/resync` 수동 endpoint | 둘 다 부재 (breaker reset endpoint 자체 없음) | ✅ |
| doc-disk-1 | disk-and-health.md §1.1 | "8 컴포넌트 (backend/postgres/redis/worker/beat/frontend/traefik/dt)" | 실제 7 컴포넌트 (postgres/redis/celery/dt/disk/active_scans/last_24h_errors). backend/worker/beat/frontend/traefik 모두 부재 | ✅ |
| doc-disk-2 | §1.2 | state 값 `healthy / degraded / down` | 실제 `ok / degraded / down` (i18n 라벨로 healthy 표시 가능 — 그러나 contract 차이) | ✅ |
| doc-disk-3 | §1.3 | "5s WebSocket auto-refresh" | react-query polling (WebSocket 아님) | ✅ |
| doc-disk-4 | §2.1 | 8 probe 표 | 5 probe 만 (backend/worker/beat/frontend/traefik probe 부재) | ✅ |
| doc-disk-5 | §2.2 | "1 miss → degraded, 3 misses → down" state machine | DT만 fail-count 카운터. 다른 component 는 single-shot threshold 기반 | ✅ |
| doc-disk-6 | §3.1 | "Workspace + PostgreSQL **2 gauge**" | 실제 4 카드 (workspace / dt_volume / postgres / redis) | ✅ |
| doc-disk-7 | §3.2-3.3 | warn 70% / hard 90% + env `DISK_WARN_LIMIT_PCT` `DISK_HARD_LIMIT_PCT` | 기본값 warn=80 / crit=90 + env 명 `DISK_THRESHOLD_WARNING_PCT` `DISK_THRESHOLD_CRITICAL_PCT`. `DISK_HARD_LIMIT_PCT` 는 별개로 scan 차단용 (default 95) | ✅ |
| doc-disk-8 | §3.4 | disk-pressure 503 + `type=https://trustedoss.io/problems/disk-pressure` + title `"Scans temporarily disabled — disk usage above hard limit"` | 503 + about:blank + title `"Workspace Disk Full"` | ✅ |
| doc-audit-1 | audit-log.md §1 | "CHECK constraint prevents updates and deletes" | constraint 자체 부재 (sys-bug-audit-1) | ✅ |
| doc-audit-2 | §2 schema 표 | 11 필드 (`ts / actor_kind / target_kind / payload`) | 실제 12 필드 (created_at / target_table / diff). `actor_kind` 부재. team_id 누락 | ✅ |
| doc-audit-3 | §3.1 filter | 6 filter (Actor 이메일/system, Action multi-select, Target kind, Target ID, Date range presets, Request ID) | 4-5 filter (actor_user_id UUID, target_table enum, action free-text, from/to, q free-text). target_id / request_id / preset date / multi-select 모두 부재 | ✅ |
| doc-audit-4 | §3.1 컬럼 | `ts` 컬럼 | 실제 `created_at` | ✅ |
| doc-audit-5 | §4 export | UTF-8 BOM | BOM 미포함 (sys-bug-audit-2) | ✅ |
| doc-audit-6 | §4 API | param `size` | 실제 `page_size` | ✅ |
| doc-bkp-1 | backup-and-restore.md §3 | `BACKUP_DAILY_ENABLED=false` 로 schedule 비활성 | env 미구현. schedule 무조건 활성 | ✅ |
| doc-bkp-2 | §3.UI | 412 Precondition Failed (X-Confirm-Restore missing) | 실제 400 (sys-bug-bkp-1) | ✅ |
| doc-apik-1 | api-keys.md §scope | "owning team + effective role (developer/team_admin) + allowed actions (5종 list) + expiry presets" | scope = 'org' | 'team' | 'project' (resource hierarchy). actions taxonomy / effective_role / expiry 모두 부재 | ✅ |
| doc-apik-2 | §issue | "Project Settings → CI/CD → API keys" path | 실제는 `/integrations` 페이지 단일 entry | ✅ |
| doc-apik-3 | §listing | "label / prefix / team / role / actions / expiry / last-used ts / IP" 8 컬럼 | last_used_ip / actions / role / expiry 컬럼 모델에 없음 | ✅ |
| doc-apik-4 | §audit | `api_key.use` event 매 request | per-request audit 미구현 | ✅ |
| doc-apik-5 | §trbl | "5 misses/60s → super_admin Slack alert" | brute-force 감지 / 알림 미구현 | ✅ |

---

## ⏭ 보류 항목 (Phase 5 자동화 또는 운영자 직접 검증)

| ID | 단계 | 사유 |
|----|------|------|
| ⏭-1 | bkp-3-2 (Trigger backup now → live progress) | celery-worker restart loop 로 동적 검증 차단. PR #29 의 e2e spec (admin_backup.spec.ts) 가 미존재 → Phase 5 권고 |
| ⏭-2 | disk-5-1 (disk pressure notification SMTP/Slack/Teams) | B 분류. 외부 채널 — fixture inbox (maildev) 또는 사람이 직접 |
| ⏭-3 | apik-6-1 (`ApiKey` 또는 `Bearer` 두 scheme) | grep 으로 부분 확인했으나 단위 테스트로 명시 검증 권고 |
| ⏭-4 | apik-7-3 (revoke 후 5s 캐시 TTL) | 캐시 만료 시간 정확 검증 — Phase 5 단위 테스트 |
| ⏭-5 | dt-3-4-2 (DT_ORPHAN_AUTODELETE=false 시 confirm) | env 분기 검증 — 다음 세션 |

---

## Phase 4 입력 요약 (PR 분리 권고)

본 walkthrough 산출물을 다음 4 PR 로 분리 권고:

1. **`chore/admin-guide-drift-fixes`** (가장 큰 doc-fix PR — 약 27 매뉴얼 수정)
   - users-and-teams 6 + dt-connector 3 + disk-and-health 6 + audit-log 6 + backup-and-restore 2 + api-keys 5 + EN/KO 동시 수정
   - section 단위로 commit 분리 권고

2. **`fix/audit-immutability`** (sys-bug-audit-1)
   - alembic migration 으로 audit_logs PG trigger 추가 (BEFORE UPDATE OR DELETE → RAISE EXCEPTION)
   - 단위 테스트 추가 — `test_audit_immutability.py`

3. **`fix/backup-restore-confirm-412`** (sys-bug-bkp-1)
   - `api/v1/admin/backup.py:337` status 400 → 412
   - frontend 영향 없음 (헤더는 항상 yes 보냄)
   - 기존 e2e 회귀 가드 부재 → Phase 5 의 admin_backup.spec.ts 신규 항목으로 흡수

4. **`fix/audit-csv-utf8-bom`** (sys-bug-audit-2)
   - `services/admin_audit_service.py` 의 stream_audit_csv 가 첫 청크 prefix `\xef\xbb\xbf` (UTF-8 BOM)
   - 매뉴얼 audit-5-1 약속 정합

(sys-bug-u&t-1 last-super-admin DB CHECK + sys-bug-dt-1 breaker reset endpoint 는 Medium-priority backlog 로 등재 — 즉시 fix 보다 매뉴얼 수정이 더 빠름)

---

## 다음 세션 (Phase 4) 시작점

`docs/sessions/_next-session-prompt-manual-walkthrough.md` §4 — Triage + 매뉴얼 fix + 시스템 버그 issue. 본 walkthrough 의 두 표 (시스템 버그 5개 + 매뉴얼 오류 27개) 를 입력으로 PR 분리.
