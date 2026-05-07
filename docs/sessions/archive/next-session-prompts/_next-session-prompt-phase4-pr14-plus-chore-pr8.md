Phase 4 PR #14 (관리자 DT/Scan/Disk/Audit/Health 5 화면) **+** chore PR #8 (admin security follow-up F2~F12) — **단일 세션 / 별도 두 PR / 별도 Producer-Reviewer 패스 / 병렬 진행**.

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <Phase 4 PR #13 squash merge SHA, 본 세션 시작 시 `gh pr list --state merged --limit 3` 으로 확인>. 누적 머지: PR #1~#13 + chore CI fix 4건 + chore PR #1~#7 + Phase 4 PR #13 (관리자 Users/Teams). **Phase 4 의 두 번째 + 세 번째 PR 을 병렬 처리**.

본 세션은 chore PR #5/#6/#7 의 다중-PR 단일-세션 패턴을 그대로 이어간다 (`docs/sessions/_next-session-prompt-chore-pr6-pr7.md` 와 같은 형식).

## 0. 라벨링 단일 진실 (PR #13 에서 정정 완료)

- v2-execution-plan §3.5 = Phase 4 = **관리자 패널** (Users/Teams/DT/Scans/Disk/Audit/Health 7 화면 + 컴포넌트 승인 워크플로우).
- v2-execution-plan §3.7 = Phase 6 = **다국어 + 알림 + 안정성**. 알림은 본 PR 도 PR #15 도 아님 — Phase 6 PR #18.

본 세션의 PR 두 개:
- **PR #14** = §3.5 의 4.4 ~ 4.8 (DT Connector + Scan Queue + Disk + Audit Log + System Health 5 화면).
- **chore PR #8** = PR #13 의 security-reviewer F2~F12 일괄 흡수 (~200 LoC, 새 endpoint 0건).

PR #15 (컴포넌트 승인 워크플로우, §3.5 의 4.9~4.10) 는 본 세션 scope 밖 — 다음 세션.

## 1. 두 PR 의 작업 분담 + 충돌 회피

| | PR #14 (DT/Scan/Disk/Audit/Health) | chore PR #8 (admin security follow-ups) |
|---|---|---|
| **브랜치** | `feature/phase4-pr14-admin-dt-scans-disk-audit-health` | `feature/chore-pr8-admin-security-followups` |
| **단일 진실 prompt** | `docs/sessions/_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md` (이미 작성됨, 190 라인) | `docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md` §6 옵션 B (작업 절차 7건 명시) |
| **신규 파일 위주** | `apps/backend/api/v1/admin/{dt,scans,disk,audit,health}.py`, `services/admin_*_service.py`, `apps/frontend/src/features/admin/{dt,scans,disk,audit,health}/*.tsx`, hook · drawer | 거의 없음 (기존 파일 in-place 수정) |
| **수정 파일** | `apps/backend/api/v1/admin/__init__.py` (router include), `apps/frontend/src/features/admin/AdminLayout.tsx` (사이드바 항목 5개 추가), i18n EN/KO 5 namespace | `apps/backend/core/{errors,audit}.py`, `apps/backend/api/v1/admin/users.py` (role query strict), `apps/backend/services/admin_team_service.py` (with_for_update 추가), `scripts/seed_e2e_user.py` (env guard), `apps/backend/services/admin_user_service.py` (update_user_role 422 변환), `apps/frontend/src/lib/parseProblemBody.ts` (schema 강화) |
| **Producer-Reviewer** | 1 라운드 (필수 — 새 surface 5개) | 1 라운드 (필수 — 보안 fix 흡수 검증) |
| **CI** | 9/9 green | 9/9 green |
| **머지 순서** | **chore PR #8 먼저** → main pull → PR #14 시작 (또는 반대) | 위 |

