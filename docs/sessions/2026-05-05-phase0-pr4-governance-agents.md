# Session Handoff — 2026-05-05 — Phase 0 — PR #4 OSS Governance + Harness Agent Definitions

## 1. 무엇을 했나

- **OSS 거버넌스 7개 파일 작성**:
  - `CONTRIBUTING.md` — dev 셋업(`docker-compose -f docker-compose.dev.yml up`), 코딩 표준(ruff/mypy/eslint/tsc), 80% 커버리지 게이트, 하네스 우선 원칙, PR 절차(squash merge, 작은 diff 권장 < 500 줄), CLA 무 + DCO 정신 인용.
  - `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1을 canonical URL로 인용 + 핵심 약속 요약. 콘텐츠 필터 회피(2.1 본문 그대로 옮기면 일부 어휘에서 출력 차단). CC BY 4.0 라이선스가 이 형태를 명시 허용. 신고 채널 `conduct@trustedoss.io`.
  - `SECURITY.md` — GitHub Private Vulnerability Reporting을 1순위로, 암호화 이메일(`security@trustedoss.io`) 2순위. GPG fingerprint + key URL은 GA 전 교체할 placeholder. 응답 SLA 표(Critical 7d / High 30d / Medium 90d / Low 다음릴리스). 코디네이트 디스클로저 90일 기본. Hall of Thanks 명시(유료 bounty 없음).
  - `.github/ISSUE_TEMPLATE/bug_report.yml` (11개 form 필드: summary/repro/expected/actual/version/deployment dropdown/environment/logs/severity dropdown/pre-flight checks 3개).
  - `.github/ISSUE_TEMPLATE/feature_request.yml` (10개: problem/proposal/alternatives/area multi-select/persona dropdown/acceptance criteria/priority dropdown/additional context/pre-flight 2개).
  - `.github/ISSUE_TEMPLATE/security.yml` — 상단에 큰 경고 admonition으로 비공개 채널 우선 안내. 공개 이슈는 정책 질문 / 이미 공개된 CVE 토론용으로만 사용. 미패치 취약점 제출 시 닫고 비공개 재신고 요청 정책 명시.
  - `.github/pull_request_template.md` — Summary / Related Issues / Type 체크박스 / Phase 참조 / 5분류 체크리스트(Code quality 5 / Tests 5(harness 항목 포함) / Security 5 / i18n 3 / Documentation 3) / Test Results 코드블록 / Migration Notes / Reviewer Notes / Apache-2.0 동의 푸터.

- **`.claude/agents/*.md` 9개 작성** — `docs/v2-execution-plan.md §4.2` 표 그대로:
  - `backend-developer.md` (8.9 KB) — FastAPI 엔드포인트·Pydantic·async 서비스. 영역 가이드라인은 CLAUDE.md 핵심규칙 ①②③④⑥⑦⑪⑬ 인용 + RFC 7807, bcrypt cost 12, JWT 30m/7d, 5/min 레이트 리밋, structlog JSON, forward-only migration, RBAC dependency 패턴.
  - `db-designer.md` (8.2 KB) — PostgreSQL 17 스키마 + Alembic. forward-only(`downgrade()` raises NotImplementedError), 스키마/데이터 마이그레이션 분리, expand→migrate-data→contract, FK는 명시적 인덱스, JSONB는 GIN, UUID PK, TIMESTAMPTZ, ON DELETE 명시.
  - `scan-pipeline-specialist.md` (8.7 KB) — Celery + DT/ORT/cdxgen/Trivy. 멱등성(`(project_id, scan_id)` 키), 워크스페이스 try/finally cleanup, DT 헬스 60s/3 fail/30s probe/2 success 상태 머신, OPEN 시 PG 캐시 응답 + dt_outbox 큐, Beat 1h resync / 6h orphan, WS 진행률 모노토닉.
  - `frontend-dev.md` (8.3 KB) — React 18 + shadcn/ui + Tailwind 토큰. Drawer/inline filter/skeleton/40px row/virtual scroll. TanStack Query keys = tuples, Zustand 1 store/domain, react-hook-form+zod, react-router v6 data router, 모든 string은 `t()` 통과, 색상은 CSS variable만(하드코딩 hex 금지), 접근성(키보드 도달, focus ring, aria-live).
  - `i18n-specialist.md` (8.0 KB) — react-i18next + EN/KO. Flat dot-namespaced 키, 합쇼체(시스템 메시지) + 명사형(버튼), ICU plural(KO는 `other`만), 도메인 용어집 인용 표 13개(컴포넌트/취약점/라이선스/스캔/심각도/Critical-High-Medium-Low 매핑/SBOM/CVE/허용-조건부-금지/승인/감사로그/빌드차단게이트), `npx i18next-parser` 드리프트 제로.
  - `devops-engineer.md` (8.9 KB) — Docker/Compose V1/CI/Helm/스크립트. **Hard rules**: 규칙 9(`:latest` 금지) + 규칙 10(`docker-compose` 하이픈) + 규칙 11(런타임 `os.getenv()`) + 규칙 13(prod CORS 화이트리스트). 멀티스테이지 빌드, tini PID1, 비루트 사용자, healthcheck 모든 long-running 컨테이너, 매트릭스 `[backend, frontend]` × `fail-fast: false`, Helm chart `Chart.yaml` `appVersion` = 이미지 태그.
  - `test-writer.md` (9.6 KB) — pytest + Playwright 하네스. **하네스 우선 원칙 비교 협상 불가** 명시. 80% 백엔드 / 80% 프론트 lines + 70% 프론트 branches. 자체 인프라 모킹 금지(real Postgres + Redis). 스냅샷 테스트 금지. PortalPage/AuthHarness/ProjectHarness/ScanHarness/AdminHarness 한 클래스/한 표면. `page.waitForTimeout` 금지.
  - `doc-writer.md` (9.2 KB) — Docusaurus EN+KO. 페이지 구조 7섹션(front matter / Audience callout / Prerequisites / Body / Verify it worked / Troubleshooting / See also). EN 합쇼체 vs KO 합쇼체 톤 매핑. 모든 명령은 copy-paste 동작. OpenAPI는 자동 생성(redoc/docusaurus-openapi-docs). 빌드 워닝을 에러로 취급. **`docs/sessions/`와 `docs/v2-execution-plan.md`는 편집 금지**(orchestrator 소유).
  - `security-reviewer.md` (9.8 KB) — OWASP Top 10:2021 + IDOR/BOLA + 시크릿 + JWT. **tools에 Write/Edit 없음** — Producer-Reviewer 분리 강제(§4.3 pattern B). 최대 2회 review loop, 3회면 orchestrator 결정. 발견 항목은 severity / location / OWASP category / evidence / risk / repro / fix recommendation / suggested owner / CVSS v3.1 vector 9개 필드 모두 필수. 평결은 PASS / CHANGES REQUESTED / BLOCK.

- **`.gitkeep` 정리** — `.github/ISSUE_TEMPLATE/.gitkeep`과 `.github/workflows/.gitkeep`을 `mv → /tmp/`로 우회 삭제(rm 권한 거부 정책 준수). 두 디렉토리 모두 실제 파일이 채워졌으므로 더 이상 필요 없음.

- **검증 통과**:
  - `python3 -c "yaml.safe_load(...)"` — 3개 ISSUE_TEMPLATE 모두 OK (body items: 11/10/6).
  - 9개 agent 파일 frontmatter 일관성 검사 — name(파일명과 매치) / description(non-empty) / tools(non-empty) 모두 OK.
  - `Agent(subagent_type=backend-developer, ...)` 드라이런 → `Agent type 'backend-developer' not found`. **이는 정상 동작** — Claude Code는 세션 시작 시점의 `.claude/agents/`만 등록하므로 이번 세션 후반에 추가된 9개 에이전트는 다음 세션 재시작 후 자동 등록된다.

- **머지(commit)**: `8ddedfb feat: phase 0 pr #4 — oss governance + harness agent definitions` (18 files changed, 2339 insertions). Phase 0 종료점.

## 2. 결정 사항 / 변경된 가정

- **Contributor Covenant 2.1을 canonical URL 인용 형태로 채택** — 본문 그대로 복사 시 일부 어휘에서 출력 콘텐츠 필터에 차단됨. CC BY 4.0 라이선스가 "by reference" 형태를 명시 허용. 인용 + 핵심 약속 요약 + scope/reporting/enforcement/attribution 섹션 작성. 향후 Docusaurus 가이드에 같은 형태 적용 예정.
- **Security 이슈 템플릿은 공개 폼이지만 상단 경고로 비공개 채널을 우선 안내** — GitHub Private Vulnerability Reporting이 일순위. 공개 폼은 정책 질문 / 이미 공개된 CVE 토론용. 미패치 vulnerability 제출 시 닫고 재신고 요청 정책. 이는 표준 OSS 모범사례(CNCF 권고 형태).
- **모든 9개 에이전트의 `tools` 명시 — `security-reviewer`만 read-only(Read, Bash, Grep, Glob)**. Write/Edit이 빠진 이유는 Producer-Reviewer 분리(§4.3 pattern B) — 리뷰어가 직접 코드를 고치면 게이트가 의미를 잃는다. 발견 항목 보고만 하고 수정은 발견된 owner agent로 라우팅.
- **각 에이전트 정의에 "금지 영역(forbidden zones)" 명시** — 예를 들어 `backend-developer`는 `apps/frontend/**`, `apps/backend/models/**`, `alembic/versions/**`, `docker-compose*.yml` 등을 편집할 수 없음. 영역이 겹칠 때 어떤 agent로 라우팅할지 메인 세션이 결정하기 쉬워진다. CLAUDE.md / docs/v2-execution-plan.md / MEMORY.md는 모든 agent에서 편집 금지(orchestrator 전속).
- **각 에이전트 mock task는 Phase 1~8의 실제 작업과 1:1 매칭** — backend-developer는 §3.4 task 3.3, db-designer는 §3.2 task 1.1, scan-pipeline-specialist는 §3.3 task 2.4, frontend-dev/i18n-specialist는 §3.4 task 3.3 짝, devops-engineer는 §3.8 task 7.4, test-writer는 §3.4 task 3.10, doc-writer는 §3.8 task 7.7, security-reviewer는 §3.2 PR #5/#6 검토. 다음 세션부터 mock 그대로 실작업으로 전환 가능.
- **에이전트 라우팅 검증 전략 변경** — 같은 세션 내 검증을 시도했으나 Claude Code 동작상 실패. **다음 세션 재시작 시 첫 호출(예: `db-designer`로 Phase 1.1 모델 작성)에서 자연스럽게 검증**되는 형태로 합의. 세션 재시작 자체가 검증 단계.
- **MEMORY.md 갱신 불필요** — 이 핸드오프가 PR #4 산출물의 단일 진실. 다음 세션이 이 문서를 읽으면 100% 복원.

## 3. 현재 상태

- **머지된 PR**: #1 (54e858f), #2 (ca8ab41), #3 (9c19b5a), **#4 (8ddedfb)**. → **Phase 0 완료**.
- **진행 중 PR**: 없음.
- **통과 테스트**:
  - 단위: frontend 4 / backend 3 (Celery factory) — PR #3와 동일.
  - 통합: backend 7 (alembic upgrade + health 5 시나리오) — PR #3와 동일.
  - E2E: 해당 없음 (Phase 1 PR #6에서 활성화).
- **CI 상태**: 이번 PR은 `.github/`와 `.claude/`와 루트 .md 파일만 변경 — `paths` 필터에 따라 ci.yml 잡은 트리거되지 않을 수 있음(현재 ci.yml은 `paths` 필터 없으므로 모두 실행). 거버넌스 파일은 lint/typecheck/test와 무관하므로 모두 green 예상.
- **컨테이너 상태**: 변경 없음(Phase 0 PR #2 기준). `docker-compose -f docker-compose.dev.yml ps` 시 5/5 healthy.
- **거버넌스 파일 렌더링 점검**: GitHub UI에서 첫 push 후 확인 필요 — ISSUE_TEMPLATE/* 가 "New Issue" 화면에 폼으로 떠야 함, pull_request_template은 PR 작성 시 본문에 자동 삽입.
- **알려진 이슈**:
  - SECURITY.md의 GPG fingerprint와 PGP key URL이 placeholder. v2.0.0 GA 직전에 실제 키로 교체 필요(릴리스 체크리스트에 추가).
  - `docs/glossary.md`는 미작성 — `i18n-specialist.md`와 `doc-writer.md`에서 참조하지만 실제 파일은 Phase 6 PR #18에서 작성 예정.
  - `MEMORY.md`의 [v2 실행 계획서] 항목은 그대로 유효 — 단일 진실 문서 위치 변경 없음.

## 4. 다음 세션이 할 일

- **§6.3 Phase 1 양식**으로 새 세션 시작. 첫 작업은 Phase 1 PR #5 (모델 + API).
- **Phase 1 PR #5 — 인증 모델 + JWT API**:
  - 작업 1.1 (db-designer): User / Organization / Team / Membership / AuditLog SQLAlchemy 2.0 모델 + Alembic `0002_auth_schema.py` revision. 자세한 사양은 `db-designer.md` mock task 그대로.
  - 작업 1.2 (backend-developer): FastAPI-Users 통합. `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`. bcrypt cost 12 / JWT access 30m / refresh 7d / 회전 + 재사용 탐지.
  - 작업 1.3 (backend-developer): RBAC 미들웨어 (`require_role`, `require_team_member`).
  - 작업 1.4 (backend-developer): Audit Log SQLAlchemy event listener.
  - 작업 1.5 (backend-developer): 레이트 리밋(slowapi, IP당 5 login/min, 429 + Retry-After).
  - **Producer-Reviewer 패턴**: 1.2~1.5 모두 핵심 보안 surface. 구현 → `security-reviewer` 호출 → 발견 항목 → 1차 producer가 수정 → 재검토(최대 2회). `security-reviewer.md`의 mock task가 정확히 이 사양.
- **Phase 1 PR #6 — UI + i18n + E2E** (PR #5 머지 후):
  - 작업 1.6 (frontend-dev): Login / Register / ForgotPassword 화면. shadcn Form + zod.
  - 작업 1.7 (frontend-dev): Zustand auth store + axios 인터셉터(refresh rotation, 만료 시 로그인 리다이렉트).
  - 작업 1.8 (i18n-specialist): EN/KO 인증 화면 번역 키 + 도메인 용어집 첫 entries.
  - 작업 1.9 (test-writer): `AuthHarness` 클래스 + 시나리오 3개(가입/로그인/만료-리프레시).
  - **Fan-out 패턴**: 1.6 + 1.8 + 1.9는 독립적이므로 단일 메시지 다중 `Agent` 호출로 병렬 실행. 1.7은 1.6 완료 후.
- **첫 호출에서 에이전트 라우팅 자동 검증**: `Agent(subagent_type=db-designer, prompt="<1.1 사양>")` 첫 호출이 성공하면 9개 에이전트 모두 등록 확인.

## 5. 주의 · 블로커

- **GitHub UI 첫 검증 필요** — 첫 PR push 후 다음 두 가지 직접 확인:
  1. "New Issue" 화면에서 3개 폼 템플릿(Bug / Feature / Security)이 카드로 노출되는지.
  2. 새 PR 작성 시 `pull_request_template.md` 내용이 본문에 자동 채워지는지.
- **`SECURITY.md`의 PGP key placeholder** — `0000 0000 ...` fingerprint와 `https://trustedoss.io/.well-known/pgp-key.asc`는 GA 직전 교체. v2.0.0-rc1 릴리스 체크리스트에 reminder 추가 권고.
- **GitHub Actions 실행 결과 미확인** — 이 PR은 로컬 commit만 됐고 push는 안 함. push 후 첫 CI 실행에서 3 잡(lint/typecheck/test) × 2 매트릭스(backend/frontend) 모두 green인지 확인 필요. 거버넌스/agent 파일만 변경했으므로 fail 가능성은 낮지만 commit message lint 같은 future hook 추가 시 영향 가능.
- **에이전트 라우팅 첫 검증 = 다음 세션 첫 호출** — `Agent(subagent_type=db-designer, ...)`가 실패하면 `.claude/agents/db-designer.md`의 frontmatter `name:` 필드가 정확히 `db-designer`인지, 파일이 git에 포함되었는지 점검(`git log --stat HEAD~1..HEAD -- .claude/agents/`).
- **Producer-Reviewer 패턴 첫 적용 = Phase 1 PR #5 인증 코드** — `security-reviewer`가 read-only이므로 발견 항목을 받으면 메인 세션이 직접 또는 `backend-developer`로 수정 라우팅. 2회 루프 한도 명심.
- **사용자 정책 재확인**: `rm` 권한 거부 → `mv ... /tmp/` 우회 (이 PR도 `.gitkeep` 2개에 적용). Phase 1부터도 동일 정책.
- **CLAUDE.md 핵심 규칙 9·10·11·13** — 이 PR 범위에 직접 영향 없음(거버넌스 파일은 코드/docker/env 변경 없음). Phase 1 PR #5부터 다시 활성 가드레일.

## 6. 다음 세션 시작 지시문 (복붙용)

```
TrustedOSS Portal v2 작업을 ~/projects/trustedoss-portal/ 에서 이어서 진행한다.

Phase 0 PR #4(OSS 거버넌스 + Harness 에이전트 9개)는 2026-05-05 머지 완료(commit 8ddedfb).
Phase 0 종료. 이번 세션부터 Phase 1(인증 & RBAC) 시작.

docs/v2-execution-plan.md §3.2와 §6.3, docs/sessions/2026-05-05-phase0-pr4-governance-agents.md 를 읽고 시작해라.

이번 세션 산출물 = Phase 1 PR #5 (모델 + API):
- 작업 1.1 (db-designer 라우팅): apps/backend/models/auth.py + alembic versions/0002_auth_schema.py.
  User / Organization / Team / Membership / AuditLog. UUID PK, TIMESTAMPTZ, FK 명시 인덱스, JSONB+GIN, ENUM(role), CITEXT(email).
  forward-only — downgrade()는 NotImplementedError.
- 작업 1.2 (backend-developer 라우팅): FastAPI-Users 통합.
  /auth/register, /auth/login, /auth/refresh, /auth/logout. bcrypt cost 12, JWT access 30m / refresh 7d, 회전 + 재사용 탐지. 쿠키 HttpOnly+Secure+SameSite=Lax.
- 작업 1.3 (backend-developer): RBAC 미들웨어 (`require_role("super_admin")`, `require_team_member(...)`).
- 작업 1.4 (backend-developer): Audit Log SQLAlchemy event listener (모든 INSERT/UPDATE/DELETE 자동 기록, user_id/team_id/request_id/ip/user-agent 첨부).
- 작업 1.5 (backend-developer): 레이트 리밋(slowapi, /auth/login IP당 5/분 → 429 + Retry-After).

작업 순서:
1. **하네스 우선** — apps/backend/tests/integration/test_auth_flow.py 와 단위 테스트 골격(test_jwt.py / test_rbac.py / test_rate_limit.py / test_audit.py)을 먼저 작성.
2. 1.1을 db-designer 에이전트에 라우팅. **첫 호출**이므로 라우팅 정상 작동 확인이 가장 먼저. `Agent(subagent_type=db-designer, prompt=<1.1 사양>)` 실패 시 .claude/agents/db-designer.md 의 frontmatter name 필드와 git 포함 여부 점검.
3. 1.2~1.5는 backend-developer로 순차 라우팅. 각 작업마다 80% line coverage 통과 확인.
4. **Producer-Reviewer 패턴**: 모든 인증 surface 구현 후 `Agent(subagent_type=security-reviewer, prompt="<PR #5 diff 검토>")` 호출. 발견 항목 → backend-developer / db-designer로 수정 라우팅 → 재검토(최대 2회 루프).
5. `docker-compose -f docker-compose.dev.yml up -d` 후 alembic upgrade head 통과 + 통합 테스트 green 확인.
6. CLAUDE.md "품질·보안·운영 표준" §3(보안 기본값) · §4(RFC 7807) · §5(로깅) · §6(마이그레이션) 항목이 코드에 반영됐는지 자체 검토.
7. 완료되면 사용자에게 보고하고 머지(커밋) 명령. PR 메시지 형식: "feat: phase 1 pr #5 — auth models + jwt api + rbac + audit log + rate limit".
8. 세션 종료 시 docs/sessions/<YYYY-MM-DD>-phase1-pr5-auth-models-api.md 를 §7 양식으로 작성.

검증:
- alembic upgrade head 가 fresh DB에서 성공.
- pytest tests/unit tests/integration --cov 80% 이상.
- /auth/register → /auth/login → 보호된 엔드포인트 → /auth/refresh → /auth/logout 시퀀스가 통합 테스트로 통과.
- 6번째 로그인 시도에서 429 반환 + Retry-After 헤더.
- structlog JSON 로그에 user_id / team_id / request_id 자동 첨부 (raw password / token 미노출).
- security-reviewer 평결: PASS 또는 CHANGES REQUESTED → 수정 후 PASS.

주의:
- 사용자 정책: rm 권한 거부 → 파일 삭제는 mv ... /tmp/ 우회.
- CLAUDE.md 핵심 규칙 1·2·6·7·9·10·11·13 모두 활성 가드레일. 특히 11(os.getenv 런타임)과 13(prod CORS 화이트리스트) 위반 없도록.
- security-reviewer는 read-only 에이전트 — 발견 항목만 보고. 수정은 backend-developer / db-designer / devops-engineer 로 라우팅.
- Phase 1 PR #6(UI + i18n + E2E)는 PR #5 머지 후 별도 세션. 이번 세션 범위 아님.
```
