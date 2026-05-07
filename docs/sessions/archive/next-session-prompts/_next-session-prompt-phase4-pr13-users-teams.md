Phase 4 PR #13 — 관리자 패널 진입 (Admin 라우트 가드 + Users 관리 + Teams 관리).

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <Phase 3 + chore PR #5/#6/#7 누적 머지 결과 SHA, 직전 docs PR squash hash>. 누적 머지: PR #1~#12 + chore CI fix 4건 + chore PR #1~#7. **Phase 0~3 완료**. 본 세션은 Phase 4 (관리자 패널) 의 첫 PR.

## 0. 시작 전 — 라벨링 정정 (반드시 먼저 처리)

**v2-execution-plan §3.5 / §3.7 이 단일 진실**이다. 이전 세션 핸드오프(`_next-session-prompt-phase4-pr14.md`)와 chore PR #5 핸드오프 §6 옵션 A 가 **알림을 "Phase 4" 로 잘못 라벨링했다**. 정확한 매핑:

| Phase | 정확한 작업 | 잘못 사용된 라벨 |
|-------|-------------|------------------|
| **Phase 4 — 관리자 패널** (§3.5) | Users / Teams / DT / Scans / Disk / Audit / Health 7 화면 + 컴포넌트 승인 워크플로우. PR #13 / #14 / #15. | `_next-session-prompt-phase4-pr14.md` 가 알림으로 오인 |
| **Phase 5 — CI/CD 연동** (§3.6) | API Key + Webhook + 빌드 차단 게이트 + Action 템플릿. PR #16 / #17. | — |
| **Phase 6 — 다국어 + 알림 + 안정성** (§3.7) | 한국어 번역 + 이메일/Slack/Teams 알림 + 백업/복원. PR #18 / #19. | 알림은 사실 여기다. |
| Phase 7 — 배포 + 문서 (§3.8) | 설치 스크립트 + 프로덕션 compose + Docusaurus + 랜딩. PR #20~22. | — |
| Phase 8 — 데모 SaaS + GA (§3.9) | OAuth + 보안/성능 hardening + 릴리스. PR #23~25. | — |

**세션 첫 작업**: 잘못된 prompt 파일을 archive 로 이동.
```
mkdir -p docs/sessions/archive/next-session-prompts
git mv docs/sessions/_next-session-prompt-phase4-pr14.md docs/sessions/archive/next-session-prompts/_next-session-prompt-phase4-pr14-MISLABELED-as-notification.md
git mv docs/sessions/_next-session-prompt-phase4-pr13-users-teams.md docs/sessions/archive/next-session-prompts/    # 본 prompt 자체 — 세션 종료 시
```
첫 commit 메시지: `chore(docs): archive mislabeled phase 4 notification prompt`. 본문: v2-execution-plan §3.5 가 단일 진실 / 알림은 Phase 6 PR #18 / Phase 4 = 관리자 패널.

## 1. 이번 세션 = Phase 4 PR #13 — Users/Teams 관리

`docs/v2-execution-plan.md` §3.5 의 4.1 + 4.2 + 4.3 을 묶어서 PR #13 으로. 4.4~4.10 은 PR #14 / #15.

| § | 작업 | 산출물 |
|---|------|--------|
| 4.1 | Admin 라우트 가드 + 사이드바 | 백엔드 미들웨어 + 프론트 `/admin/*` 가드 + admin layout |
| 4.2 | Users 관리 (역할 변경 / 비활성화 / 비밀번호 리셋) | 백엔드 `/api/v1/admin/users/*` + 프론트 `/admin/users` |
| 4.3 | Teams 관리 (생성 / 삭제 / 멤버) | 백엔드 `/api/v1/admin/teams/*` + 프론트 `/admin/teams` |

플로우: Super Admin 만 `/admin/*` 접근. 일반 사용자 / Team Admin / Developer 는 404 (existence-hide). E2E 가 super_admin / team_admin / developer 3 역할의 차등 접근 핀.

## 2. 직전 핸드오프 (반드시 시작 시 읽기)