**충돌 회피 핵심**: PR #14 와 chore PR #8 둘 다 `apps/backend/api/v1/admin/*.py` 와 `apps/frontend/src/features/admin/*` 를 만진다. 단:
- chore PR #8 의 `apps/backend/api/v1/admin/users.py` 수정 = 기존 endpoint 의 query parameter 정의 변경 (1줄). PR #14 는 users.py 미변경.
- chore PR #8 의 `apps/backend/services/admin_team_service.py` = 기존 메서드 SELECT FOR UPDATE 추가. PR #14 는 admin_team_service 미변경.
- chore PR #8 의 `apps/backend/core/errors.py` + `core/audit.py` = 공통 헬퍼. PR #14 가 새 admin endpoint 에서 동일 헬퍼 호출 → **chore PR #8 먼저 머지**하면 PR #14 가 보강된 헬퍼 그대로 사용 (audit PII redaction / Problem Details input redact 자동 적용).

→ **권고 머지 순서: chore PR #8 → main pull → PR #14**.
→ **권고 작업 순서**: chore PR #8 을 백그라운드 에이전트 (backend-developer + frontend-dev + test-writer) 에 위임하여 병렬로 진행하는 동시에, 메인 세션은 PR #14 의 admin 5 화면 작업. chore PR #8 이 ~200 LoC 으로 작아 1~2 시간 내 완료 → 머지 → 메인 세션이 main pull 후 PR #14 계속.

## 2. 직전 핸드오프 (반드시 시작 시 읽기)

- **`docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md`** — 단일 진실. §1.5 의 F2~F12 표 + §6 옵션 B 의 chore PR #8 작업 절차 7건. 본 세션이 흡수해야 할 fix 의 전체 목록.
- **`docs/sessions/_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md`** — PR #14 의 단일 진실 (이미 190 라인 작성됨). §4 의 4.4~4.8 endpoint 명세 + §6 의 라우팅 + §10 DoD. 본 prompt 는 그 파일을 superseded 하지 않고 그 파일을 PR #14 작업의 단일 진실로 위임. 본 prompt 는 두 PR 의 entry-point + 충돌 회피 가이드.
- `docs/v2-execution-plan.md` §3.5 — Phase 4 4.4~4.8 작업 정의 + DoD 표.
- `CLAUDE.md` "주요 기능 / 관리자" + "DT 연동 전략".
- 메모리 `feedback_adversarial_input_parametrize.md` — chore PR #8 의 F3 (role query strict) 단위 테스트에 적대적 입력 parametrize 필수.

## 3. 시작 시 검증 (반드시)

```
docker-compose -f docker-compose.dev.yml ps               # 6/6 healthy (backend hot-reload stuck 시 stop --timeout 1 + up -d)
docker-compose -f docker-compose.dev.yml -f docker-compose.dt.yml ps  # +dtrack-api healthy
gh run list --limit 3                                      # main 최신 success
git status                                                 # working tree
git checkout main && git pull --ff-only                    # PR #13 squash merge 반영
```

main 의 working tree 잔여:
- `.claude/scheduled_tasks.lock` — 무시.
- `docs/review-binaryanalysis-ng.md` — 사용자 작업 중 doc, 무시.
- 본 prompt (`_next-session-prompt-phase4-pr14-plus-chore-pr8.md`) — 세션 종료 시 archive.
- `_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md` — PR #14 머지 후 archive (본 prompt 와 동일 commit 으로 처리 가능).

브랜치 두 개:
- `feature/chore-pr8-admin-security-followups` — chore PR #8 백그라운드 에이전트.
- `feature/phase4-pr14-admin-dt-scans-disk-audit-health` — PR #14 메인 세션.

## 4. chore PR #8 작업 절차 요약 (위임용)

직전 PR #13 핸드오프 §6 옵션 B 그대로. backend-developer 에이전트에 다음과 같이 위임:

