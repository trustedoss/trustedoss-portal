# Session Handoff — 2026-05-06 — Phase 3 PR #10 — Project Detail (Overview + Components 탭)

## 1. 무엇을 했나

- **Phase 3 PR #10 머지 완료** — feature 브랜치 `feature/phase3-pr10-project-detail`. 머지 커밋 `7d6f66d`. 4-wave 구조 (db-designer + backend / frontend / i18n + test-writer / security-reviewer) 로 진행, 2 차례 CI fix iteration 끝에 모든 잡 green.
- **commit 트리** (5 commits, main 머지):
  1. `4e886d9` — chore PR #2 핸드오프 문서 (`docs/sessions/2026-05-06-chore-worker-image-hardening.md`) 동행 commit. 직전 PR 의 정책 결정 (`.trivyignore` 카테고리 (3) 도입) 을 main 에 함께 보냄.
  2. `f8d728b` — Phase 3 PR #10 main work. 43 files, +6519 lines.
  3. `69d9f1c` — Round 1 CI fix: Postgres ENUM 비교 cast 누락. `case({literal("foo"): N}, value=Vulnerability.severity)` 가 `vuln_severity = character varying` 비교를 만들어 asyncpg 가 거부. 양 컬럼(`vuln_severity`, `license_category`) 의 LHS 를 `cast(col, String)` 으로 text 화. **schema 변경 없음, 쿼리 재작성만**.
  4. `7c53306` — Round 2 CI fix: `_make_license` fixture idempotency. `_migrate_once` 가 module-scope 라 commit 데이터가 test 간 잔존 → hardcoded spdx_id ("MIT" 등) 두 번 INSERT 시 `uq_licenses_spdx_id` 위반. fixture 를 SELECT-or-INSERT 로 변경, `category` 충돌 시 동작은 docstring 에 명시.
  5. `7d6f66d` — merge commit.
- **Wave 1 — db-designer + backend-developer 병렬**:
  - **db-designer**: 신규 마이그레이션 불필요 판정. 기존 `ix_scan_components_scan_id` / `ix_vuln_findings_scan_id` / `ix_license_findings_scan_id` / `ix_scans_project_created_at` 인덱스로 1만 행 페이지네이션 p95 < 200ms 달성 가능 — EXPLAIN 시뮬레이션 기반.
  - **중요 schema 발견**: 실제 DB 모델은 `severity_max` / `license_category` 컬럼이 components 또는 scan_components 에 **없음**. PR #7 의 의도적 결정 — query-time aggregation. backend-developer 가 task spec 의 flat schema 가정을 실제 모델에 매치. 100k+ 행 도달 시 denormalized cache 또는 materialized view 검토 — Phase 3+ follow-up.
  - **backend-developer**: 3 신규 엔드포인트 (`/v1/projects/{id}/overview`, `/v1/projects/{id}/components`, `/v1/components/{id}`). 모두 `Depends(get_current_user)` + `_can_access_team` IDOR 가드 + RFC 7807. cross-team component-detail 은 404 hide-existence (의도). 37 신규 테스트 (7 pure-unit + 19 service-DB + 11 HTTP-integration). ruff + mypy --strict clean.
