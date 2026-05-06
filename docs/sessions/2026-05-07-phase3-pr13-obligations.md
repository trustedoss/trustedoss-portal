# Session Handoff — 2026-05-07 — Phase 3 PR #13 — Obligations Tab (read-only catalog + NOTICE generator)

## 1. 무엇을 했나

- **Phase 3 PR #13 commit 완료** — feature 브랜치 `feature/phase3-pr13-obligations`. 4-wave 구조 (db-designer + backend / frontend + i18n / test-writer / security-reviewer) — backend-developer 와 test-writer 에이전트가 limit / 500-error 로 중단되어 메인 세션이 backend 본체 + frontend tests + e2e + harness 직접 작성. **read-only 도메인** — `Obligation` 모델에 status workflow 컬럼 부재 (`id, license_id, kind, text, link, created_at, updated_at`) → PR #12 의 license 패턴 그대로 미러, mutation/transition/audit 0건.
- **사전 schema 확인 — 핸드오프 prompt 가정 검증**:
  - `apps/backend/models/scan.py:712~742` 의 `Obligation` 모델 직접 검사 → status / fulfillment 컬럼 부재 확정. License 1:N Obligation, UNIQUE `(license_id, kind)`, 기존 인덱스 `ix_obligations_license_id` + `ix_obligations_kind` 존재.
  - **결정: read-only catalog 도메인**. PATCH endpoint 0건, transition matrix 0건, `if_match` ETag 0건, audit listener 호출 0건.
  - obligation 채움 로직이 ORT/cdxgen scan task 어디에도 없음 — e2e 가 의미있게 동작하려면 seed CLI 확장 필요 → `--with-obligations` flag 추가 + `_OBLIGATIONS_BY_CATEGORY` 카탈로그 (forbidden 2 / conditional 2 / allowed 2 / unknown 1 = 7 obligation/scan).
- **Wave 1 — db-designer + backend-developer 병렬**:
  - **db-designer** (verification-only): 신규 마이그레이션 0건 판정. 3개 신규 query 패턴 모두 기존 인덱스로 충분.
    - Q1 (list): `ix_license_findings_scan_id` BitmapHeapScan + `licenses` PK hash join + `ix_obligations_license_id` nested loop. ≤10k LF + ≤300 licenses + ≤10 obligations/license 워크로드에서 p95 < 50ms.
    - Q2 (notice): 동일 driver + ComponentVersion / Component PK joins + `array_agg`. p95 < 200ms.
    - Q3 (kind distribution): same path + terminal `GROUP BY o.kind`. p95 < 30ms.
    - Future measure-first 후보: `(scan_id, license_id) INCLUDE (component_version_id)` partial index — 50k+ findings 도달 시. NOTICE 생성 latency > 1s p95 시 materialized view per-scan.
  - **backend-developer** (limit 도달 — 메인 세션 직접 구현): 5 신규/수정 파일.
    - `apps/backend/schemas/obligation_detail.py` (신규, 183 LOC) — Pydantic v2 closed Literal (LicenseCategory 재사용, NoticeFormat, ObligationSortKey) + open `kind: str` (catalog 자유) + `KNOWN_OBLIGATION_KINDS` 7-tuple advisory rank.
    - `apps/backend/services/obligation_service.py` (신규, 530 LOC) — `list_project_obligations` (kind multi + category multi + search 4 컬럼 ILIKE escape + sort 4 + page) returning `(items, distribution, total)`. `get_obligation_detail` (project-scoped URL — `obligation_id + project_id` 조합으로 cross-team existence-hide). `generate_notice` (text/markdown body composer + provenance dict). 도메인 예외 `ObligationError` / `ObligationNotFound` (ProjectError subclass — 자동 RFC 7807 변환).
    - `apps/backend/api/v1/obligations.py` (신규, 270 LOC) — 3 routes: `GET /v1/projects/{id}/obligations`, `GET /v1/projects/{id}/obligations/{obligation_id}`, `GET /v1/projects/{id}/notice` (text/plain + text/markdown + download flag → Content-Disposition: attachment). `_safe_filename_token` 정규식 sanitize (`[^A-Za-z0-9._-]+` → `-`, 빈 결과 "project").
    - `apps/backend/api/v1/__init__.py` + `apps/backend/main.py` — wire-up.
    - `apps/backend/scripts/seed_e2e_user.py` — `--with-obligations` flag 추가 + `_OBLIGATIONS_BY_CATEGORY` 카탈로그 (UNIQUE `(license_id, kind)` 멱등, text ≥ 50자 e2e grep 안전).
    - **PR #11/#12 carry-over 적용**: (1) `_escape_like` cross-import (vulnerability_service 에서, license_service 도 동일), (2) cross-team `log.warning("authz.cross_team_attempt", ...)` 사전 emit (list 403 + detail 404 + notice 403), (3) module-level `log = structlog.get_logger("obligation.service")`, (4) `cast(license.category, String).in_(...)` for ENUM, (5) query-time aggregation only — denormalization 0건, (6) read-only domain — PATCH 0 / transition 0 / audit_log 0.