> chore PR #8 — admin security follow-up. PR #13 핸드오프 `docs/sessions/2026-05-07-phase4-pr13-admin-users-teams.md` 의 §1.5 F2~F12 표 + §6 옵션 B 의 7건 작업 절차가 단일 진실. 본 PR 의 정확한 7 작업:
>
> 1. **F2** — `apps/backend/core/errors.py:_validation_exception_handler` 의 `errors[].input` 평문 reflection 제거. `input` 필드를 `<redacted>` 로 치환 또는 키 자체 drop. CWE-209 회귀 단위 테스트 (PII 가 422 응답에 echo 되지 않음).
> 2. **F3** — `apps/backend/api/v1/admin/users.py` 의 `GET /v1/admin/users` query parameter `role` 을 `Literal["super_admin", "team_admin", "developer"] | None = None` 로 strict 화. 미정의 값 → 422 fail closed (현재는 silently 무시). adversarial parametrize: 정수, 리스트, javascript:, oversized, CRLF, null bytes.
> 3. **F4** — `apps/backend/core/audit.py` 의 `_SENSITIVE_COLUMNS` (또는 `_PII_COLUMNS` 신설) 에 `email` / `full_name` 추가. audit_logs.diff 가 sha256(value) 만 저장하도록 변경. retention purger task 영향 검토.
> 4. **F5** — `apps/backend/api/v1/admin/users.py` 의 password_reset_endpoint 에 docstring 추가 — admin 의 404-on-miss 가 super-admin gated 라 enumeration 위험 안 함을 명시 + 미래 Phase 6 public flow 는 uniform 204 무관 응답을 사용해야 함을 분리 명시. `docs/v2-execution-plan.md` §3.7 (Phase 6) 에도 보강 노트.
> 5. **F7** — `apps/backend/services/admin_team_service.py:delete_team` 에 `select(Team).where(Team.id == team_id).with_for_update()` 적용 + active scan 체크. F1 의 last-X-admin SELECT FOR UPDATE 패턴 그대로. 동시 삭제 + scan trigger race 회귀 테스트 (`test_admin_team_delete_concurrency.py`, asyncio.gather).
> 6. **F8** — `scripts/seed_e2e_user.py` 의 `--super-admin` 플래그 사용 시 `os.getenv("APP_ENV") in {"dev", "test", "ci"}` 가드. 그 외 환경에서 sys.exit(1) + 명시적 에러 메시지. CWE-489. Phase 7 의 .dockerignore 에서 scripts/ 제외 backlog (별도 PR).
> 7. **F9** — `apps/backend/services/admin_user_service.py:update_user_role` 에서 존재하지 않는 team_id (membership 변경 시) → IntegrityError 잡아서 422 + `{type: "team-not-found", detail: "team {team_id} does not exist"}` Problem Details. 회귀 단위 테스트.
> 8. **F10** — `apps/frontend/src/lib/parseProblemBody.ts` 의 extension passthrough 를 zod schema 로 강화. 알려진 Problem 도메인 코드 (whitelist) 만 허용 + 미지 코드는 graceful fallback. 향후 sensitive extension 자동 차단.
> 9. **F12** — `apps/backend/core/admin_errors.py` (또는 동등 위치) 의 `_problem_for_admin_user_error` 의 `detail = str(exc)` 위에 코멘트 추가 — 미래 PII echo 가능성 + Phase 6 public flow 에서는 sanitize 필수.
>
> F6 / F11 은 as-is (의도적 설계, 문서 only). 본 PR 에 포함 X.
>
> 변경 예상: ~200 LoC (~70 백엔드 + ~30 프론트 + ~100 테스트). commit 7~9개 (logical 단위) 또는 1 commit (작업 grouping). 핵심 보안 fix 는 별도 commit 권고 (F2 / F4 / F7 / F9). 각 fix 마다 회귀 단위 테스트 1건 이상.
>
> security-reviewer Producer-Reviewer 1 라운드 — fix 의 정확성 + 새 위험 (예: F4 sha256 hashing 의 lookup 깨짐) + adversarial input 회귀.
>
> 단위 + 통합 + adversarial parametrize green / ruff/mypy clean / line coverage ≥ 80% / security-reviewer PASS.
>
> 끝나면 PR open (제목 `chore: admin security follow-ups (F2~F12 from PR #13 review)`) + body 에 9 작업 항목 체크리스트.

