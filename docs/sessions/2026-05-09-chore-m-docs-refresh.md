# Session Handoff — 2026-05-09 — Chore M (post-GA documentation refresh)

> Post-GA cleanup 세션 1. PRs #28~#33 + v2.0.0 GA에 동행하지 못한 Docusaurus 가이드를 회수.
> 시작 시점: main HEAD = `9816f21`. 종료 시점: main HEAD = `5b3b48d`.

## 1. 처리한 PR

| Chore | PR | 머지 commit | 비고 |
|-------|-----|-------------|------|
| M | #34 | `5b3b48d` | post-GA documentation refresh — EN 8 신규 + KO 13 미러 + 3 갱신 |

## 2. 작업 내역

### EN — 8 신규 + 3 갱신

신규:
- `docs-site/docs/user-guide/{auth-and-profile,notifications,integrations}.md` — PR #28/#32/#33 신규 기능 사용자 가이드 (각 600~900 단어 + 스크린샷 placeholder)
- `docs-site/docs/contributor-guide/{getting-started,coding-standards,testing-guide,agent-team}.md` — 신규 카테고리. 로컬 셋업 / TypeScript strict / Pydantic v2 / Alembic forward-only / RFC 7807 / structlog JSON / i18n 키 패턴 / Playwright 하네스 / 적대적 입력 parametrize 의무 / 9개 에이전트 + Producer-Reviewer 트리거 조건
- `docs-site/docs/release-notes/v2.0.0.md` — CHANGELOG [2.0.0] 미러 + Upgrading from rc.1 / Known issues 섹션

갱신:
- `docs-site/docs/admin-guide/backup-and-restore.md` — `## Manual backup with the admin UI` 섹션 (Trigger / list / Upload+Restore typing-gate / 10 GB cap)
- `docs-site/docs/admin-guide/api-keys.md` — `## Manage with the /integrations UI` lead 섹션 (사용자 perspective + cross-link)
- `docs-site/docs/intro.md` — GA tip admonition + What's new in 2.0.0 섹션

### KO — 13 신규 + 2 갱신

신규 (모두 `docs-site/i18n/ko/docusaurus-plugin-content-docs/current/` 하위):
- 위 EN 신규 8개 + `admin-guide/api-keys.md` (KO 부재) + `ci-integration/{github-actions,gitlab-ci,jenkins,webhooks}.md` (KO 부재 4개) + `reference/{architecture,env-variables,api-overview}.md` (KO 부재 3개)

갱신:
- `admin-guide/backup-and-restore.md` (UI 섹션 한국어 미러)
- `intro.md` (GA tip + What's new 한국어)

### 인프라

- `docs/installation/gcp-deploy{,.ko}.md` → `docs-site/docs/installation/` (EN) + `docs-site/i18n/ko/.../installation/` (KO) — 기존엔 docs-site 외부에 있어 게시 안 됨
- `docs-site/sidebars.ts` — 3개 user-guide 항목 + Contributor guide 카테고리 + Release notes 카테고리 + Installation 에 gcp-deploy 등록
- `.gitignore` — `docs-site/.docusaurus/` (build cache) + `apps/frontend/@/` (shadcn artifact) 제외
- `docs-site/i18n/ko/.../{user-guide,admin-guide}/img` 심볼릭 링크 — EN 자산 공유

## 3. 측정 가능한 결과

- **신규/갱신 가이드**: EN 11개 + KO 15개 = 총 26개 문서 변경
- **빌드**: `npm run build` EN/KO 양쪽 SUCCESS (사전 존재하던 글로벌 navbar broken-link 경고는 본 PR이 도입한 것이 아님)
- **CI**: 11/11 체크 모두 green (bandit / semgrep / lint backend+frontend / test backend+frontend / typecheck backend+frontend / image-scan / e2e / frontend-bundle-audit)

## 4. 자율 실행 중 발생한 이슈와 처리

| 이슈 | 처리 |
|------|------|
| Local Node 25 + Docusaurus 3.6.3 webpack 호환 문제로 doc-writer 에이전트가 임시로 `webpack@5.97.1` 핀을 시도 (package.json은 revert) | `package-lock.json`이 staged 상태로 남아있어 unstage. 18537 라인 lock 파일을 commit에서 제외. CI runner는 Node 20 + 기본 webpack 범위로 정상 빌드 |
| Docusaurus 3.6.3은 누락 이미지에 대해 build를 fail | 1×1 transparent stub PNG 10개를 placeholder 자리에 생성. 마크다운 ref는 안정 — 실제 스크린샷은 후속 시점 추가 |
| `docs-site/.docusaurus/` build cache가 untracked로 남음 | `.gitignore`에 추가 |

## 5. backlog 갱신

`docs/chore-backlog.md`:
- ~~Chore M~~ ✅ PR #34 (2026-05-09) — 처리 결과 요약 추가

## 6. 다음 세션

`docs/sessions/_next-session-prompt-post-ga-cleanup.md` §3 우선순위 표대로 **세션 2 — Chore L2 (Webhook fixture HMAC drift fix)** 진행.

작업 범위: `apps/backend/tests/integration/test_webhooks_{github,gitlab}.py`의 12 xfail + `test_api_keys_api.py`의 1 xfail 정리. 원인은 webhook fixture의 commit 누락 가능성 (코드 확인 결과 `_make_github_project`는 이미 commit이 있음 — backend-developer 에이전트가 실제 실행해 진단 후 fix).

## 7. follow-ups (별도 chore)

- 10개 placeholder PNG (1×1 transparent stub) → 실제 스크린샷 교체 — UAT 시점에 함께 처리 가능
- 글로벌 navbar broken-link 경고 (`/trustedoss-portal/` 루트 링크 — 모든 페이지에서 발생, 사전 존재) → 별도 chore
