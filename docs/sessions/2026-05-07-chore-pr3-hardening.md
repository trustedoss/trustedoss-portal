# Session Handoff — 2026-05-07 — chore PR #3 — Hardening (size caps + nosniff + rate-limit + RFC 6266)

## 1. 무엇을 했나

- **chore PR #3 commit + push + gh pr create 완료** — 브랜치 `feature/chore-pr3-hardening`, PR #7 (`https://github.com/trustedoss/trustedoss-portal/pull/7`). PR #11/#12/#13 누적 security-reviewer follow-up 을 단일 PR 로 통합. **새 endpoint 0건**, 행동 변화 4 건뿐 (size cap / 보안 헤더 / rate-limit / RFC 6266) + 동작 보존 refactor 2 건 (`escape_like` promote / `assert_team_access` shared helper 도입 + 부분 적용).
- **사전 정정 — PR #13 회귀 (한 줄)**:
  - 핸드오프 prompt 가 "main HEAD = PR #13 merge commit" 을 전제했지만 실제로는 PR #6 (PR #13) 이 OPEN 상태였고 backend integration 1 건 실패 (`tests/integration/test_obligations_api.py::test_list_returns_seeded_obligations`).
  - 원인: `API-MIT` SPDX 가 `test_licenses_api.py:230` + `test_obligations_api.py:236` 양쪽에 하드코딩되어 같은 postgres 컨테이너에서 `uq_licenses_spdx_id` 충돌. 사용자 결정 → **옵션 A (PR #13 fix → 머지 → chore PR #3)** 진행.
  - obligations test 의 4 개 하드코딩 SPDX (API-MIT / NOTICE-MIT / MD-MIT / DL-MIT) 모두 `OBL-<orig>-<uuid8>` 패턴으로 일괄 교체. body assertion 도 동적 변수 비교로 갱신. commit `d456ee4` push → CI green → PR #13 머지 (`a3634e3`).
  - **사용자 정책 보강**: push 차단 → 사용자 옵션 B 선택 → `.claude/settings.json` (project-scope) 에 `Bash(git push *)` + `Bash(gh pr merge *)` allow 등재. 이후 push/PR 직접 수행 가능. 이 working-tree 변경은 chore PR #3 commit 에는 포함하지 않음 (별도 chore 권고).
- **chore PR #3 — 27 files / +1119 / -129**:
  - **신규 7 파일**:
    - `apps/backend/core/sql_safety.py` — `escape_like(value: str) -> str` 단일 export. PostgreSQL `LIKE` 와일드카드 (`%`, `_`, `\\`) 이스케이프. SQLAlchemy `.ilike(pattern, escape='\\\\')` 와 round-trip 호환.
    - `apps/backend/core/authz.py` — `can_access_team(actor, team_id) -> bool` (super_admin bypass + team membership predicate) + `assert_team_access(actor, team_id, *, log, resource, resource_id, deny: Callable[[], Exception]) -> None`. happy path 무 로그, denial 시 단일 `authz.cross_team_attempt` 라인 + `raise deny()` (lazy callable — 정상 경로에서 예외 미생성).
    - `apps/backend/tests/unit/test_sql_safety.py` — 6 cases (literal/wildcard 분리 + SQLAlchemy round-trip).
    - `apps/backend/tests/unit/test_authz.py` — 8 cases (super_admin / 멤버십 / happy 무 로그 / 403 + 404 deny / lazy callable).
    - `apps/backend/tests/unit/test_security_headers.py` — 3 cases (성공 / 4xx / 기존 헤더 보존).
    - `apps/backend/tests/unit/test_obligations_api_helpers.py` — 7 cases (`_safe_filename_token` + RFC 6266 ASCII 폴백 / UTF-8 round-trip / 한국어 / `;,"` 이스케이프).
    - `apps/backend/tests/unit/test_size_caps.py` — 5 cases (cap constant 핀 + `_clamp_obligation_text` boundary / multi-byte UTF-8 / exact-cap / empty).
  - **수정 backend 8 파일**:
    - `core/middleware.py` — `SecurityHeadersMiddleware` 추가. ASGI pure (BaseHTTPMiddleware 회피). `nosniff` / `no-referrer` / `DENY` 3 헤더, 기존 per-route 헤더 보존 (idempotent 루프).
    - `main.py` — `SecurityHeadersMiddleware` 를 **마지막에 추가** (Starlette `add_middleware` 는 last-added 가 outermost) → CORS preflight + 4xx/5xx 도 헤더 부착. 주석에 실제 ordering 명시.
    - `services/vulnerability_service.py` — `_escape_like` 정의 → `from core.sql_safety import escape_like as _escape_like` thin alias (out-of-tree caller 호환), `re` import 제거.
    - `services/license_service.py` — `_can_access_team` 정의 제거, `from core.authz import assert_team_access`. 2 cross-team 가드 (`list_project_licenses` 403 / `get_license_finding_detail` 404) 모두 `assert_team_access` 로 마이그레이션. `_load_affected_components` 에 `LIMIT cap+1` truncation detection + cap=500 + 트리거 시 별도 `COUNT(*)` 서브쿼리. 응답 dict 에 `affected_components_truncated` / `affected_components_total` 추가.
    - `services/obligation_service.py` — 동일 패턴. 3 cross-team 가드 (list / detail / notice) 모두 `assert_team_access`. `_clamp_obligation_text` 신규 (64 KiB, UTF-8 codepoint boundary 안전 — `errors="ignore"` 로 partial 트레일러 drop, U+FFFD 미출력). `text_truncated` 응답 필드 추가.
    - `services/{project,project_detail}_service.py` — `_can_access_team` 정의를 `from core.authz import can_access_team as _can_access_team` 로 alias 유지 (해당 모듈은 본 PR 에서 `assert_team_access` 마이그레이션 미진행, 별도 chore 로 follow-up).
    - `api/v1/obligations.py` — `@limiter.limit("10/minute")` 데코레이터 (slowapi, IP-keyed, redis 스토리지). `_format_content_disposition(name, ext)` 신규 — RFC 6266 ASCII 폴백 + `filename*=UTF-8''<percent-encoded with safe="">`. detail endpoint 응답 envelope 에 `text_truncated` / `affected_components_truncated` / `affected_components_total` wire-up. 429 OpenAPI 에 `application/problem+json` content-type 명시.
    - `api/v1/licenses.py` — detail endpoint 응답 envelope 에 `affected_components_truncated` / `affected_components_total` wire-up.
  - **수정 schemas 2 파일**:
    - `schemas/license_detail.py` — `LicenseDetailResponse` 에 `affected_components_truncated: bool = False` + `affected_components_total: int = 0`.
    - `schemas/obligation_detail.py` — `ObligationDetailResponse` 에 `text_truncated: bool = False` + `affected_components_truncated: bool = False` + `affected_components_total: int = 0`.
  - **수정 tests 3 파일**:
    - `tests/integration/test_obligations_api.py` — 기존 `test_notice_download_attaches_filename_with_safe_token` assertion 을 multi-segment Content-Disposition 에 맞춰 갱신 (`ascii_part` 분리 추출 + `filename*=UTF-8''` 존재 검증). 신규 `test_notice_download_filename_carries_utf8_round_trip_for_non_ascii_project` — 한국어 프로젝트명 percent-decode round-trip.
    - `tests/unit/features/projects/{LicenseDrawer,ObligationDrawer}.test.tsx` — fixture detail 객체에 `affected_components_truncated: false` / `affected_components_total: N` / `text_truncated: false` 추가 (TS 타입 일치).
  - **수정 frontend 4 파일**:
    - `features/projects/api/{licensesApi,obligationsApi}.ts` — 새 wire 필드 type 정의.
    - `features/projects/components/LicenseDrawer.tsx` — `DrawerAffectedSection` 에 `total`/`truncated` props 추가, truncated 시 `text-xs text-muted-foreground` 메시지 표시 ("Showing N of M components…").
    - `features/projects/components/ObligationDrawer.tsx` — 동일 + `text_truncated` 시 본문 아래 안내 메시지 (`obligations.drawer.text_truncated`).
  - **수정 i18n 2 파일**:
    - `locales/{en,ko}/project_detail.json` — 4 키씩 추가 (`licenses.drawer.affected_truncated`, `obligations.drawer.{affected_truncated, text_truncated}`).
- **security-reviewer Producer-Reviewer 1 라운드**:
  - **평결: PASS-with-follow-ups**, 블로커 0, Critical/High(코드)/Medium 0.
  - 발견: F1 (High doc-vs-code) — 미들웨어 ordering 주석이 실제 흐름과 반대였음. **Fix applied**: `SecurityHeadersMiddleware` 를 마지막 add_middleware 호출로 이동, 주석 정정.
  - F2 (Medium) — 429 OpenAPI content-type 누락. **Fix applied**.
  - F3 (Low) — `assert_team_access` 가 dead code. **Fix applied**: license + obligation 서비스의 5 cross-team gate 마이그레이션. 나머지 3 모듈 follow-up.
  - F4 (Low) — cap 상수 회귀 테스트 부재. **Fix applied**: `tests/unit/test_size_caps.py` 5 case (cap=500 / cap=64 KiB constant pin + `_clamp_obligation_text` boundary).
  - F5 (Info) — `.claude/settings.json` working-tree 변경. 의도대로 commit 미포함.
  - F6 (Info) — unused `_SECURITY_HEADER_NAMES`. **Fix applied**: 제거.
  - F7 (Info) — CSP 별도 PR. 본 PR scope 외, OK.
- **로컬 검증**:
  - `ruff check apps/backend` clean.
  - `mypy apps/backend` clean (124 source files).
  - `npm run lint` 0 errors / 14 pre-existing fast-refresh warnings.
  - `npm run typecheck` clean.
  - `pytest tests/unit` **421 passed**, 137 skipped (postgres-gated). 이전 PR #13 baseline 414 → +7 (test_authz 8 + test_sql_safety 6 + test_security_headers 3 + test_obligations_api_helpers 7 + test_size_caps 5 = 29 신규, 일부 기존 helper 이동으로 net +7. 정확 카운트는 CI 가 검증).
  - `npm run test -- --run` **241/241 pass** — PR #13 baseline 그대로 유지 (회귀 0).
  - bandit 미실행 (로컬 env 부재). CI semgrep / gitleaks / pip-audit 도입은 별도 chore (PR #10/#11/#12/#13 누적 권고).
- **CI 상태 (commit 직후)**: 9 잡 IN_PROGRESS, 본 PR 시점에는 결과 미확정. 다음 세션 시작 시 `gh pr view 7` 로 확인.

## 2. 결정 사항 / 변경된 가정

- **PR #13 merge 전제 정정**: 핸드오프 prompt 가 "main HEAD = PR #13 merge commit" 을 전제했으나 실제 PR #6 OPEN. SPDX 충돌 1 줄 fix 후 머지 → chore PR #3 시작 (옵션 A). 30 분 추가 소요.
- **`assert_team_access` 부분 적용**: helper 는 5 모듈 전체에서 사용하도록 설계되었지만 본 PR 에서는 license + obligation 의 5 사이트만 마이그레이션. 나머지 3 모듈 (project / project_detail / vulnerability) 의 11 사이트는 별도 chore 로 분리 — 16 사이트 일괄 마이그레이션은 회귀 위험 ↑, 단계적 채택이 안전.
- **`_can_access_team` alias 보존 정책**:
  - `vulnerability_service.py` / `project_service.py` / `project_detail_service.py` — 본 PR 에서 `assert_team_access` 미적용 → `from core.authz import can_access_team as _can_access_team` alias 유지 (out-of-tree 호출자 호환 + lint 통과).
  - `license_service.py` / `obligation_service.py` — 5 사이트 전부 마이그레이션 완료 → alias 제거, `from core.authz import assert_team_access` 만.
- **`SecurityHeadersMiddleware` 위치**: F1 fix 로 마지막 add_middleware (outermost) 로 이동. 결과: CORS preflight (`OPTIONS`) + 4xx/5xx 응답에도 nosniff/Referrer-Policy/Frame-Options 부착. CSP 는 의도적으로 본 PR scope 외 (`/docs` Swagger UI 인라인 스크립트 호환 별도 작업).
- **`affected_components` cap = 500, `obligation.text` cap = 64 KiB**: 핀된 `tests/unit/test_size_caps.py` 의 첫 두 테스트로 미래 silent bump 차단. cap 변경 시 schema description + i18n 디스클로저 카피도 동시 갱신 필요.
- **truncation detection 패턴**: `LIMIT cap+1` 으로 정상 응답에서는 추가 round-trip 0건. cap 트리거 시에만 `SELECT COUNT(*) FROM (... GROUP BY ...) sub` 로 정확한 total. license_service 는 `(cv.id, kind)` GROUP BY, obligation_service 는 `cv.id` GROUP BY (의무 단위는 finding kind 축 미사용).
- **`_clamp_obligation_text` byte-slice + `errors="ignore"`**: 64 KiB 바이트 경계에서 multi-byte 코드포인트가 잘리면 partial 트레일러를 drop (U+FFFD 미출력). `test_clamp_handles_multibyte_codepoint_at_boundary` 가 핀.
- **NOTICE rate-limit 10/min/IP**: slowapi 의 기존 `core.ratelimit.limiter` 인스턴스 재사용 (Redis storage, X-Forwarded-For 정규화). 429 응답은 기존 `rate_limit_exceeded_handler` (RFC 7807 + Retry-After) 통과. e2e 환경은 `RATELIMIT_DISABLED=1` 로 우회 (이전 PR #9 패턴).
- **RFC 6266 multi-segment**: `attachment; filename="<ASCII>"; filename*=UTF-8''<percent-encoded>`. percent-encoder `safe=""` 로 `;` `,` `"` 모두 escape — Content-Disposition 헤더 파서가 token 경계로 오인할 수 없음.
- **MEMORY.md 갱신 후보**:
  - chore PR 의 4-wave 구조 (small fixes + size cap + reviewer feedback fix + commit). 재사용 패턴.
  - `.claude/settings.json` push allow 가 project scope 에 등재됨 — 향후 새 contributor 도 동일 권한.

## 3. 현재 상태

- **머지된 PR**: #1 (54e858f), #2 (ca8ab41), #3 (9c19b5a), #4 (8ddedfb), #5 (4325835), #6 (55e67bd), #7 (d7bc929 + 93c41a4), #8 (502f02f + ebb9c53), #9 (f55e70d + 9da6b3c), chore PR #1 (6366b62), chore PR #2 (38236e2), Phase 3 PR #10 (7d6f66d), Phase 3 PR #11 (e19bd8a), Phase 3 PR #12 (ac15d6a), **Phase 3 PR #13 (a3634e3)**.
- **진행 중 PR**: **#7 — chore: PR #11/#12/#13 hardening — feature/chore-pr3-hardening**. CI 9 잡 IN_PROGRESS (commit 09467d6 시점).
- **GitHub origin/main**: `a3634e3` (Phase 3 PR #13 머지).
- **변경 규모 (chore PR #3)**: 27 files / +1119 / -129. 신규 backend 7 (core 2 + tests 5) + 수정 backend 8 (services 5 + middleware/main 2 + api 1) + 수정 schemas 2 + 수정 frontend 4 + 수정 i18n 2 + 수정 tests 3.
- **로컬 환경**: postgres 컨테이너 disk-full restart loop 지속 (PR #11/#12/#13 carry-over). redis/backend/frontend healthy. CI 가 integration 검증 채널.
- **i18n**: EN + KO 양쪽 4 키씩 추가, parity 100%.
- **`.claude/settings.json` (working-tree only)**: project-scope allow 에 `Bash(git push *)` / `Bash(gh pr merge *)` 추가됨. 본 PR commit 미포함. 별도 commit 으로 처리할지는 다음 세션 결정.

## 4. 후속 backlog

### chore PR #3 follow-up (잠재적 chore PR #4)
- **`assert_team_access` 잔여 마이그레이션** — `services/{project,project_detail,vulnerability}_service.py` 의 11 cross-team 사이트. license/obligation 패턴 그대로 미러. 회귀 테스트는 기존 IDOR integration 테스트로 충분.
- **shadcn Tabs → `@radix-ui/react-tabs` swap** — PR #12 carry-over. 5 탭 deep-link 회귀 위험 ↑ → 별도 PR 에서 시나리오별 e2e 회귀 동반.
- **`.claude/settings.json` push allow 정식 commit** — 만약 팀 합의되면 별도 chore commit 으로 등재 (현재는 working-tree only).

### security-reviewer 누적 권고 (별도 PR)
- **bandit / semgrep / gitleaks / pip-audit GitHub Actions 잡 추가** — PR #10/#11/#12/#13 + chore PR #3 reviewer 누적 요청. CI 자동 정적 스캔 도입.
- **CSP 도입** — `/docs` Swagger UI 의 인라인 스크립트 호환 (per-route nonce 또는 Swagger UI 교체). chore PR #3 의 `SecurityHeadersMiddleware` 를 base 로 확장.

### PR #11 carry-over (미해결)
- **byte-stable ETag for vulnerability_findings** — JS `Date.toISOString()` ms 절단 회귀. 별도 row-version (BIGINT) 컬럼 + 마이그레이션. Schema migration 필요.
- **Phase 8 hardening — `analysis_justification` PII guidance** (PR #11 Low #4). doc-writer + regex secret reject.
- **server-side references URL scheme allow-list** (PR #11 Info #2).
- **`audit_logs` lookup defense-in-depth team filter** (PR #11 Info #3).

### Phase 8 hardening
- **Phase 8 audit listener INSERT-PK 버그** — PR #11 review. 본 PR read-only 표면 영향 0.
- (chore PR #2 carry-over) cdxgen-plugins-bin 카브, Dockerfile.worker base digest pin, Worker container `USER` 지시문, NodeSource signed-by deb, cdxgen `npm audit signatures`.

### Phase 3+ (잠재적 PR #14 — 데이터 채움)
- **scan pipeline 의 obligation 자동 채움** — ORT rule pack 또는 SPDX exception ingestion 으로 obligation 자동 시드. PR #13 은 카탈로그 surface 만, 데이터 파이프라인 미적용.

### v1 carry-over backlog
- **PR #10 의 security-reviewer Medium #1 (raw_data redaction)** — `mask_pii` 헬퍼.
- **PR #10 backlog Low #1 (severity / license_category enum router-level 검증)** — 일부 도메인 미해결.
- **PR #9 follow-up backlog 7개 / PR #8 follow-up backlog 6개 / python-jose → PyJWT / 야간 Trivy soft-fail 잡** — 기존 backlog 유지.

### DB 인덱스 follow-up (db-designer measure-first)
- **`audit_logs (target_table, target_id, created_at)` 복합 인덱스** — 50k+ rows 도달 시.
- **`license_findings (scan_id, license_id) INCLUDE (component_version_id)` partial composite** — 50k+ findings/scan 도달 시 detail + NOTICE 가속.
- **`vulnerability_findings (scan_id, severity_rank, cvss_score DESC)` partial index** — 정렬 hot path 일 때만.
- **NOTICE materialized view per-scan** — Q2 p95 > 1s 일 때만.

### 운영 / 환경
- **postgres 컨테이너 disk-full restart loop** — PR #11/#12/#13/chore #3 네 세션 연속 동일. `docker system prune -a -f --volumes` 또는 디스크 확장 필요.

## 5. 다음 세션 시작 지시문

### 옵션 A — Phase 4 — 알림 시스템 (이메일 SMTP + Slack/Teams Webhook)

```
Phase 4 — 알림 시스템.

main HEAD = chore PR #3 merge commit. Phase 3 (Project Detail Overview/Components/Vulnerabilities/Licenses/Obligations) + chore PR #3 hardening 완료.

이번 세션 = docs/v2-execution-plan.md §3 Phase 4 — 알림 (이메일 + Slack/Teams Webhook + 알림 센터 UI + per-team channel 설정).

직전 핸드오프(반드시 시작 시 읽기):
  - docs/sessions/2026-05-07-chore-pr3-hardening.md — chore PR #3 의 hardening 묶음 (size cap / nosniff / rate-limit / RFC 6266 / authz helper / sql_safety) + 부분 마이그레이션 정책.
  - docs/sessions/2026-05-07-phase3-pr13-obligations.md — 직전 직전 phase 컨텍스트.

시작 시 검증:
  CLAUDE.md 의 SMTP / SLACK_WEBHOOK_URL / TEAMS_WEBHOOK_URL 환경변수 placeholder 확인.
  apps/backend/notifications/ 디렉터리 (CLAUDE.md 디렉토리 구조에 명시) 미존재 여부.
  postgres 컨테이너 health (4 세션 연속 disk-full restart loop — `docker system prune -a -f --volumes` 또는 디스크 확장 검토).

작업 내용:
  1. Backend `notifications/` 모듈 — ABC + concrete (SMTP / Slack / Teams). 각 채널 retry/backoff.
  2. Celery task `notifications.dispatch` — 비동기 dispatch + dead-letter queue 처리.
  3. 트리거 hook — scan completed / new CVE / 라이선스 정책 위반 / 빌드 게이트 실패 / 의무사항 미이행 (의무 워크플로 도입 시).
  4. Frontend `/notifications` 페이지 — 알림 센터 (TanStack Query, 가상 스크롤, 필터, mark-as-read).
  5. Admin UI 의 알림 채널 설정 — per-team SMTP/Slack/Teams URL 등록, 테스트 발송.
  6. test-writer + security-reviewer (Producer-Reviewer).
  7. i18n EN/KO.

핵심 라우팅:
  - backend-developer / scan-pipeline-specialist / frontend-dev / i18n-specialist / test-writer / security-reviewer.

설계 제약:
  - PostgreSQL only / Alembic forward-only / 인증 필수 / docker-compose V1 / `os.getenv()` 런타임 호출 / RFC 7807 / structlog JSON.
  - 알림 페이로드는 PII 마스킹 (`mask_pii` 헬퍼) — 사용자 이메일/이름이 raw 로 외부 채널 송신되지 않도록.
  - Webhook URL 은 secrets store (환경변수 또는 admin UI 의 password 필드) — 평문 로깅 금지.

DoD: 4 채널 동작 + 재시도/dead-letter + 알림 센터 + admin 설정. main CI green / 신규 coverage ≥ 80% / security PASS.

세션 종료 시 docs/sessions/2026-05-XX-phase4-notifications.md 를 §7 양식으로 작성.
```

### 옵션 B — chore PR #4 — `assert_team_access` 잔여 마이그레이션 + Tabs swap

```
chore PR #4 — `assert_team_access` 3 모듈 마이그레이션 + shadcn Tabs → radix swap.

main HEAD = chore PR #3 merge commit.

이번 세션 = chore PR #3 deferred follow-up 통합:
  1. `assert_team_access` 잔여 11 사이트 마이그레이션 (project / project_detail / vulnerability).
  2. shadcn Tabs primitive → @radix-ui/react-tabs swap (5 탭 모두 활성).
  3. `.claude/settings.json` push allow 정식 commit (사용자 합의 시).

직전 핸드오프: docs/sessions/2026-05-07-chore-pr3-hardening.md.

시작 시 검증:
  grep -n "log.warning(\"authz.cross_team_attempt\"" apps/backend/services/{project,project_detail,vulnerability}_service.py — 11 사이트 확인.
  apps/frontend/src/components/ui/tabs.tsx 가 shadcn 기본 export 그대로인지.
  package.json 에 `@radix-ui/react-tabs` peer 존재 여부.

작업 내용:
  1. 3 service 모듈 cross-team 가드 11 사이트 → `assert_team_access(...)` (license/obligation 패턴 미러).
     - 각 모듈 import 변경: `from core.authz import assert_team_access` 추가, `_can_access_team` alias 제거.
     - 회귀 테스트: 기존 IDOR integration 테스트가 동일 status + log emit 으로 통과해야 함.
  2. `apps/frontend/src/components/ui/tabs.tsx` 를 radix 기반으로 교체 (shadcn 표준 패턴).
     - `@radix-ui/react-tabs` peer 설치.
     - 5 탭 e2e 시나리오 회귀 (Overview / Components / Vulnerabilities / Licenses / Obligations 모두 deep-link `?tab=...&drawer=...&vuln=...&license=...&obligation=...`).
  3. (옵션) `.claude/settings.json` push allow 를 별도 commit 으로 정식 등재.
  4. test-writer + security-reviewer.

DoD: main CI green / IDOR 회귀 0 / 5 탭 e2e green / Tabs swap UI 회귀 0 / security PASS.

세션 종료 시 docs/sessions/2026-05-XX-chore-pr4-cleanup.md.
```

### 옵션 C — scan pipeline obligation 자동 채움 (잠재적 PR #14)

```
Phase 3+ — scan pipeline obligation auto-population.

main HEAD = chore PR #3 merge commit.

이번 세션 = ORT rule pack 기반 obligation 자동 시드 + scan task 갱신.

직전 핸드오프: docs/sessions/2026-05-07-chore-pr3-hardening.md.

작업 내용:
  1. ORT rule pack 통합 — 라이선스 → 표준 obligation 매핑 (`ort/rules.kts` 확장 또는 별도 catalog YAML).
  2. `tasks/scan_source.py` / `scan_container.py` 의 license_finding 처리 직후 obligation upsert (ON CONFLICT DO NOTHING, `(license_id, kind)` UNIQUE 멱등).
  3. obligation seed catalog — 7 KNOWN_OBLIGATION_KINDS 카테고리별 표준 본문.
  4. 단위 + integration test (실제 ORT 룰 호출 mock).
  5. e2e: scan flow 후 obligations 탭에 자동 채움 검증.
  6. security-reviewer.

DoD: cdxgen 시드된 라이선스가 표준 obligation kind 자동 부여, e2e 시드 CLI `--with-obligations` 가 chore 가 되지 않음 (실제 scan 으로 채워짐).
```