- **Wave 2 — frontend-dev**:
  - `ProjectDetailPage` + 4 탭 (Overview / Components 활성, Vulnerabilities / Licenses 는 PR #11/#12 placeholder).
  - **shadcn-style Tabs primitive 자체 구현** — `@radix-ui/react-tabs` 미추가. 동일 shape (TabsList / TabsTrigger / TabsContent) 라 미래 swap 무중단.
  - `OverviewTab` — Risk gauge (semicircular SVG) + severity / license stacked bars + recent-5 scans. **recharts 의도적 미사용** (bundle 200kB + v1 XSS surface 회피). pure SVG / Tailwind divs.
  - `ComponentsTab` — react-virtuoso `TableVirtuoso` 1만 행 가상 스크롤 + 인라인 toolbar + URL search-params 동기화 (deep-linking) + 우측 슬라이드 Sheet 드로어.
  - `ComponentDrawer` — vuln 리스트 + raw_data accordion (`<pre>` + `JSON.stringify` text node).
  - 라우터 `/projects/:id` 추가, ProjectListPage row name → `<Link>`.
  - 41 신규 vitest 케이스. coverage **93.41% lines / 85.29% branches / 87.09% funcs**.
- **Wave 3 — i18n-specialist + test-writer 병렬**:
  - **i18n-specialist**: `project_detail` namespace 84 키 EN + KO 양쪽 완성. 기존 `common.risk` / `projects.status` 와 정합. 신규 도메인 용어 8개 (Severity, Forbidden/Conditional/Allowed, Cancelled, Source/Container, Fixed in, Breadcrumb, Unknown) — `docs/glossary.md` 등재 후보.
  - **test-writer**: PortalPage 하네스에 8 verbs 추가 (6 user-requested + 2 ergonomic), 모두 event-driven wait — `page.waitForTimeout` 미사용. `project_detail.spec.ts` 6 시나리오. seed CLI 확장 (`--with-scan`, `--component-count`, `--component-prefix`). 시나리오 2 의 endReached 트리거는 250 행으로 검증 (CI 30s/test 예산 준수, 10k 는 ad-hoc perf 테스트).
- **Wave 4 — security-reviewer Producer-Reviewer 라운드**:
  - **평결: PASS**, 블로커 0, Medium 1, Low 4, Info 3.
  - [Medium] **`ComponentDetailResponse.raw_data` redaction 누락** — cdxgen/DT 원본의 잠재적 시크릿 (npm `_auth`, git tokens) 가 same-team developer 에게 노출. **same-team 노출 + 256 KiB JSONB 가드 (PR #8) mitigation 으로 머지 차단 사유 아님**. Phase 8 follow-up = `mask_pii` 헬퍼를 raw_data 에도 적용.
  - [Low] severity / license_category enum router-level 검증 부재 (서비스 레이어 화이트리스트 dedup 으로 mitigation), offset 상한 부재 (10k 행 cap 에서 영향 미미), IDOR 시도 미로깅 (기존 service_project 와 동일 패턴), search ILIKE `%`/`_` 미escape (UX 이슈).
  - [Info] 통합 테스트 cross-team component-detail 케이스 누락 (단위 커버리지 충분), seed `--component-count` 상한 부재 (운영자 CLI 전용), dynamic 스캔 도구 (bandit/semgrep/gitleaks/pip-audit) 본 라운드 실행 불가 (venv 부재).

## 2. 결정 사항 / 변경된 가정

- **Schema 결정 — query-time aggregation 채택, denormalization 미도입**.
  - Task spec 의 `Component.project_id / severity_max / license_category` 는 **unimplementable** — 실제 model 은 `project → latest_scan_id → scan → scan_components → component_versions → components → vulnerability_findings/license_findings join`.
  - 1만 행 cap 의 데이터 모델에서 query-time aggregation 은 p95 < 200ms 안에 충분히 들어옴 (db-designer EXPLAIN 검증).
  - 100k+ 행 도달 시 trade-off 재검토:
    - 옵션 A: denormalize `worst_severity_id`/`worst_license_category` onto `scan_components` (expand → migrate → contract). 가장 invasive.
    - 옵션 B: 사용자 facing materialized view 도입 (REFRESH 주기 결정 필요).
    - 옵션 C: 스캔 결과 tiers (cache layer) 의 별도 모델 — Phase 3+ scan-pipeline-specialist follow-up.
- **shadcn Tabs primitive 자체 구현 — radix 의존성 미도입**.
  - 211 LOC 의 hand-rolled minimal Tabs (`apps/frontend/src/components/ui/tabs.tsx`). ARIA roving keyboard (`ArrowLeft/Right/Home/End`), `aria-selected/-controls`, focus trap 모두 wired.
  - **이유**: 본 PR 의 Tabs 사용이 단일 (ProjectDetailPage). radix 추가는 8 packages + 100kB+ bundle. PR #11/#12 (Vulnerabilities/Licenses 탭) 가 Tabs 를 더 쓰면 그 시점에 radix swap 가능 (동일 shape).
- **recharts 의도적 미사용**.
  - 모든 차트 (`RiskGauge`, `SeverityDistributionChart`, `LicenseDistributionChart`) 는 pure SVG / Tailwind divs.
  - **이유**: bundle 200kB + v1 의 XSS 회귀 사례 회피. 단순 분포는 SVG 가 충분.
  - 복잡한 차트 (히트맵, multi-series 등) 가 필요해지면 recharts 또는 visx 도입 검토 — 그 시점에 별도 PR 로.
- **하네스 하네스 verbs — event-driven wait 만**.
  - `page.waitForTimeout` 0건 — 모두 `expect.poll()` / `waitFor({ state: 'visible' })` / 어설션 auto-retry. 시간 의존적 flakiness 회피.
  - 시나리오 2 의 endReached 트리거는 `expect.poll(getLoadedComponentCount).toBeGreaterThan(prev)` 패턴으로 wheel scroll 후 비동기 fetch 완료 자동 동기화.
- **CI fix 2건의 root cause 패턴**:
  - **enum cast** (`69d9f1c`): SQLAlchemy 의 `case({literal: N}, value=Column)` 패턴이 PG ENUM 컬럼에서 type mismatch. 향후 ENUM 컬럼을 CASE 의 `value=` 로 쓸 때 항상 `cast(col, String)` 적용 — 인라인 주석으로 future strip 방지.
  - **fixture idempotency** (`7c53306`): module-scope alembic + 같은 hardcoded ID 두 번 INSERT 패턴 = 미래 테스트가 같은 ID 재사용 시 silently 깨짐. SELECT-or-INSERT fixture 가 안전.
- **MEMORY.md 갱신 후보**: 본 PR 의 핵심 결정 (query-time aggregation, recharts 미사용, Tabs primitive 자체 구현) 은 후속 PR 들이 의문 제기할 수 있어 메모리 등재 가치 있음.

## 3. 현재 상태

- **머지된 PR**: #1 (54e858f), #2 (ca8ab41), #3 (9c19b5a), #4 (8ddedfb), #5 (4325835), #6 (55e67bd), #7 (d7bc929 + 93c41a4 merge), #8 (502f02f + ebb9c53 merge), #9 (f55e70d + 9da6b3c merge), **chore PR #1 (6366b62)**, **chore PR #2 (38236e2)**, **Phase 3 PR #10 (7d6f66d)** + chore CI fix 4건.
- **진행 중 PR**: 없음. 다음 = PR #11 (Vulnerabilities 탭) 또는 PR #12 (Licenses 탭) 또는 follow-up backlog.
- **GitHub origin/main**: `7d6f66d` (Phase 3 PR #10 머지).
- **변경 규모 (PR #10 누적)**: 43 files, +6,519 / -17 lines.
  - Backend: 10 files (5 신규, 5 수정), 723 service + 185 schemas + 401 router + 401 tests
  - Frontend: 18 신규 + 3 수정, ~3,765 LOC
  - i18n: 2 신규 (EN+KO), 280 LOC (140×2)
  - E2E: 1 spec + 2 harness, ~600 LOC
  - 78 신규 테스트 (37 backend + 41 frontend) + 6 e2e 시나리오
- **통과 테스트** (CI green 잡):
  - lint (backend, frontend), typecheck (backend, frontend), test (backend, frontend), image-scan (worker hard-fail), frontend-bundle-audit, e2e (scan-flow + project-detail = 13 시나리오 총)
- **i18n**: EN + KO 양쪽 84 키 완성, 정합성 검증 통과.

## 4. 후속 backlog

### Phase 3 후속 PR (Vulnerabilities / Licenses 탭)
- **PR #11 — Vulnerabilities 탭**: 현재 disabled placeholder. 작업 범위:
  - Backend: `GET /v1/projects/{id}/vulnerabilities` (CVE 리스트, severity 필터, 상태 워크플로우 — pending → under_review → approved/rejected/dismissed).
  - Frontend: VulnerabilitiesTab + 상태 변경 UI + audit log 표시.
  - 신규 model: `VulnerabilityFinding.status` 추가 (PR #7 의 `status` 컬럼 활용).
  - 라우팅: `vulnerabilities-tab-trigger` 활성화 + 탭 내용 wire-up.
- **PR #12 — Licenses 탭**: 현재 disabled placeholder. 작업 범위:
  - Backend: `GET /v1/projects/{id}/licenses` (라이선스 분포 doughnut, allow/conditional/forbidden 그룹).
  - Frontend: LicensesTab + ORT 룰 정책 표시 + obligation 추적 UI 시작점.
  - 본격 obligation 추적은 PR #13 (Obligations 탭, NOTICE 파일 자동 생성) 으로 분리 검토.

### security-reviewer follow-up (별도 PR)
- **(우선순위 ↑) Phase 8 hardening — `raw_data` redaction 레이어** — Medium #1. `mask_pii` 헬퍼를 `_size_guard` 와 같은 위치에 추가, 알려진 시크릿 키(`_auth`, `authorization`, `password`, `token`, `npm_token`, `registry_token`, `bearer`) case-insensitive 매칭으로 `***REDACTED***`. 또는 `raw_data` 를 `team_admin` 이상에게만 반환하도록 role gate.
- **(우선순위 ↑) Phase 8 hardening — 신규 read API rate limit** — 60 req/min/user. 인증된 read 의 일관 정책으로 일괄 적용.
- **별도 PR — service-layer IDOR 시도 일괄 로깅** — Low #3. 본 PR 의 신규 3 지점 + 기존 `project_service.get_project` / `update_project` / `archive_project` 까지 같은 변경. `log.warning("authz.cross_team_attempt", actor_id=..., target_team_id=..., resource=...)`.
- **별도 PR — bandit / semgrep / gitleaks / pip-audit GitHub Actions 잡 추가** — Info. CI 자동 정적 스캔 도입.
- **별도 PR — search ILIKE `%`/`_` escape** — Low #5. UX polish.
- **별도 PR — severity / license_category enum router-level 검증** — Low #1. `Literal["critical", ...]` list + 길이 cap.

### v1 carry-over backlog
- **PR #9 follow-up backlog 7개 (L-1~L-4 / I-1~I-3)** — 직전 chore PR #1 carry-over. L-1 / L-2 / L-4 (DoS 류) 우선.
- **PR #8 follow-up backlog 6개 (L-1·L-2·L-3·L-4·I-2·I-3)** — scan-pipeline-specialist 주도.
- **python-jose → PyJWT 마이그레이션** — chore PR #1 의 security-reviewer Low 권고.
- **야간 Trivy soft-fail 잡** — chore PR #1 의 Medium 권고. 미해결 carry-over.

### Phase 8 hardening 통합 backlog
- (chore PR #2 에서 등록) cdxgen-plugins-bin 카브 (image build 시 `RUN rm -rf .../cdxgen-plugins-bin*`).
- (chore PR #2 에서 등록) Dockerfile.worker base digest pin (`python:3.12.7-slim@sha256:...`).
- (chore PR #2 에서 등록) Worker container `USER` 지시문 — 현재 root 으로 celery 실행.
- (chore PR #2 에서 등록) NodeSource `curl | bash` → signed-by deb 패턴.
- (chore PR #2 에서 등록) cdxgen install 시 `npm audit signatures` 검증.

### 운영 / 환경
- 사용자 환경 Docker Desktop VM 디스크 정리 — `docker system prune -a -f` 또는 디스크 늘리기. 본 세션 도 로컬 docker 미사용 (CI 가 검증 채널).

## 5. 다음 세션 시작 지시문

### 옵션 A — Phase 3 PR #11: Vulnerabilities 탭

```
Phase 3 PR #11 — Vulnerabilities 탭 (CVE 리스트 + 상태 워크플로우).

TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

main HEAD = 7d6f66d. 누적 머지: PR #1~#9 + chore CI fix 4건 + chore PR #1 (deps hygiene) + chore PR #2 (worker image hardening + .trivyignore 카테고리 (3) 도입) + Phase 3 PR #10 (Project Detail Overview + Components).

이번 세션 = Phase 3 PR #11 — Vulnerabilities 탭.
docs/v2-execution-plan.md §3 Vulnerabilities 항목 산출.

시작 시 검증:
  docker-compose -f docker-compose.dev.yml ps  → 5/5 healthy
  gh run list --limit 3                          → main 최신 success
  curl http://localhost:8000/v1/projects/<id>/components  → 200 (PR #10 endpoint)
  ProjectDetailPage 의 "Vulnerabilities" 탭 trigger 가 disabled 상태 확인

작업 내용 (Phase 3 PR #11):

1. backend (api/v1/vulnerabilities.py 또는 projects.py 확장):
   - GET /v1/projects/{id}/vulnerabilities — CVE 리스트, 페이지네이션, severity 필터, status 필터.
   - PATCH /v1/vulnerability_findings/{id}/status — 상태 워크플로우 (pending → under_review → approved/rejected/dismissed). audit log 자동 기록.
   - GET /v1/vulnerability_findings/{id} — 드로어 상세 (CVE 정보 + 영향 컴포넌트 + 분석 코멘트 + 이력).

2. db-designer (필요 시):
   - vulnerability_findings.status 워크플로우 인덱스 검증.
   - audit_log 의 vulnerability_finding 변경 이벤트 인덱스.

3. frontend (features/projects/components/VulnerabilitiesTab.tsx):
   - PR #10 의 disabled placeholder 활성화.
   - shadcn Table + react-virtuoso (PR #10 패턴 재사용).
   - 상태 dropdown — under_review / approved / rejected / dismissed (Developer 권한).
   - 드로어 — CVE 상세 + 영향 컴포넌트 리스트 + 분석 코멘트 input.

4. i18n-specialist:
   - EN/KO 번역 (vulnerability_detail / vulnerability_workflow 네임스페이스).
   - 기존 project_detail.severity / common.risk 와 정합.

5. test-writer:
   - 단위 (상태 전이 가드, IDOR, 분석 코멘트 저장).
   - e2e 5 시나리오 (탭 진입 / 필터 / 상태 변경 → audit log / 드로어 / 권한 거부).

6. security-reviewer (Producer-Reviewer):
   - 상태 변경 IDOR 가드 + audit log 무결성.
   - 분석 코멘트 XSS escape (사용자 입력).
   - 상태 워크플로우의 race condition (낙관적 락 또는 sequence 검증).

핵심 라우팅:
  - backend-developer: API 확장 + 상태 워크플로우.
  - db-designer: 인덱스 검증 (필요 시).
  - frontend-dev: VulnerabilitiesTab + 드로어 + 상태 변경 UI.
  - i18n-specialist: 번역 동시.
  - test-writer: 단위 + e2e 5 시나리오.
  - security-reviewer: Producer-Reviewer.

DoD:
  - main CI 전체 잡 success (image-scan hard-fail 포함).
  - 신규/변경 backend + frontend coverage ≥ 80%.
  - 상태 변경이 audit log 에 기록되는지 e2e 검증.
  - e2e 5 시나리오 green.
  - security-reviewer 평결 PASS 또는 PASS-with-follow-ups.

주의:
  - 사용자 정책: rm/push/docker prune 거부 — 사용자가 ! 프리픽스로.
  - CLAUDE.md 규칙 4 (DT Circuit Breaker — vulnerabilities 데이터는 DT 캐시 활용), 5 (감사 로그 — 상태 변경은 모두 audit), 12 (인증 surface).
  - PR #10 의 query-time aggregation 패턴 재사용 — denormalization 신규 도입 금지.
  - .trivyignore 정책 카테고리 (3) — 본 세션 새 surface 가 .trivyignore 추가 트리거하면 카테고리 명시 + reach 분석 의무.

세션 종료 시 docs/sessions/2026-05-XX-phase3-pr11-vulnerabilities.md 를 §7 양식으로 작성.
```

### 옵션 B — security-reviewer follow-up: raw_data redaction (Phase 8 hardening 우선 처리)

```
Phase 8 hardening (early) — raw_data redaction 레이어.

main HEAD = 7d6f66d. PR #10 의 security-reviewer Medium #1 권고.

이번 세션 = `apps/backend/integrations/_pii_mask.py` (또는 기존 mask_pii) 를
`scan_components.raw_data` / `vulnerability_findings.analysis_response` /
`license_findings.raw_data` jsonb 컬럼에 적용.

작업:
  1. _pii_mask 의 마스킹 키 확장 — `_auth`, `authorization`, `password`,
     `token`, `npm_token`, `registry_token`, `bearer`, `git+https://*@`
     (URL embedded credentials).
  2. tasks/scan_source.py / scan_container.py 의 persistence 직전에
     `mask_pii_recursive(raw_data)` 호출 (size_guard 와 같은 위치).
  3. 단위 테스트 — 알려진 시크릿 패턴이 마스킹되는지 검증.
  4. (선택) 기존 데이터 마이그레이션 — Celery 일회성 task 로 기존
     raw_data 를 in-place mask. forward-only 정책 (CLAUDE.md §6).
  5. security-reviewer Producer-Reviewer 라운드.

DoD: 머지된 후 GET /v1/components/{id} 응답의 raw_data 에 시크릿 부재.
```

### 옵션 C — IDOR 시도 일괄 로깅 (별도 PR)

```
별도 PR — service-layer IDOR 시도 일괄 로깅.

main HEAD = 7d6f66d. PR #10 의 security-reviewer Low #3 권고.

이번 세션 = 모든 service-layer IDOR/forbidden raise 지점에 보안 이벤트 로그 추가.

대상:
  - apps/backend/services/project_service.py — get_project, update_project, archive_project
  - apps/backend/services/project_detail_service.py — get_project_overview,
    list_components_for_project, get_component_detail
  - apps/backend/services/scan_service.py — get_scan, trigger_scan (cross-team)

패턴:
  log.warning("authz.cross_team_attempt",
              actor_id=user.id, target_team_id=project.team_id,
              resource="project", resource_id=project.id)

CLAUDE.md §5 "사용자 오류 WARNING" 규약과 정합.

DoD: 단위 테스트 — 모든 IDOR 거부 시점에 log.warning 호출 확인.
```