- `docs/sessions/2026-05-XX-chore-pr7-maven-url-uat-revalidation.md` (또는 직전 세션 핸드오프) — **§5 의 adversarial input 결함 + UAT 와 단위 테스트의 functional gap 교훈** 반드시 흡수. 본 PR 의 untrusted input 표면 (Users 관리의 비밀번호 리셋 토큰, Teams 의 외부 식별자, role 변경 payload) 동일 위험.
- `docs/sessions/2026-05-XX-chore-pr6-cdxgen-ort-env-scrub.md` — chore PR #6 핸드오프 (subprocess env scrub). Phase 4 와 직접 무관하나 패턴 참조.
- `docs/sessions/2026-05-07-chore-pr5-security-license-fetcher.md` — chore PR #5 핸드오프. assert_team_access 마이그레이션 패턴 참조 (4.1 의 admin 가드 도 동일 헬퍼 활용).
- `docs/sessions/2026-05-07-phase3-pr13-obligations.md` — Phase 3 종결 핸드오프 (PR # 의미 혼동 주의 — 그쪽의 PR #13 은 이미 머지된 obligations PR, 본 PR #13 은 plan §3.5 의 admin Users/Teams).
- **`docs/v2-execution-plan.md` §3.5** — Phase 4 단일 진실. 본 PR 의 정확한 작업 범위 + DoD.
- `CLAUDE.md` "조직/팀/권한 모델" + "주요 기능 / 관리자" 절 — RBAC 3단계 정의 + admin 화면 7개 목록.
- `apps/backend/core/authz.py` — `assert_team_access` 헬퍼 (이미 chore PR #3 / #5 에서 도입). 본 PR 에서 admin-only 변종 (`assert_super_admin`) 추가 검토.

## 3. 시작 시 검증 (반드시)

```
docker-compose -f docker-compose.dev.yml ps               # 6/6 healthy (celery-beat 포함)
docker-compose -f docker-compose.dev.yml -f docker-compose.dt.yml ps  # +dtrack-api healthy
gh run list --limit 3                                      # main 최신 success
git status                                                 # working tree 검증
```

main 의 working tree 잔여:
- `docs/sessions/_next-session-prompt-phase4-pr14.md` (잘못 라벨링된 알림 prompt) — §0 절차로 archive.
- `docs/sessions/_next-session-prompt-phase4-pr13-users-teams.md` (본 prompt) — 세션 종료 시 archive.
- `.claude/scheduled_tasks.lock` — 무시.
- `docs/review-binaryanalysis-ng.md` — 사용자 작업 중 doc, 무시.

브랜치: `feature/phase4-pr13-admin-users-teams` 신규 생성.

## 4. 작업 절차

### 4.1 Admin 라우트 가드 + 사이드바

#### 백엔드

신규 모듈 `apps/backend/api/v1/admin/__init__.py` (router 묶음):
```python
from fastapi import APIRouter
from . import users, teams  # PR #14 에서 dt / scans / disk / audit / health 추가
admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("super_admin"))])
admin_router.include_router(users.router)
admin_router.include_router(teams.router)
```

`apps/backend/api/v1/__init__.py` (또는 `main.py` 의 라우팅 등록 위치) 에서 `app.include_router(admin_router, prefix="/api/v1")`.

`require_role("super_admin")` 는 이미 Phase 1 PR #5 에서 도입된 헬퍼. 비-super_admin 의 모든 admin endpoint 는 **404** 반환 (403 아님 — existence-hide). 만약 현재 헬퍼가 403 을 던진다면 admin-only 분기 (`return 404` mode) 추가.

신규 모듈 `apps/backend/core/authz.py` 에 `assert_super_admin(actor, *, log, resource, resource_id)` 헬퍼 추가 (선택 — `require_role` 이 이미 충분하면 skip). assert_team_access 패턴과 동일 (warning log + raise NotFound).

신규 audit 이벤트 정의 (`core/audit.py` 또는 audit_log 테이블):
- `admin.user.role_changed` (target_user_id, before_role, after_role)
- `admin.user.deactivated` (target_user_id)
- `admin.user.password_reset_initiated` (target_user_id, reset_token_id)
- `admin.team.created` (team_id, name)
- `admin.team.deleted` (team_id)
- `admin.team.member_added` (team_id, target_user_id)
- `admin.team.member_removed` (team_id, target_user_id)

모든 admin 변경 작업 = audit 1줄 자동 기록 (CLAUDE.md "감사 로그 (모든 쓰기 작업 자동 기록)" 핵심 규칙).

#### 프론트

신규 layout `apps/frontend/src/features/admin/AdminLayout.tsx`:
- 사이드바 좌측 (CLAUDE.md "고정 사이드바 (224px)") — Users / Teams 두 항목 (PR #14 에서 DT / Scans / Disk / Audit / Health 추가).
- 상단 헤더 동일 (48px).
- `useCurrentUser()` 훅에서 `is_superuser || role === "super_admin"` 아니면 `<Navigate to="/404" />` 또는 `<NotFound />` 페이지.

라우터 `apps/frontend/src/App.tsx` (또는 router 정의 위치):
```tsx
<Route path="/admin" element={<AdminLayout />}>
  <Route path="users" element={<AdminUsersPage />} />
  <Route path="teams" element={<AdminTeamsPage />} />
  // PR #14 에서 dt / scans / disk / audit / health 추가
</Route>
```

기존 사이드바 (앱 전체) 의 하단에 "관리자" 그룹 추가 — Super Admin 만 표시. i18n 키 `nav.admin.users` / `nav.admin.teams` 만 본 PR 에서 추가 (EN/KO 동시).

### 4.2 Users 관리

#### 백엔드 `apps/backend/api/v1/admin/users.py`

| Method | Path | 설명 |
|--------|------|------|
| GET | `/admin/users` | 목록 (페이지네이션, role/active 필터, email 검색) |
| GET | `/admin/users/{user_id}` | 상세 (last_login, scan count, team memberships) |
| PATCH | `/admin/users/{user_id}/role` | 역할 변경 (super_admin / team_admin / developer) |
| PATCH | `/admin/users/{user_id}/deactivate` | 비활성화 (`is_active = false`, JWT 무효화) |
| POST | `/admin/users/{user_id}/password-reset` | 비밀번호 리셋 토큰 발행 + 사용자에게 이메일 발송 큐 (Phase 6 알림 시스템 미존재 → 본 PR 은 토큰만 생성, 이메일 발송은 stub: log + 토큰을 응답에 포함하지 않고 audit 만 기록) |

**중요한 안전장치**:
- 마지막 super_admin 의 역할 변경 / 비활성화 시 차단 (`HTTP 422 last_super_admin_protected`).
- 자기 자신의 역할 변경 / 비활성화 차단 (자기를 잠그면 복구 불가).
- 비밀번호 리셋 토큰 = `secrets.token_urlsafe(32)`, 1 시간 만료, bcrypt hash 로 DB 저장 (평문 X).

서비스: `apps/backend/services/admin_user_service.py` 신규.

#### 프론트 `apps/frontend/src/features/admin/users/`

- `AdminUsersPage.tsx` — 테이블 (40px compact, CLAUDE.md "테이블 밀도"), 필터 인라인, 행 클릭 → 드로어 (CLAUDE.md "드로어 (오른쪽 슬라이드)").
- `AdminUserDrawer.tsx` — 사용자 상세 + 액션 버튼 (역할 변경 / 비활성화 / 비밀번호 리셋). 확인 다이얼로그 필수.
- `useAdminUsers()` / `useAdminUser(id)` / `useUpdateUserRole()` / `useDeactivateUser()` / `useResetUserPassword()` — TanStack Query 훅.

### 4.3 Teams 관리

#### 백엔드 `apps/backend/api/v1/admin/teams.py`

| Method | Path | 설명 |
|--------|------|------|
| GET | `/admin/teams` | 목록 (페이지네이션, name 검색) |
| GET | `/admin/teams/{team_id}` | 상세 (멤버 목록, project count) |
| POST | `/admin/teams` | 생성 (name unique) |
| PATCH | `/admin/teams/{team_id}` | name 변경 |
| DELETE | `/admin/teams/{team_id}` | 삭제 (CASCADE: 멤버십, projects 는 archive) |
| POST | `/admin/teams/{team_id}/members` | 멤버 추가 (`{user_id, role: team_admin|developer}`) |
| DELETE | `/admin/teams/{team_id}/members/{user_id}` | 멤버 제거 |

**안전장치**:
- 마지막 Team Admin 제거 시 차단 (§3.5 4.3 의 DoD 명시: "마지막 Team Admin 제거 시 차단").
- Team 삭제 시 해당 팀의 active scan 이 있으면 차단 (또는 강제 옵션 + audit 명시).
- Team 삭제 시 projects 는 default team 으로 이전 (또는 archive). 정책 결정 필요 — **권고: archive (project.archived_at 채우기), 새 default team 생성 안 함**. Super Admin 이 수동 재배치.

서비스: `apps/backend/services/admin_team_service.py` 신규.

#### 프론트 `apps/frontend/src/features/admin/teams/`

- `AdminTeamsPage.tsx` — 테이블, 필터, 새 팀 생성 버튼.
- `AdminTeamDrawer.tsx` — 팀 상세 + 멤버 관리 + 삭제 버튼 (확인 다이얼로그).
- `useAdminTeams()` / `useAdminTeam(id)` / `useCreateTeam()` / `useDeleteTeam()` / `useTeamMembers()` / `useAddTeamMember()` / `useRemoveTeamMember()`.

## 5. RFC 7807 Problem Details + 에러 응답 규약

CLAUDE.md "에러 응답 규약 (RFC 7807)" 그대로:
- 모든 4xx/5xx 응답은 `application/problem+json`.
- 도메인 확장 필드:
  - `last_super_admin_protected` (4xx)
  - `cannot_modify_self` (4xx)
  - `last_team_admin_protected` (4xx)
  - `team_has_active_scans` (4xx)
- OpenAPI 에 모델 등록.

기존 exception_handlers (chore PR #3) 패턴 따라 구현.

## 6. 단위 + 통합 + E2E 테스트

### 6.1 단위 (pytest)

`tests/unit/services/test_admin_user_service.py` / `test_admin_team_service.py`:
- happy path: 모든 endpoint 의 정상 흐름.
- 안전장치: 마지막 super_admin / 자기 자신 / 마지막 team_admin / active scan 보유 팀 삭제 — 모두 4xx + Problem Details.
- 비밀번호 리셋 토큰 hash 저장 + 평문 미저장 + 1시간 만료 + 사용 후 invalidate.
- audit 이벤트 1줄 자동 기록 (mock log 호출 검증).
- adversarial input parametrize (memory `feedback_adversarial_input_parametrize.md`):
  - email: oversized (10KB), CRLF injection, javascript:, null bytes, unicode normalization 오버
  - role: 미정의 값, integer, list, None
  - team name: SQL keyword, oversized, unicode RTL override

`tests/unit/test_authz_admin.py`:
- `require_role("super_admin")` 가 비-super_admin 에 404 (existence-hide).
- 자기 자신 / target_user_id 가 super_admin 일 때의 분기.

### 6.2 통합 (pytest + 실 PostgreSQL)

`tests/integration/admin/test_admin_users_api.py` / `test_admin_teams_api.py`:
- 모든 endpoint 의 IDOR / role 강제 (developer / team_admin / super_admin / unauthenticated 4 시나리오).
- audit log 가 실제 DB 에 기록되는지.
- 비밀번호 리셋 토큰 한 번 사용 후 재사용 차단.
- Team 삭제 후 멤버십 / 프로젝트 archive 회귀.

### 6.3 E2E (Playwright)

`apps/frontend/tests/e2e/admin_users_teams.spec.ts`:
- 시나리오 1 — Super Admin 이 /admin/users 진입 → 사용자 역할 변경 → 변경 후 사용자 로그인 시 새 권한 적용.
- 시나리오 2 — Team Admin 이 /admin/* 접근 시 404.
- 시나리오 3 — Super Admin 이 /admin/teams 에서 새 팀 생성 → 멤버 추가 → 멤버 제거.
- 시나리오 4 — 마지막 super_admin 의 역할 변경 시도 → 422 + 친화 에러 메시지.

`apps/frontend/tests/_harness/AdminUsersHarness.ts` / `AdminTeamsHarness.ts` 신규 — 도메인 verb (changeRoleTo, deactivate, addMember 등). PortalPage 에 admin 진입 verb 추가.

## 7. i18n (EN / KO 동시)

`apps/frontend/src/locales/{en,ko}/admin.json` 신규:
- nav.admin.users / nav.admin.teams
- admin.users.* (페이지 제목, 컬럼, 액션 버튼, 확인 다이얼로그, 에러 메시지)
- admin.teams.*
- admin.errors.last_super_admin_protected / cannot_modify_self / last_team_admin_protected / team_has_active_scans

i18n-specialist 라우팅. 한 번에 두 언어 동시.

## 8. 핵심 라우팅

- **db-designer** (선택): 본 PR 은 schema 변경 없을 가능성 높음 (User / Team / Membership 모델은 Phase 1 PR #5 에서 이미 존재). 비밀번호 리셋 토큰 테이블 (`password_reset_tokens`) 이 미존재면 신규 + Alembic forward-only migration 1건. **시작 시 `apps/backend/models/auth.py` 확인 후 결정**.
- **backend-developer** (필수): 4.1 admin router + require_role 보강 + 4.2 Users service/API + 4.3 Teams service/API + Problem Details 응답 + audit 이벤트.
- **frontend-dev** (필수): 4.1 AdminLayout + 라우터 + 사이드바 + 4.2 AdminUsersPage + Drawer + 훅 + 4.3 AdminTeamsPage + Drawer + 훅.
- **i18n-specialist** (필수): 7. EN/KO admin namespace.
- **test-writer** (필수): 6.1 + 6.2 + 6.3 단위 + 통합 + E2E + 하네스.
- **security-reviewer** (필수): Producer-Reviewer 1 라운드 — RBAC / IDOR / existence-hide / 비밀번호 리셋 토큰 안전성 / audit 누락 / adversarial input.

## 9. 설계 제약

- PostgreSQL only / Alembic forward-only / 인증 필수 / docker-compose V1 (하이픈) / `os.getenv()` 런타임 / docker `:latest` 금지.
- 모든 admin endpoint = JWT 인증 + Super Admin 권한.
- 비-super_admin 의 admin endpoint 접근 = **404** (existence-hide), 403 X.
- 모든 admin 쓰기 = audit 1줄 자동.
- 비밀번호 평문 X, bcrypt hash 만. 리셋 토큰도 동일.
- RFC 7807 Problem Details 강제.
- adversarial input parametrize 필수 (memory `feedback_adversarial_input_parametrize.md`).
- 신규 코드 line coverage ≥ 80%.
- 핵심 보안 코드 (authz / 비밀번호 리셋) Producer-Reviewer 패스.
- 알림 발송은 본 PR 에 미포함 (Phase 6 PR #18). 비밀번호 리셋 이메일은 stub (audit 만 기록, 실제 발송은 Phase 6 에서 wire-up).
- 새 도메인 0건 (User / Team / Membership 재사용). schema +1건 (password_reset_tokens) 가능.
- DT 변경 0건 / scan pipeline 변경 0건.

## 10. DoD (Definition of Done)

- main CI 9/9 success (image-scan soft-fail 유지).
- `ruff check apps/backend` clean / `mypy apps/backend` clean / `npm run lint` 0 errors / `npm run typecheck` clean.
- 신규/변경 backend coverage ≥ 80%.
- 신규/변경 frontend coverage (Vitest) ≥ 80%.
- E2E 4 시나리오 green (super_admin 흐름 + 비-super_admin 404 + 마지막 super_admin 차단 + 팀 멤버 관리).
- Playwright 하네스 verb 추가.
- EN/KO 번역 동시.
- audit 이벤트 7개 모두 기록 검증.
- security-reviewer PASS (M-/H- 흡수 또는 명시적 follow-up 등재).
- PR #13 squash merge 후 main 에 admin 7화면 중 2개 (Users / Teams) 가 동작.

## 11. 비주문 (PR #13 scope 외)

- DT Connector / Scan Queue / Disk / Audit Log / System Health 5 화면 → **PR #14**.
- 컴포넌트 승인 워크플로우 → **PR #15**.
- 알림 시스템 (이메일 SMTP / Slack / Teams) → **Phase 6 PR #18**. 본 PR 의 비밀번호 리셋 이메일은 stub.
- 사용자 / 팀 모델 변경 (예: 사용자 프로파일 사진, 팀 메타) → 본 PR scope 밖.
- OAuth 사용자 (GitHub / Google) → Phase 8 PR #23. 본 PR 은 password 사용자만.

## 12. 세션 종료 시

- `docs/sessions/2026-05-XX-phase4-pr13-admin-users-teams.md` 핸드오프 (`docs/v2-execution-plan.md` §7 양식).
- 본 prompt (`_next-session-prompt-phase4-pr13-users-teams.md`) → `docs/sessions/archive/next-session-prompts/`.
- 다음 세션 prompt: `_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md` 작성. 본 prompt 의 §1~12 구조 그대로 + plan §3.5 의 4.4~4.8 (DT Connector / Scan Queue / Disk / Audit / Health) 으로 변경.

본 작업 예상 시간: **8~12 시간** (admin layout + 7 endpoint + Drawer 2개 + E2E 4 시나리오 + i18n 2 언어 + 통합 테스트). 백그라운드 에이전트 (backend-developer + frontend-dev + i18n-specialist + test-writer) 적극 병렬 활용. 시간 부족 시 4.3 Teams 만 본 PR, 4.2 Users 다음 세션으로 분리 가능 — 하지만 4.1 admin 인프라 (router + layout) 가 둘 다 의존하므로 같은 PR 권고.