- **Wave 2 — frontend-dev + i18n-specialist 병렬 (메인 세션 직접 구현)**:
  - 8 신규 frontend 파일 + 1 수정:
    - `obligationsApi.ts` — wire types 미러, `listProjectObligations`, `getObligation`, `fetchProjectNotice` (axios `responseType: "text"` + `transformResponse` identity 로 raw text 보존), `KNOWN_OBLIGATION_KINDS`, X-Notice-* 헤더 partial-parse.
    - 3 hooks: `useObligations.ts` (TanStack Query, `staleTime: 30000`, `keepPreviousData`, sorted-array 캐시 키), `useObligation.ts` (project-scoped key, null disable), `useNotice.ts` (imperative download — Blob + `<a download>` + URL.revokeObjectURL 후처리).
    - `ObligationsTab.tsx` — TableVirtuoso 가상 스크롤 + URL search-params 동기화 (`?obligation=<id>` drawer key — `?drawer`/`?vuln`/`?license` 와 충돌 회피). 컬럼: SPDX / License Name / Category badge / Kind / Affected count. `DistributionStrip` (zero-count kinds 필터링한 chip 들).
    - `ObligationsToolbar.tsx` — search debounce 300ms + kind multi (KNOWN_OBLIGATION_KINDS 7) + category multi (4) + sort (4) + order asc/desc + **NOTICE download 버튼** (toolbar 내부에 배치 — 카탈로그 핵심 deliverable).
    - `ObligationDrawer.tsx` — Sheet 우측 슬라이드. meta (parent license SPDX/name/category badge + kind chip + license_reference_url isSafeUrl 가드) + obligation body (whitespace-pre-wrap React text node) + reference link (isSafeUrl http(s)) + affected components + cross-link → `setSearchParams({tab:"components", drawer:<cv_id>})` 동시에 `?obligation` clear (드로어 자동 닫힘). **`isSafeUrl()` http(s) scheme guard** — `javascript:`/`data:`/`file:` 는 anchor 미생성 plain text fallback (PR #12 패턴).
    - `ProjectDetailPage.tsx` — 5번째 탭 (Obligations) 활성화. `ALLOWED_TABS` 5개로 확장. `setTab` 헬퍼: `?obligation` clear 분기 + `kind` 가 licenses/obligations 두 탭 공유 → 둘 모두 떠날 때만 drop. **shadcn Tabs primitive 유지** — 5 탭 모두 활성 시점이지만 radix swap 은 본 PR scope 외 (별도 chore 권고, scope creep 회피).
  - **i18n-specialist** (메인 세션 직접 구현):
    - `project_detail.obligations.*` namespace EN + KO 양쪽 49 키씩 신규 (264/264 parity 검증, ICU placeholder 정합).
    - 한국어: 한자어 명사형 (`저작자 표시 / 소스 공개 / 카피레프트 / 변경 표시 / 동적 링킹 / 보증 금지 / NOTICE 보존`). 합쇼체 메시지.
    - `tabs_placeholder.licenses` 제거 (PR #12 부터 미사용).
    - `docs/glossary.md` 9 항목 등재: Obligation, 7 obligation kinds, NOTICE file.
- **Wave 3 — test-writer (500 internal error 로 partial — 메인 세션이 보강)**:
  - test-writer 에이전트는 backend pure-unit + integration 2 파일까지 작성 후 41 tool_uses 시점에 500 에러로 중단. 메인 세션이 frontend vitest + e2e + harness verbs 직접 작성.
  - Backend `tests/unit/test_obligation_service.py` — **49 cases** (22 pure-helper 매 PR 실행 + 27 `@pytest.mark.integration` DB-gated): `_normalize_*_filter`, `_order_distribution`, `_safe_filename_token`, `_format_header`, `_render_empty_notice` helper 단위. integration: list happy + page + filter + search + sort 4×2 + distribution + IDOR list/detail/notice + detail-not-visible + notice text/markdown/empty + 422 unsupported.
  - Backend `tests/integration/test_obligations_api.py` — **10 cases**: 401 unauth, 200 happy + empty, multi-value `kind` query, 422 invalid sort, 403 cross-team list, 404 cross-team detail, 404 detail not visible, NOTICE text/plain inline, NOTICE markdown, NOTICE download (Content-Disposition: attachment + filename sanitize). RFC 7807 problem+json 검증, X-Notice-* 헤더 검증.
  - Frontend `ObligationsTab.test.tsx` — **9 cases**: skeleton, empty, rows + summary, distribution chips (zero filter out), RFC 7807 error, kind filter URL sync at offset 0, sort change, URL hydration on mount, row click → drawer.
  - Frontend `ObligationDrawer.test.tsx` — **9 cases**: closed (no fetch), loading, meta + license, **non-http(s) link XSS guard** (`javascript:alert(1)`), null link omit, unknown kind defaultValue fallback, body + reference link + cross-link URL pivot (`?obligation` → `?tab=components&drawer=<cv>`), error.
  - PortalPage 하네스: 5 verbs 추가 (`selectObligationsTab`, `expectObligationsTabReady`, `filterObligationsByKind`, `openObligationDrawer`, `getObligationRowCount`, `downloadNotice`). `downloadNotice` 는 `page.waitForEvent("download")` 래핑 + node:fs/promises 로 body 읽기 → `{filename, body}` 반환. event-driven only.
  - `e2e/obligations.spec.ts` — **4 `@obligations` 시나리오**: S1 탭 + 차트 + 카운트, S2 kind 필터 narrows + URL persists across reload, S3 row → drawer meta + body + URL, S4 NOTICE download → filename `^NOTICE-.+\.txt$` + body 에 `PROJECT_NAME` + `E2E-[A-Z]+-` SPDX prefix.
  - 로컬 검증: backend pure-unit **22/22 pass** (REDIS_URL=localhost — 27 integration skip 로컬 docker 환경 dependent), backend ruff clean, mypy clean (117 source files), frontend lint 0 errors / typecheck clean, **vitest 241/241 pass** (이전 223 → +18 신규), playwright `--list --grep @obligations` 4건 collect.
- **Wave 4 — security-reviewer Producer-Reviewer 라운드**:
  - **평결: PASS-with-follow-ups**, 블로커 0, Critical/High/Medium 0, Low 1, Info 3.
  - bandit 통과 (887 LOC, 0 issues). dangerouslySetInnerHTML 0건. raw_data passthrough 0건. PII/secret 평문 0건.
  - PR #11/#12 carry-over 일관성 검증: auth dependency / 403-vs-404 cross-team / `authz.cross_team_attempt` log emit / `_escape_like` ESCAPE clause / category cast / sort whitelist / RFC 7807 envelope / no audit_log writes — 모두 정합.
  - **[Low #1]** `affected_components` + `obligation.text` 응답 size cap 부재 — Defense-in-depth. `affected_components` 가 unbounded (perm. license + 대규모 monorepo 시 다수 행), `obligation.text` 도 `Text` 타입 무제한. CVSS 3.1 (Low). PR #12 의 Info #1 carry-over 와 동일 패턴 — 별도 follow-up PR.
  - **[Info #1]** `_safe_filename_token` 이 Unicode 전체 ASCII 로 축소 — 보안 OK (CR/LF/quote/backslash 모두 strip), UX 개선용 RFC 6266 `filename*=UTF-8''…` 추가 권고.
  - **[Info #2]** `/notice` endpoint 의 `X-Content-Type-Options: nosniff` 부재 — 글로벌 미들웨어로 적용 권고 (devops-engineer).
  - **[Info #3]** `noticeError.message` JSX text expression — auto-escape 안전 확인용 evidence 만 기록.
  - 추가 권고: semgrep / gitleaks / pip-audit GitHub Actions 잡 도입 (PR #10/#11/#12 reviewer 누적 요청).

## 2. 결정 사항 / 변경된 가정

- **schema 가정 정정 — Obligation 은 read-only catalog**.
  - 핸드오프 prompt 가 status workflow 가능성을 명시하며 schema 우선 확인을 강조했음. 실제 모델 검사 결과 `id, license_id, kind, text, link, created_at, updated_at` 만 존재 — 워크플로 컬럼 부재.
  - 결정: PR #12 의 license 패턴 그대로 미러. mutation 패턴 0건.
- **Detail URL = project-scoped** (`/v1/projects/{project_id}/obligations/{obligation_id}`).
  - obligation 자체는 project-agnostic catalog 이지만, 같은 obligation 이 다른 팀 프로젝트와도 연관될 수 있음. URL 에 project 컨텍스트를 명시해 cross-team 가드를 단순화.
  - 가시성 검사: `obligation.license_id` 가 `project.latest_scan_id` 의 license_findings 에 등장해야만 200; 그렇지 않으면 404 (existence-hide).
- **`obligations.kind` open enum**.
  - DB 컬럼이 `String(64)` (catalog 자유). schema 는 `kind: str` 으로 노출하고 advisory rank `KNOWN_OBLIGATION_KINDS` 7-tuple 만 contract 로 advertise.
  - frontend toolbar 는 KNOWN_OBLIGATION_KINDS 만 dropdown — 미지의 catalog kind 는 row/drawer 에서 raw 그대로 렌더 (i18n `defaultValue` fallback).
  - distribution shape: `dict[str, int]` (Pydantic v2 insertion-order 보장 — known first → unknown alphabetical).
- **NOTICE 파일 endpoint = `text/plain` 직접 반환**.
  - JSON envelope 미사용 (browser download UX 단순화). provenance 는 X-Notice-{Generated-At, License-Count, Obligation-Count} 헤더로 노출.
  - `format=markdown` variant 도 동일 패턴 (text/markdown).
  - `download=true` 시 Content-Disposition: attachment + `_safe_filename_token` 정규식 sanitize 적용 filename.
  - 빈 scan (`latest_scan_id is None`) 도 NOTICE 본문 well-formed — "no scan has been run" 안내.
- **NOTICE 본문 형식**: 라이선스 SPDX 헤더 + Components 리스트 + 라이선스별 obligations (kind / text / Reference link). 라이선스 정렬: `spdx_id NULLS LAST, name asc`. obligation 정렬: `kind asc within license`. obligation 0건 라이선스도 attribution 표시 차원에서 헤더 + `(no obligations recorded)` 라인 출력.
- **5번째 탭 활성화 — `?obligation=<id>` drawer key 충돌 회피**.
  - Components: `?drawer=<cv_id>`, Vulnerabilities: `?vuln=<id>`, Licenses: `?license=<finding_id>`. PR #13 은 `?obligation=<id>` 사용.
  - cross-link (ObligationDrawer → ComponentDrawer) 시 `setSearchParams({tab:"components", drawer:<cv_id>})` — `?obligation` 자동 clear 되어 ObligationDrawer 닫힘.
  - `kind` URL param 은 licenses (declared/concluded/detected) + obligations (catalog 자유) 두 탭에서 공유 — 둘 모두 떠날 때만 drop (deep-link 친화).
- **shadcn Tabs primitive 유지** — 5 탭 모두 활성. PR #12 carry-over 권고 (radix swap) 는 본 PR scope 외 별도 chore 로 분리 (정확히 4→5 탭 전환은 swap 가치 변동 없음).
- **NOTICE 차트 부재** — obligation kind 가 catalog 자유라 LicenseDistributionChart 의 4-fixed-bucket 패턴 부적합. 대신 ObligationsTab 상단에 inline `DistributionStrip` (zero-count 필터링 chip) — 시각적 분포는 충분, recharts 의존 도입 회피.
- **e2e 시드 — `--with-obligations` opt-in flag**.
  - 기존 PR #10/#11 e2e 가 obligation 부재를 가정하므로 default false.
  - PR #13 e2e 만 `componentCount=8 + withObligations=true` 로 8 컴포넌트 × 4 카테고리 라이선스 × 7 obligation 시드 → 모든 시나리오 의미있게 동작.
  - scan task 파이프라인 (cdxgen/ORT) 의 obligation 채움은 본 PR scope 외 — Phase 3+ backlog.
- **MEMORY.md 갱신 후보**:
  - Obligation 도메인 = read-only catalog (status 컬럼 부재). 향후 PR 들이 mutation 패턴 도입 가정 차단.
  - Detail URL = project-scoped 로 catalog 의 cross-team 가드를 단순화하는 패턴 — 향후 catalog 도메인 (조직/팀 정책 등) 도입 시 선례.

## 3. 현재 상태

- **머지된 PR**: #1 (54e858f), #2 (ca8ab41), #3 (9c19b5a), #4 (8ddedfb), #5 (4325835), #6 (55e67bd), #7 (d7bc929 + 93c41a4 merge), #8 (502f02f + ebb9c53 merge), #9 (f55e70d + 9da6b3c merge), chore PR #1 (6366b62), chore PR #2 (38236e2), Phase 3 PR #10 (7d6f66d), Phase 3 PR #11 (e19bd8a), **Phase 3 PR #12 (ac15d6a)**.
- **진행 중 PR**: **#13 — feature/phase3-pr13-obligations**. commit + push + gh pr create 메인 세션 직접 수행 (사용자 정책 2026-05-06: push/PR 직접 수행 허용, force-push/destructive 는 명시 승인).
- **GitHub origin/main**: `ac15d6a` (Phase 3 PR #12 머지) — PR #13 핸드오프는 본 commit.
- **변경 규모 (PR #13)**: 약 22 files, 신규 14 (backend 5 + frontend 8 + tests 4 + harness 0 신규지만 verbs 추가) + 수정 6 (backend wire-up 2 + frontend ProjectDetailPage 1 + locales 2 + glossary 1 + harness 1 + seed.ts 1).
  - Backend 신규: `api/v1/obligations.py`, `services/obligation_service.py`, `schemas/obligation_detail.py`, `tests/unit/test_obligation_service.py`, `tests/integration/test_obligations_api.py`.
  - Frontend 신규: `features/projects/api/obligationsApi.ts`, `useObligations.ts`, `useObligation.ts`, `useNotice.ts`, `components/ObligationsTab.tsx`, `ObligationsToolbar.tsx`, `ObligationDrawer.tsx`, `tests/unit/features/projects/ObligationsTab.test.tsx`, `ObligationDrawer.test.tsx`, `tests/e2e/obligations.spec.ts`.
  - 수정: backend `main.py` + `api/v1/__init__.py` (wire-up), `scripts/seed_e2e_user.py` (`--with-obligations`), frontend `features/projects/ProjectDetailPage.tsx` (5번째 탭 + setTab 분기), `locales/{en,ko}/project_detail.json` (각 49 키), `tests/_harness/PortalPage.ts` (5 verbs), `tests/_harness/seed.ts` (`withObligations` flag), `docs/glossary.md` (9 용어).
- **통과 검증**:
  - `ruff check apps/backend` clean.
  - `mypy apps/backend` clean (117 source files).
  - `npm run lint` 0 errors (14 pre-existing fast-refresh warnings — 본 PR ObligationsToolbar 의 신규 2건 동일 패턴, LicensesToolbar/VulnerabilitiesToolbar 와 정합).
  - `npm run typecheck` clean.
  - `pytest -q tests/unit/test_obligation_service.py -k 'not integration'` **22/22 pass** (REDIS_URL=localhost; 27 integration skip — postgres dependent, CI 가 검증 채널).
  - `npm run test -- --run` (full vitest) **241/241 pass** (이전 223 → +18 신규 ObligationsTab 9 + ObligationDrawer 9).
  - `npx playwright test --list --grep '@obligations'` 4건 collect.
  - bandit 887 LOC clean.
- **i18n**: EN + KO 양쪽 49 키씩 추가, parity 100% (264/264).
- **CI 미실행** — 브랜치 push 대기 (commit 직후 push + gh pr create).
- **로컬 환경**: postgres 컨테이너는 disk-full restart loop (PR #11/#12 에서 carry-over). redis/backend/frontend healthy. CI 가 검증 채널.

## 4. 후속 backlog

### Phase 3 후속 (잠재적 PR #14)
- **scan pipeline 의 obligation 채움** — 현재 ORT/cdxgen scan task 가 obligation row 를 INSERT 하지 않음. 본 PR 은 카탈로그 surface 만 — 데이터 파이프라인 확장은 별도. ORT rule pack 또는 SPDX exception ingestion 으로 자동 시드.
- **obligation 워크플로우** — 만약 향후 사용자 fulfilment 추적 (이행/미이행/예외) 이 필요하면 별도 `obligation_status` 테이블 + transition matrix + audit_log + PATCH endpoint 도입. 본 PR 은 read-only catalog 이므로 전제 변경 시 새 PR.

### security-reviewer follow-up (별도 PR, PR #12 carry-over 통합)
- **(우선순위 ↑) PR #13 Low #1 + PR #12 Info #1 통합 — 응답 payload size cap**:
  - `affected_components` 서버 측 `.limit(500)` + `truncated: bool` 응답 필드 (license_service 의 `_load_affected_components` + obligation_service 의 `_load_affected_components` 둘 다 적용).
  - `obligation.text` 응답 시 `text[:65_536]` clamp (DB Text 타입 무제한 → drawer JSON 부풀림 방지).
  - CVSS 3.1 (Low). Phase 3+ 또는 Phase 8 hardening.
- **(우선순위 ↑) PR #13 Info #2 — `X-Content-Type-Options: nosniff` 글로벌 미들웨어** (devops-engineer 또는 backend-developer). FastAPI 미들웨어로 모든 응답에 적용 + CSP 보강 검토.
- **PR #13 Info #1 — RFC 6266 `filename*=UTF-8''…`** for NOTICE Content-Disposition. 한/일 프로젝트 이름 UX 개선. 보안 영향 없음.
- **`/notice` endpoint rate-limit** — 무거운 read (두 SELECT + array_agg). 5–10/min/user 로 추가 (slowapi `limiter.limit` 데코레이터).
- **shadcn Tabs primitive → `@radix-ui/react-tabs` swap** — 5 탭 모두 활성 시점. PR #12 carry-over. 별도 chore PR.
- **`_escape_like` → `core/sql_safety.py` promote** (PR #12 Info #2 carry-over). vulnerability_service / license_service / obligation_service 3개 모듈이 같은 source 사용. cross-module leading-underscore import 회피.
- **`_authz_deny` shared helper** (PR #11 Low #3 long-form). project_service / project_detail_service / vulnerability_service / license_service / **obligation_service 신규 추가** = 5 모듈 공통 사용. cross-team logging emit + ProjectForbidden / NotFound 일관 raise.
- **bandit / semgrep / gitleaks / pip-audit GitHub Actions 잡 추가** — PR #10/#11/#12/#13 reviewer 누적 요청. CI 자동 정적 스캔 도입.

### PR #11 carry-over (미해결)
- **byte-stable ETag for vulnerability_findings** — JS `Date.toISOString()` ms 절단 회귀 가능성. 별도 row-version (BIGINT) 컬럼 + 마이그레이션. Schema migration 필요.
- **Phase 8 hardening — `analysis_justification` PII guidance** (PR #11 Low #4). doc-writer + regex secret reject.
- **server-side references URL scheme allow-list** (PR #11 Info #2).
- **`audit_logs` lookup defense-in-depth team filter** (PR #11 Info #3).

### Phase 8 audit listener INSERT-PK 버그
- PR #11 review 에서 발견. 본 PR 의 read-only surface 에 영향 0. Phase 8 hardening 우선순위.

### v1 carry-over backlog
- **PR #10 의 security-reviewer Medium #1 (raw_data redaction)** — `mask_pii` 헬퍼.
- **PR #10 backlog Low #1 (severity / license_category enum router-level 검증)** — 일부 도메인 미해결.
- **PR #9 follow-up backlog 7개 / PR #8 follow-up backlog 6개 / python-jose → PyJWT / 야간 Trivy soft-fail 잡** — 기존 backlog 유지.

### Phase 8 hardening 통합 backlog
- (chore PR #2 carry-over) cdxgen-plugins-bin 카브, Dockerfile.worker base digest pin, Worker container `USER` 지시문, NodeSource signed-by deb, cdxgen `npm audit signatures`.

### DB 인덱스 follow-up (db-designer measure-first)
- **`audit_logs (target_table, target_id, created_at)` 복합 인덱스** — 50k+ rows 도달 시.
- **`license_findings (scan_id, license_id) INCLUDE (component_version_id)` partial composite** — 50k+ findings/scan 도달 시 detail + NOTICE 가속.
- **`vulnerability_findings (scan_id, severity_rank, cvss_score DESC)` partial index** — 정렬 hot path 일 때만.
- **NOTICE materialized view per-scan** — Q2 p95 > 1s 일 때만.

### 운영 / 환경
- **postgres 컨테이너 disk-full restart loop** — PR #11/#12/#13 세 세션 연속 동일 issue. `docker system prune -a -f --volumes` 또는 디스크 확장 필요. 다음 세션 시작 시 `docker-compose -f docker-compose.dev.yml ps` 가 5/5 healthy 인지 재확인.

## 5. 다음 세션 시작 지시문

### 옵션 A — chore: 누적 follow-up 일괄 처리 (size cap + nosniff + rate-limit + shared helpers)

```
chore — PR #11/#12/#13 누적 security-reviewer follow-up 일괄 처리.

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = <PR #13 merge commit>. 누적 머지: PR #1~#9 + chore CI fix 4건 + chore PR #1 + chore PR #2 + Phase 3 PR #10/#11/#12/#13.

이번 세션 = 누적 follow-up 일괄 처리. docs/v2-execution-plan.md §3 의 hardening 항목 + Phase 8 백로그 일부.

직전 핸드오프(반드시 시작 시 읽기):
  - docs/sessions/2026-05-07-phase3-pr13-obligations.md — PR #13 의 4-wave + read-only catalog 패턴 + NOTICE generator + size cap Info.
  - docs/sessions/2026-05-06-phase3-pr12-licenses.md — PR #12 carry-over.

시작 시 검증:
  docker-compose -f docker-compose.dev.yml ps  → 5/5 healthy
  gh run list --limit 3                          → main 최신 success
  ProjectDetailPage 의 5 탭 모두 활성 (Overview/Components/Vulnerabilities/Licenses/Obligations)

작업 내용 (chore PR — 보안/성능 hardening 묶음):

1. payload size cap (PR #12 Info #1 + PR #13 Low #1 통합):
   - `services/license_service.py::_load_affected_components` + `services/obligation_service.py::_load_affected_components` 에 `.limit(500)` + `truncated: bool` 응답 필드.
   - `services/obligation_service.py` list/detail 에서 `obligation.text[:65_536]` clamp.
   - 응답 schema 갱신 + 단위 테스트.

2. `X-Content-Type-Options: nosniff` 글로벌 미들웨어 (PR #13 Info #2):
   - `apps/backend/core/middleware.py` 에 신규 `SecurityHeadersMiddleware`.
   - main.py 에 추가. CORS 보다 outer.

3. `/notice` endpoint rate-limit (PR #13 follow-up):
   - `slowapi` `@limiter.limit("10/minute")` per-user.

4. `_escape_like` → `core/sql_safety.py` promote (PR #12 Info #2):
   - 신규 모듈 + vulnerability_service / license_service / obligation_service import 갱신.
   - 단위 테스트 회귀.

5. `_authz_deny` shared helper (PR #11 Low #3):
   - `core/authz.py` 또는 `services/_authz.py` 신규.
   - project_service / project_detail_service / vulnerability_service / license_service / obligation_service 5개 모듈 갱신.

6. RFC 6266 `filename*=UTF-8''…` for NOTICE (PR #13 Info #1, optional 우선순위 낮음).

7. security-reviewer Producer-Reviewer 라운드.

핵심 라우팅:
  - backend-developer: services + middleware.
  - test-writer: 단위 + 회귀.
  - security-reviewer: Producer-Reviewer.

DoD: main CI green, 신규 coverage ≥ 80%, 5 탭 회귀 0, security PASS.

세션 종료 시 docs/sessions/2026-05-XX-chore-pr3-hardening.md 를 §7 양식으로 작성.
```

### 옵션 B — Phase 4 — 알림 시스템 (이메일 SMTP + Slack/Teams Webhook)

```
Phase 4 — 알림 시스템.

main HEAD = <PR #13 merge commit>. Phase 3 (Project Detail Overview/Components/Vulnerabilities/Licenses/Obligations) 완료.

이번 세션 = docs/v2-execution-plan.md §3 Phase 4 — 알림 (이메일 + Slack/Teams Webhook + 알림 센터 UI).

시작 시 검증:
  CLAUDE.md 의 SMTP / SLACK_WEBHOOK_URL / TEAMS_WEBHOOK_URL 환경변수 placeholder 확인.
  apps/backend/notifications/ 디렉터리 (CLAUDE.md 디렉토리 구조에 명시) 미존재 여부.

작업 내용:
  1. Backend `notifications/` 모듈: ABC + concrete (SMTP / Slack / Teams).
  2. Celery task `notifications.dispatch` (비동기, 재시도 백오프).
  3. 트리거 hook: scan completed / new CVE / 라이선스 정책 위반 / 빌드 게이트 실패.
  4. Frontend `/notifications` 페이지 (알림 센터, 필터, mark-as-read).
  5. Admin UI 의 알림 채널 설정 (per-team).
  6. test-writer + security-reviewer.

핵심 라우팅:
  - backend-developer / scan-pipeline-specialist / frontend-dev / i18n-specialist / test-writer / security-reviewer.

DoD: 4 채널 동작 + 재시도 + 알림 센터 + admin 설정.
```

### 옵션 C — scan pipeline 의 obligation 자동 채움 (잠재적 PR #14)

```
Phase 3+ — scan pipeline obligation auto-population.

main HEAD = <PR #13 merge commit>. PR #13 은 obligation read-only surface 만 — scan task 의 obligation 채움 부재.

이번 세션 = ORT rule pack (또는 SPDX exception 카탈로그) 기반 obligation 자동 시드 + scan task 갱신.

작업 내용:
  1. ORT rule pack 통합 — 라이선스 → 표준 obligation 매핑 (`ort/rules.kts` 확장 또는 별도 catalog YAML).
  2. `tasks/scan_source.py` / `scan_container.py` 의 license_finding 처리 직후 obligation upsert (ON CONFLICT DO NOTHING).
  3. 멱등 시드 — UNIQUE `(license_id, kind)` 존중.
  4. 단위 + integration test (실제 ORT 룰 호출 mock).
  5. e2e: scan flow 후 obligations 탭에 자동 채움 검증.
  6. security-reviewer.

DoD: cdxgen 시드된 라이선스가 표준 obligation kind 자동 부여, e2e 시드 CLI `--with-obligations` 가 chore 가 되지 않음 (실제 scan 으로 채워짐).
```
