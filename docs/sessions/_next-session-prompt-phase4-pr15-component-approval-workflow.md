Phase 4 PR #15 — 컴포넌트 승인 워크플로우 (`/approvals`). v2-execution-plan §3.5 의 4.9 + 4.10. **Phase 4 의 마지막 PR**.

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

## 0. 단일 진실

- main HEAD = <Phase 4 PR #14 squash merge SHA, 본 세션 시작 시 `gh pr list --state merged --limit 3` 으로 확인>. 누적 머지: PR #1~#15 (GitHub PR 번호 기준 — PR #14 = chore PR #8, PR #15 = phase4 PR #14).
- v2-execution-plan §3.5 = Phase 4. 본 세션 = 4.9 (승인 워크플로우 UI) + 4.10 (E2E Admin 7화면 + 승인 워크플로우 시나리오 9개 green).
- v2-execution-plan §3.7 = Phase 6 = 알림. 4.9 의 "Pending → Under Review → Approved/Rejected, 알림 발송" 중 알림은 Phase 6 PR #18 — 본 PR 은 audit + log 만, 실제 발송 X.

## 1. 직전 핸드오프 (반드시 시작 시 읽기)

- **`docs/sessions/2026-05-08-phase4-pr14-admin-dt-scans-disk-audit-health.md`** — 본 PR 의 직전 PR (Phase 4 PR #14). admin 7 화면 인프라 완성. 본 PR 은 그 위에 `/approvals` 추가.
- **`docs/sessions/2026-05-08-chore-pr8-admin-security-followups.md`** — 동시 진행 chore PR. PII sha256 / Problem redact / errors handler 등이 본 PR 자동 적용.
- **`docs/v2-execution-plan.md` §3.5 의 4.9~4.10** — 단일 진실.
- **CLAUDE.md** "주요 기능 / 거버넌스 / 컴포넌트 승인 워크플로우" + "조건부 라이선스 → 법무 검토 + 승인 워크플로우".
- 메모리 `feedback_admin_existence_hide_pattern.md` (admin pattern) / `feedback_optimistic_concurrency_pattern.md` (`with_for_update()` for race) / `feedback_adversarial_input_parametrize.md` / `feedback_vex_status_enum.md` (VEX 7-state — 본 PR 도 status enum 명확히).
- 메모리 `project_phase4_admin_followup_pr.md` — chore PR #9 backlog (PR #14 G2~G10, chore PR #8 M1~M3, L1/L2). 본 PR 머지 후 또는 병렬 진행.

## 2. 시작 시 검증 (반드시)

```
docker-compose -f docker-compose.dev.yml ps               # 6/6 healthy
docker-compose -f docker-compose.dev.yml -f docker-compose.dt.yml ps  # +dtrack-api healthy
gh run list --limit 3                                      # main 최신 success
git status                                                 # working tree
git checkout main && git pull --ff-only                    # PR #14 squash merge 반영
```

main 의 working tree 잔여 (무시):
- `.claude/scheduled_tasks.lock` / `.claude/worktrees/` / `docs/review-binaryanalysis-ng.md`
- `docs/sessions/_next-session-prompt-phase4-pr15-component-approval-workflow.md` (본 prompt — 세션 종료 시 archive)

브랜치: `feature/phase4-pr15-component-approval-workflow` 신규 생성.

## 3. 작업 범위

### 3.1 도메인 모델 (db-designer)

**테이블 신설**: `component_approvals` — Pending / Under Review / Approved / Rejected 상태 + 다중 평가자 지원.

```sql
CREATE TABLE component_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id UUID NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    requested_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    status approval_status NOT NULL DEFAULT 'pending',
    decided_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    decided_at TIMESTAMP WITH TIME ZONE,
    decision_note TEXT,
    -- ETag for optimistic concurrency (PR #11 패턴)
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TYPE approval_status AS ENUM ('pending', 'under_review', 'approved', 'rejected');
CREATE INDEX ix_component_approvals_team_status ON component_approvals (team_id, status);
CREATE INDEX ix_component_approvals_status_requested_at ON component_approvals (status, requested_at);
CREATE UNIQUE INDEX ix_component_approvals_unique_open ON component_approvals (component_id, project_id) WHERE status IN ('pending', 'under_review');
```

**Why**: 단일 컴포넌트 + 프로젝트 조합당 active (pending/under_review) approval 은 1건만. unique partial index 강제. ETag (`version`) 는 PR #11 의 if_match echo 패턴.

**Alembic 0008** (forward-only).

### 3.2 백엔드 API (backend-developer)

**엔드포인트** (모두 `require_team_member` 또는 `require_super_admin_or_404` — 정확한 권한은 §3.4 참고):

1. `GET /v1/approvals` — 내 팀 + super_admin 인 경우 전체. 필터 (`status`, `team_id`, `requested_by_user_id`, `from`, `to`).
2. `GET /v1/approvals/{id}` — 단건 + ETag.
3. `POST /v1/approvals` — 새 승인 요청 (component_id + project_id). 활성 approval 존재 시 409 + `approval_already_open`.
4. `PATCH /v1/approvals/{id}/transition` — 상태 전이 (`under_review` / `approved` / `rejected`). `If-Match` 헤더 필수. body `{action, decision_note?}`. PR #11 의 `with_for_update()` 패턴.
5. `DELETE /v1/approvals/{id}` — 요청자 또는 super_admin 만. terminal 상태 (approved/rejected) 는 삭제 불가 → 409.

**상태 전이 매트릭스**:
- `pending` → `under_review` / `rejected`
- `under_review` → `approved` / `rejected`
- `approved` / `rejected` = terminal (재요청은 새 row 생성).
- 각 전이 시 audit auto-emit (PR #13 패턴) + (Phase 6 PR #18 에서 알림 wire-up). 본 PR 은 audit + structlog 만.

**도메인 RFC 7807 Problem 신규**:
- `approval_already_open` (409)
- `approval_invalid_transition` (409)
- `approval_etag_mismatch` (412)
- `approval_terminal_state` (409)

### 3.3 프론트엔드 (frontend-dev)

**라우트**: `/approvals` (모든 user 가시 — admin 외부).

**페이지** (`apps/frontend/src/features/approvals/ApprovalsPage.tsx`):
- 사이드바 navigation 항목 추가 — 일반 user 도 보이게 (admin 외부). `/projects` 옆.
- 인라인 filter toolbar (status / team / requestor / 날짜 범위).
- 컴팩트 테이블 (40px 행) — component_purl + project + team + status badge + requested_by + requested_at + decided_at + decided_by.
- 행 클릭 → drawer (component 상세 + 라이선스 정보 + 결정 노트 + 전이 액션 버튼).
- Pending / Under Review 만 actionable; Approved / Rejected 은 read-only.
- 인라인 confirm strip (PR #13 패턴) + If-Match 자동 처리 (TanStack Query).

**EN/KO i18n**: `apps/frontend/src/locales/{en,ko}/approvals.json` 신규 namespace + `nav.approvals`.

### 3.4 권한 매트릭스

| 액션 | Developer | Team Admin | Super Admin |
|------|-----------|-----------|-------------|
| 자신 팀 list | ✅ | ✅ | ✅ (모든 팀) |
| 자신 팀 detail | ✅ | ✅ | ✅ (모든 팀) |
| 새 요청 (`POST`) | ✅ (자신 팀) | ✅ (자신 팀) | ✅ (모든 팀) |
| `under_review` 전이 | ❌ | ✅ (자신 팀) | ✅ |
| `approved` 전이 | ❌ | ✅ (자신 팀) | ✅ |
| `rejected` 전이 | ❌ | ✅ (자신 팀) | ✅ |
| 삭제 | 본인 요청만 | 자신 팀 | ✅ |

비-팀원 접근 = 404 (existence-hide). super_admin 은 cross-team 전체 가시.

### 3.5 핵심 라우팅

- **db-designer** (필수): `component_approvals` 테이블 + Alembic 0008 + 인덱스 + ENUM.
- **backend-developer** (필수): 5 endpoint + service + Pydantic schemas + 권한 매트릭스 + audit emit + ETag/`with_for_update()` race 차단.
- **frontend-dev** (필수): `/approvals` 페이지 + drawer + 사이드바 + EN/KO i18n + If-Match handling.
- **test-writer** (필수): pytest 단위/통합 + adversarial parametrize + Playwright e2e (시나리오 9 — 본 PR 4 + Phase 4 회귀 5).
- **security-reviewer** (필수): Producer-Reviewer 1라운드 — IDOR (다른 팀 approval 접근 시도) / 전이 권한 우회 / If-Match bypass / decision_note 의 PII / SQL injection.

### 3.6 Phase 4 의 4.10 — E2E 시나리오 9개 (회귀 + 신규)

기존 (PR #13 + #14 회귀) 8 시나리오 + 본 PR 신규 4 시나리오 = 12. 단 v2-execution-plan §4.10 의 "9개" 는 admin 7화면 + 승인 워크플로우 2개. 본 PR 에서는:
- 신규 4: pending 생성 / under_review 전이 / approved 종결 / rejected 종결.
- 또는 4 시나리오 압축 + 권한 매트릭스 1 시나리오 (비-팀원 = 404).

`apps/frontend/tests/_harness/ApprovalsHarness.ts` + `tests/e2e/approvals_workflow.spec.ts`.

## 4. 설계 제약 (PR #14 와 동일 + 추가)

- PostgreSQL only / Alembic forward-only / docker-compose V1 / `os.getenv()` 런타임 / docker `:latest` 금지.
- 모든 쓰기 = audit auto-emit + PII redaction (chore PR #8 F4 적용 후).
- adversarial input parametrize 필수 (memory `feedback_adversarial_input_parametrize.md`) — `decision_note` (free text) / status filter / team_id query.
- VEX status 7-state 보존 (별 컴포넌트 — vuln_finding_status 와는 분리, `approval_status` 는 새 enum).
- ETag/If-Match optimistic concurrency (memory `feedback_optimistic_concurrency_pattern.md`) — vulnerability_service 패턴 일관.
- 알림 발송 미포함 (Phase 6 PR #18). 본 PR 의 전이는 audit only.
- 핵심 보안 fix 는 Producer-Reviewer 패스.

## 5. DoD

- main CI 9/9 success.
- ruff / mypy / npm lint / npm typecheck clean.
- 신규 backend coverage ≥ 80%, frontend Vitest ≥ 80%.
- E2E 4 신규 시나리오 + Phase 4 회귀 admin 시나리오 모두 green.
- `/approvals` 페이지 + drawer + 사이드바 + EN/KO 동시.
- audit 이벤트 신규 (4 액션) 모두 기록 검증.
- security-reviewer PASS.
- alembic upgrade 0008 적용 가능.
- PR open + 9/9 green + squash merge.

## 6. 비주문 (PR #15 scope 외)

- **알림 발송** (이메일/Slack/Teams) → Phase 6 PR #18.
- **감사 로그 retention** (자동 purge) → Phase 6 PR #18.
- **OAuth GitHub/Google** → Phase 8.
- **chore PR #9** (admin follow-ups) → 본 PR 머지 후 또는 병렬. backlog memory `project_phase4_admin_followup_pr.md`.

## 7. 세션 종료 시

- 핸드오프: `docs/sessions/2026-05-XX-phase4-pr15-component-approval-workflow.md` (`docs/v2-execution-plan.md` §7 양식).
- 본 prompt → `docs/sessions/archive/next-session-prompts/`.
- 다음 세션 prompt: `_next-session-prompt-phase5-pr16-api-keys-webhooks.md` (Phase 5 시작) 또는 `_next-session-prompt-chore-pr9-admin-followups.md` (chore PR #9).
- v2-execution-plan §3.5 의 Phase 4 완료 표시.

본 작업 예상 시간: 8~12 시간.