이 작업을 **단일 백그라운드 backend-developer 에이전트** 에 위임 — 메인 세션은 PR #14 진행. 에이전트 결과 받아서 PR open / push / squash merge 까지 메인 세션이 처리 (사용자 push/PR allow 정책).

## 5. PR #14 작업 절차 요약 (위임 X, 메인 세션 + 보조 에이전트)

`docs/sessions/_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md` 가 **단일 진실**. 그 파일의 §4 작업 절차 (4.4 DT / 4.5 Scans / 4.6 Disk / 4.7 Audit / 4.8 Health) + §6 라우팅 (backend-developer / frontend-dev / i18n-specialist / test-writer / security-reviewer) + §10 DoD 그대로 사용.

요약 (자세한 endpoint 명세 / 안전장치 / 화면 디자인 / hook 명은 PR #14 prompt 참조):

| § | 화면 | 백엔드 endpoint | 프론트 페이지 |
|---|------|----------------|--------------|
| 4.4 | DT Connector | `/v1/admin/dt/{status,orphans,health-check}` + orphan cleanup task 트리거 | `/admin/dt` |
| 4.5 | Scan Queue | `/v1/admin/scans` (목록/취소/재시도) + WebSocket live progress | `/admin/scans` |
| 4.6 | Disk | `/v1/admin/disk` (workspace + DT volume + DB) + 임계치 80% 알림 stub | `/admin/disk` |
| 4.7 | Audit Log | `/v1/admin/audit` (검색/필터/CSV export) | `/admin/audit` |
| 4.8 | System Health | `/v1/admin/health` (postgres/redis/celery/dt/disk 종합) | `/admin/health` |

**핵심 패턴 (PR #13 인프라 그대로 재사용)**:
- 모든 endpoint = `require_super_admin_or_404` (PR #13 도입).
- 모든 쓰기 = audit auto-emit (PR #13 패턴).
- `with_for_update()` for 경쟁 조건 (PR #13 의 last-X-admin 패턴).
- RFC 7807 Problem Details + i18n EN/KO + Playwright 하네스 (`AdminDTHarness` 등 5개).
- adversarial input parametrize 필수.
- 신규 line coverage ≥ 80%.

## 6. 두 PR 의 핵심 라우팅 통합

| 에이전트 | chore PR #8 | PR #14 |
|---------|-------------|--------|
| **backend-developer** | F2 / F3 / F4 / F5 / F7 / F8 / F9 / F12 (백그라운드) | 4.4 / 4.5 / 4.6 / 4.7 / 4.8 의 admin/* endpoint + service |
| **frontend-dev** | F10 (parseProblemBody zod) | 4.4~4.8 의 admin 페이지 5개 + 드로어 + hook |
| **i18n-specialist** | — | 4.4~4.8 의 EN/KO admin namespace 5개 |
| **test-writer** | F2 / F4 / F7 / F9 회귀 + adversarial parametrize | 4.4~4.8 의 단위/통합/E2E 5 시나리오 + 하네스 5개 |
| **security-reviewer** | chore PR #8 1 라운드 | PR #14 1 라운드 |
| **db-designer** | — | 4.7 audit_log 인덱스 검토 (검색 < 1초 in 100만 행 — DoD §3.5 4.7), 필요 시 forward-only revision 1건 |

## 7. 설계 제약 (두 PR 공통)

- PostgreSQL only / Alembic forward-only / 인증 필수 (`require_super_admin_or_404`) / docker-compose V1 / `os.getenv()` 런타임 / docker `:latest` 금지.
- 모든 admin 쓰기 = audit auto-emit + PII redaction (chore PR #8 F4 적용 후).
- adversarial input parametrize 필수 (memory `feedback_adversarial_input_parametrize.md`) — chore PR #8 의 F3 + PR #14 의 모든 query parameter.
- VEX status 7-state 보존 / Optimistic concurrency 보존.
- 알림 발송은 본 두 PR 모두 미포함 (Phase 6 PR #18). 본 세션 의 disk 임계치 / DT down 등은 stub (audit only).
- 새 도메인 0건 / 새 endpoint 다수 (PR #14) / schema +0~1건 (audit_log 인덱스 추가 시).
- 핵심 보안 fix (chore PR #8) 와 새 admin surface (PR #14) 모두 Producer-Reviewer 패스.
- **chore PR #8 먼저 머지 → PR #14 가 보강된 헬퍼 즉시 활용**. 충돌 시 PR #14 메인 세션이 rebase 후 진행.

## 8. DoD (두 PR 각각)

### chore PR #8
- ruff / mypy / lint clean.
- 7 fix 모두 회귀 단위 테스트 동반.
- 신규/변경 coverage ≥ 80%.
- security-reviewer PASS (F2~F12 closed, F6/F11 as-is 명시).
- PR open + CI 9/9 green + squash merge.

### PR #14
- main CI 9/9 success (image-scan soft-fail 유지).
- ruff / mypy clean / npm lint 0 errors / typecheck clean.
- 신규 backend coverage ≥ 80%, frontend Vitest ≥ 80%.
- E2E 5 시나리오 green (DT / Scans / Disk / Audit / Health 각 1개).
- Playwright 하네스 5개 추가.
- EN/KO 번역 동시 + 5 namespace 추가.
- audit 이벤트 신규 정의 모두 기록 검증.
- security-reviewer PASS.
- PR open + 9/9 green + squash merge.

## 9. 비주문 (두 PR scope 외)

- **컴포넌트 승인 워크플로우** (`/approvals`, §3.5 4.9~4.10) → **PR #15** (다음 세션).
- **알림 시스템** (이메일 / Slack / Teams) → **Phase 6 PR #18**. 본 세션의 disk 임계치 / DT down 알림은 audit + log only (실제 발송은 Phase 6 wire-up).
- **OAuth (GitHub / Google)** → Phase 8 PR #23.
- **Docusaurus 사용자/관리자/기여자 가이드** → Phase 7 PR #21.
- **Helm chart** → Phase 8 (Helm 도입 시점은 §1.3 의 데모 SaaS 결정 게이트에 따라 변경 가능).
- **scripts/ 의 .dockerignore 제외** (chore PR #8 F8 의 후속) → 별도 chore PR 또는 Phase 7 PR #20 의 prod compose 작업 안에서.

## 10. 세션 종료 시

- chore PR #8 핸드오프: `docs/sessions/2026-05-XX-chore-pr8-admin-security-followups.md` (`docs/v2-execution-plan.md` §7 양식).
- PR #14 핸드오프: `docs/sessions/2026-05-XX-phase4-pr14-admin-dt-scans-disk-audit-health.md`.
- 본 prompt + `_next-session-prompt-phase4-pr14-admin-dt-scans-disk-audit-health.md` 두 prompt 모두 `docs/sessions/archive/next-session-prompts/` 로 이동.
- 다음 세션 prompt: `_next-session-prompt-phase4-pr15-component-approval-workflow.md` 작성. v2-execution-plan §3.5 의 4.9 + 4.10 기반.

본 작업 예상 시간: **chore PR #8 ~2 시간 (백그라운드) + PR #14 ~10~14 시간 (메인 세션 + 보조 에이전트 4 병렬)** = 단일 세션 ~12~16 시간. 시간 부족 시 chore PR #8 만 본 세션에 머지 + PR #14 다음 세션으로 분리. 또는 PR #14 의 5 화면 중 4.4 (DT) + 4.5 (Scans) 두 개만 본 PR + 4.6/4.7/4.8 분리 PR — 단 admin 사이드바 일관성 (5개 모두 한 번에 노출 권고) 고려해서 결정.
