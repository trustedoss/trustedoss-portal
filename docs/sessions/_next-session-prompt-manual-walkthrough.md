# 다음 세션 시작 prompt — Manual Walkthrough Verification (사용자/관리자 매뉴얼 검증)

> v2.0.0 GA + post-GA cleanup (Chore M~P) 완료 후속.
> 사용자/관리자 매뉴얼대로 시스템이 실제 동작하는지 페르소나별로 검증하고, 매뉴얼 또는 시스템의 drift를 정정한다.
> 본 파일을 새 세션 첫 메시지에 그대로 붙여넣으면 정확한 컨텍스트로 시작.
> **세션 중간에 끊겨도 본 파일 + main HEAD + chore-backlog.md 만으로 이어 진행 가능.**

---

TrustedOSS Portal v2 작업을 `~/projects/trustedoss-portal/` 에서 이어서 진행한다.

## 0. 현재 상태 (2026-05-09 기준)

- main HEAD = `fe9386a` (post-GA cleanup 6-session summary)
- 누적 머지: PR #1 ~ #39 + tag `v2.0.0`
- post-GA cleanup 6 세션 완료. 본 prompt 의 세션 1~6 은 **매뉴얼 검증** 단계.

```bash
git log --oneline -3
# fe9386a docs: post-GA cleanup 6-session summary
# 5cdebbc chore(worker): refresh base image deps + Trivy HIGH hard-fail (Chore P) (#39)
# 9f5a216 test: install/restore UAT + shellcheck CI gate (Chore E) (#38)
```

직전 세션 통합 핸드오프: `docs/sessions/2026-05-09-post-ga-cleanup-complete.md`

## 1. 단일 진실

- `docs-site/docs/user-guide/*.md` — 9 페이지 (사용자 매뉴얼, EN)
- `docs-site/docs/admin-guide/*.md` — 6 페이지 (관리자 매뉴얼, EN)
- `docs-site/i18n/ko/docusaurus-plugin-content-docs/current/{user,admin}-guide/*.md` — KO 미러 (본 작업은 EN/KO 모두 검증)
- `docs/sessions/2026-05-08-uat-manual-test-scenarios.md` + `2026-05-09-uat-v2.0.0-scenarios.md` — 기존 27 시나리오 / 44 sub-scenario
- `apps/frontend/tests/_harness/` — Playwright 하네스 (PortalPage + 9 도메인 하네스: AdminUsers/Teams/DT/Scans/Disk/Audit/Health/auth/integrations/seed)
- `apps/frontend/tests/e2e/*.spec.ts` — 기존 E2E 9 spec / 39 시나리오
- `CLAUDE.md` — 핵심 규칙 + 품질·보안 표준
- 본 파일 — **세션 1~6 의 단일 진실**. 각 세션 prompt 가 self-contained.

## 2. 시작 시 검증 (반드시)

```bash
# 환경 + 진행 상태 확인
git status                                            # working tree clean (untracked는 무시)
git checkout main && git pull --ff-only               # 최신 반영
git log --oneline -3                                  # 최신 commit 확인
gh run list --branch main --limit 3                   # main CI 상태

# 매뉴얼 인벤토리
ls docs-site/docs/user-guide/                         # 9 페이지
ls docs-site/docs/admin-guide/                        # 6 페이지

# 하네스 + E2E 인벤토리
ls apps/frontend/tests/_harness/                      # PortalPage + 9 하네스
ls apps/frontend/tests/e2e/                           # 9 spec

# dev stack 가용성 확인 (이미 떠있을 수 있음)
docker-compose -f docker-compose.dev.yml ps           # postgres + redis + backend + frontend + worker + beat
```

main 의 untracked 잔여 (무시):
- `.claude/scheduled_tasks.lock`
- `apps/frontend/@/` (artifact 폴더, .gitignore 처리됨)
- `docs/review-binaryanalysis-ng.md`
- `docs/sessions/_next-session-prompt-phase4-pr15-plus-chore-pr9.md` (구 prompt)

## 3. 진행 우선순위 (전체 상)

| 세션 | Phase | 작업 | PR 묶음 | 추정 |
|------|-------|------|---------|------|
| 1 | 1 | Coverage matrix 작성 (매뉴얼 단계 분해 + 자동화 분류) | 1 PR (`chore/manual-coverage-matrix`) | 1 세션 |
| 2 | 2 | User persona walkthrough — Developer 9 페이지 | 1~3 PR (매뉴얼 fix + 시스템 버그 fix) | 1~1.5 세션 |
| 3 | 3 | Admin persona walkthrough — Super Admin 6 페이지 | 1~3 PR | 1 세션 |
| 4 | 4 | Triage — 매뉴얼 fix 통합 + 시스템 버그 issue | 영역별 PR 분리 | 0.5~1 세션 |
| 5 | 5 | manual-aligned E2E 시나리오 추가 (Playwright 하네스 확장) | 1 PR (`chore/manual-aligned-e2e`) | 1~1.5 세션 |
| 6 | 6 | CI 게이트 통합 (`e2e (scan-flow)` 또는 신규 잡) | 1 PR (`chore/manual-aligned-ci-gate`) | 0.5 세션 |

**총합 ~5~6.5 세션.** 각 세션은 독립 PR. 매뉴얼 fix는 영역별 (user/admin) 분리, 시스템 버그 fix는 severity별 또는 묶음.

## 4. 핵심 결정 (직전 계획 세션 합의)

본 작업 진행 시 다음 5개 결정을 적용한다:

1. **Matrix 먼저** — Phase 1 (1 세션) 후 옵션 D (수동+자동 하이브리드) 비율 미세 조정
2. **에이전트가 Playwright headed mode로 자동 실행** — 자동화 불가 영역(외부 OAuth 동의 / SMTP 수신함 / sudo)만 사람 백업
3. **destructive flow는 dev compose 직접 + backup 안전망** — 시작 직전 `bash scripts/backup.sh` 1회로 snapshot 확보. `BACKUP_DIR=backups/walkthrough/` 격리
4. **스크린샷 캡처는 자동화하되 실제 매뉴얼 PNG 교체는 별도 chore** — 본 작업의 부산물로 `docs/sessions/walkthrough-screenshots/` 자동 저장. 별도 후속 chore에서 placeholder 교체
5. **결과물 1 chore = 1 PR 분리** — matrix → user fix → admin fix → bug fix → E2E → CI 6개 PR

---

## 세션 1 — Phase 1: Coverage matrix

**브랜치**: `chore/manual-coverage-matrix`

**자율 실행 프로토콜 그대로 따른다** (`docs/autonomous-execution-plan.md` §"자율 실행 프로토콜").

### 1.1 작업 범위

각 매뉴얼 페이지를 한 줄씩 읽으며 다음 metadata 추출:

| 컬럼 | 의미 |
|------|------|
| 페이지 | 매뉴얼 파일 경로 |
| 단계 ID | `<page>-<section>-<step>` (예: `auth-and-profile-1-1`) |
| 페르소나 | Developer / Super Admin / Anonymous |
| 단계 본문 | 매뉴얼이 사용자에게 시키는 명령어 / 클릭 / 탐색 |
| 기대 결과 | 매뉴얼이 약속하는 응답 / 화면 변화 |
| 자동화 가능성 | A (Playwright 가능) / B (외부 통합 필요) / C (시각/Copy 검증) / D (수동) |
| 기존 E2E 가드 | 해당 단계가 이미 회귀 가드 있는지 (`apps/frontend/tests/e2e/<spec>.spec.ts:<line>`) |
| 비고 | 알려진 drift 후보 / 의존성 |

### 1.2 산출물

`docs/sessions/2026-05-XX-manual-coverage-matrix.md` (NEW):

```markdown
# Manual coverage matrix — TrustedOSS Portal v2.0.0

> 작성일: 2026-05-XX
> 대상: 사용자 매뉴얼 9 페이지 + 관리자 매뉴얼 6 페이지
> 목적: 매뉴얼 walkthrough 자동화 비율 결정 + 후속 세션 우선순위

## 사용자 매뉴얼 (Developer 페르소나)

### user-guide/projects.md
| 단계 ID | 본문 | 기대 결과 | 분류 | 기존 E2E |
|---------|------|----------|------|----------|
| projects-1-1 | `/projects` 접속 | 3 프로젝트 카드 표시 | A | `project_detail.spec.ts:23` |
| ... |

### user-guide/auth-and-profile.md
| ... |

(... 9 페이지 모두)

## 관리자 매뉴얼 (Super Admin 페르소나)

### admin-guide/users-and-teams.md
(... 6 페이지 모두)

## 분류 통계
- Total 단계 수: ~150~200 추정
- A (Playwright 자동): X%
- B (외부 통합): Y%
- C (시각/Copy): Z%
- D (수동): W%
- 기존 E2E 가드 보유: V%
- 신규 E2E 추가 권고: U%

## 자동화 비율 권고
- Phase 2/3 (walkthrough)에서 자동 vs 수동 분리 기준
- Phase 5 (E2E 추가) 우선순위 영역
```

### 1.3 작업 흐름

1. `docs-site/docs/user-guide/projects.md`부터 시작해 9 페이지 순서대로 매뉴얼을 읽는다
2. 각 numbered step / `**기대 결과**` bullet을 추출
3. 분류 + 기존 E2E grep 매칭
4. 매뉴얼 자체에 명백한 오류 발견 시 **matrix에 ⚠ 표시만** — 본 phase는 수정 X (Phase 4에서 일괄)

### 1.4 PR + 머지

```bash
git checkout -b chore/manual-coverage-matrix
# (직접 작성 또는 doc-writer 에이전트 위임)
git add docs/sessions/2026-05-XX-manual-coverage-matrix.md docs/chore-backlog.md
git commit -m "docs: manual coverage matrix for v2.0.0 walkthrough verification"
git push -u origin chore/manual-coverage-matrix
gh pr create --title "docs: manual coverage matrix (Manual Walkthrough Phase 1)" --body "..."
```

CI는 lint/test/SAST 모두 docs-only 영향 없음. 1차 푸시 후 일반 절차로 머지.

### 1.5 세션 종료 시

`docs/sessions/2026-05-XX-phase1-coverage-matrix.md` 핸드오프 작성. backlog에 신규 항목 등재:

```markdown
### Manual Walkthrough — Phase 1 ~ 6 (사용자/관리자 매뉴얼 검증)
**우선순위**: post-GA 운영 준비
**시작 prompt**: `docs/sessions/_next-session-prompt-manual-walkthrough.md`
**현재 상태**: Phase 1 ✅ → Phase 2 진행 예정
```

---

## 세션 2 — Phase 2: User persona walkthrough (Developer)

**브랜치**: `chore/user-guide-walkthrough` (matrix 산출물에 따라 1~3개 PR로 분할 가능)

### 2.1 사전 준비

```bash
# dev stack 기동 (이미 떠있으면 재시드만)
docker-compose -f docker-compose.dev.yml up -d
# seed 데이터 확인 — Developer (`dev@trustedoss.dev` / `TrustedDev2026!`)
docker-compose -f docker-compose.dev.yml exec backend python scripts/seed_e2e_user.py
# walkthrough 시작 안전망: backup 1회
BACKUP_DIR=backups/walkthrough/ bash scripts/backup.sh
```

### 2.2 walkthrough 실행

Phase 1 matrix의 user-guide 섹션을 따라 순서대로 수행:

1. **Playwright headed mode** (자동화 가능 영역, A 분류):
   - 새 spec 파일 임시 작성: `apps/frontend/tests/walkthrough/<page>.walkthrough.ts` (PR에 포함 X — 작업 종료 시 제거 또는 e2e/로 promotion)
   - PortalPage 하네스 메서드 + raw page 조작 혼용 가능 (단발 검증이라 하네스 verb 미흡 시 inline OK)
   - `await page.screenshot({ path: 'docs/sessions/walkthrough-screenshots/user/<page>/<step>.png' })` 로 캡처
2. **수동 검증** (B/C/D 분류): 사람이 브라우저 또는 SMTP 수신함 등 직접 확인 후 결과만 기록

각 단계 실행 후 분류:

| 분류 | 의미 | 처리 |
|------|------|------|
| ✅ 일치 | 매뉴얼 = 시스템 | 기록만 |
| 📝 매뉴얼 오류 | 시스템 동작이 정확하고 매뉴얼이 틀림 | walkthrough 결과 파일에 정정 제안 + Phase 4에서 매뉴얼 PR로 fix |
| 🐛 시스템 버그 | 매뉴얼이 정확하고 시스템이 틀림 | severity (Critical/High/Medium/Low) + 재현 단계 + Phase 4에서 GitHub issue 등록 |
| ⏭ 보류 | 명확하지 않음 | 매뉴얼 작성자 또는 backend-developer 에이전트 검토 필요 |

### 2.3 산출물

`docs/sessions/2026-05-XX-user-manual-walkthrough.md`:

```markdown
# User manual walkthrough — Developer persona

> 실행 시점: main HEAD = <sha>
> 환경: docker-compose dev stack
> 페르소나: Developer (dev@trustedoss.dev)

## 결과 요약
- 총 단계: X
- ✅ 일치: A (X%)
- 📝 매뉴얼 오류: B (Y%)
- 🐛 시스템 버그: C (Z%) — Critical: c1, High: c2, Medium: c3, Low: c4
- ⏭ 보류: D (W%)

## user-guide/projects.md

### projects-1-1 — `/projects` 접속
**단계**: ...
**기대 결과 (매뉴얼)**: ...
**관찰 결과 (시스템)**: ...
**분류**: ✅ 일치

### projects-1-2 — ...
**분류**: 🐛 시스템 버그 (Medium)
- 증상: ...
- 재현: ...
- Phase 4에 issue 등록 예정
- 매뉴얼 정정 불필요

(... 9 페이지)
```

### 2.4 PR

walkthrough 결과 파일만 commit. 매뉴얼 fix / 시스템 버그 fix 는 Phase 4에서 별도 PR. 본 PR은 docs-only:

```bash
git checkout -b chore/user-guide-walkthrough
git add docs/sessions/2026-05-XX-user-manual-walkthrough.md
git commit -m "docs: user manual walkthrough results (Phase 2)"
git push -u origin chore/user-guide-walkthrough
gh pr create --title "docs: user manual walkthrough — Developer persona (Phase 2)" --body "..."
```

캡처된 스크린샷은 `docs/sessions/walkthrough-screenshots/user/` 아래 동행 commit. 단, 본 PR은 walkthrough 결과 + 스크린샷만이고 매뉴얼 / 코드 변경 X.

---

## 세션 3 — Phase 3: Admin persona walkthrough (Super Admin)

**브랜치**: `chore/admin-guide-walkthrough`

### 3.1 사전 준비

세션 2와 동일 + Super Admin 계정 (`admin@trustedoss.dev` / `TrustedAdmin2026!`).

**destructive flow 안전망** (admin-guide의 backup-and-restore + Admin Panel 모두):

```bash
# walkthrough 시작 직전
BACKUP_DIR=backups/walkthrough/ bash scripts/backup.sh
# walkthrough 결과 검증 후 필요 시 복원
# bash scripts/restore.sh backups/walkthrough/<latest>
```

### 3.2 walkthrough

세션 2와 동일한 절차로 admin-guide 6 페이지:
1. users-and-teams
2. dt-connector
3. disk-and-health
4. audit-log
5. backup-and-restore (destructive — 가장 주의)
6. api-keys

특히 **backup-and-restore**:
- backup 트리거 → 다운로드 → upload + typing-gate 흐름을 ephemeral 데이터로 검증
- 실제 시스템 복원은 walkthrough 종료 후 **dev seed 재시드**로 마무리 (또는 step 3.1의 walkthrough backup 사용)
- 10 GB cap, decompression bomb 가드 (PR #36 H3) 도 검증 — 작은 fixture로 가드 동작 확인 (실제 10 GB 업로드 X)

### 3.3 산출물

`docs/sessions/2026-05-XX-admin-manual-walkthrough.md` — 형식은 세션 2와 동일.

### 3.4 PR

```bash
git add docs/sessions/2026-05-XX-admin-manual-walkthrough.md \
        docs/sessions/walkthrough-screenshots/admin/
git commit -m "docs: admin manual walkthrough results (Phase 3)"
```

---

## 세션 4 — Phase 4: Triage + 매뉴얼 fix + 시스템 버그 issue

**브랜치**: 매뉴얼 fix는 영역별로 분리

### 4.1 작업 범위

세션 2/3의 walkthrough 결과를 분류 후 처리:

#### 4.1.1 매뉴얼 fix (📝)

영역별 PR 2개:
- `chore/user-guide-drift-fixes` — user-guide 9 페이지의 매뉴얼 오류
- `chore/admin-guide-drift-fixes` — admin-guide 6 페이지의 매뉴얼 오류

각 PR:
- EN 수정 + 동일한 KO 미러 수정 (CLAUDE.md §8 정합)
- `docs-site && npm run build` 양쪽 SUCCESS 확인
- screenshots 교체는 본 PR 범위 X (별도 chore U로 등재)

#### 4.1.2 시스템 버그 issue (🐛)

severity별:
- **Critical**: 즉시 fix PR (`fix/<bug-id>`)
- **High**: GitHub issue 등록 + 본 세션 또는 다음 세션에서 fix PR
- **Medium / Low**: GitHub issue 등록 + backlog 등재 (별도 chore로 예약)

issue 양식:
```markdown
## Bug — <한 줄 요약>

**Severity**: <Critical/High/Medium/Low>
**Discovered in**: Manual Walkthrough Phase <2|3>, step `<page>-<section>-<step>`
**Persona**: Developer / Super Admin

### Reproduction
1. ...
2. ...

### Expected (per manual)
...

### Actual
...

### Suggested fix
...

### Link
- 매뉴얼: `docs-site/docs/<page>.md:<line>`
- 관련 코드: `apps/<area>/<file>.py:<line>`
```

### 4.2 PR + 머지

각 PR 독립적 lint/test/CI 통과 후 머지. severity Critical 버그 fix가 다른 시나리오에 영향 줄 수 있으므로 순서:
1. Critical bug fix PR(s) 먼저
2. 매뉴얼 fix PR (user → admin)
3. High bug fix PR(s) 마지막

backlog 갱신: 발견된 모든 버그 + 이월 항목 표시.

---

## 세션 5 — Phase 5: manual-aligned E2E 시나리오 추가

**브랜치**: `chore/manual-aligned-e2e`

### 5.1 작업 범위

Phase 1 matrix에서 "기존 E2E 가드 부재 + 회귀 가치 높음"으로 표시된 단계를 Playwright 시나리오로 등재.

대상 (예상):
- 신규 user-guide 페이지 3개 (auth-and-profile, notifications, integrations) — PR #34 신규 페이지로 E2E 부재 가능성 높음
- admin-guide의 destructive flow (`/admin/backup` UI) — PR #29 신규
- in-app notification guard (PR #36 M3) — 422 응답 검증

### 5.2 하네스 확장

기존 `apps/frontend/tests/_harness/` 9 하네스 + PortalPage 메서드 활용. 부족한 영역에 신규 verb 추가:

신규 하네스 후보:
- `AdminBackupHarness.ts` — `/admin/backup` UI (Trigger / Download / Upload+Restore typing-gate)
- `NotificationsHarness.ts` — 헤더 벨 + `/notifications` Inbox + Preferences
- `IntegrationsHarness.ts` (이미 `integrations.ts` 존재 — verb 확장)
- `ProfileHarness.ts` — `/profile` Connected Accounts + Unlink

### 5.3 신규 spec 파일

`apps/frontend/tests/e2e/`:
- `auth_and_profile.spec.ts` (신규)
- `notifications.spec.ts` (신규)
- `admin_backup.spec.ts` (신규, destructive — `BACKUP_DIR=backups/test/` 격리)

각 spec:
- Phase 2/3 walkthrough에서 자동화 가능했던 단계를 정식 E2E로 옮김
- 적대적 input parametrize (memory `feedback_adversarial_input_parametrize`) 적용 (특히 webhook URL / API Key scope / backup upload)

### 5.4 검증

```bash
cd apps/frontend
npm run test:e2e -- --grep "@manual-aligned" 2>&1 | tail -30
```

기존 시나리오 회귀 X 확인:
```bash
npm run test:e2e 2>&1 | tail -20  # 전체 39 + 신규 통과
```

### 5.5 PR + 머지

`chore/manual-aligned-e2e` PR 단일. 신규 하네스 + 신규 spec 통합. CI `e2e (scan-flow)` 잡 통과 확인.

---

## 세션 6 — Phase 6: CI 게이트 통합

**브랜치**: `chore/manual-aligned-ci-gate`

### 6.1 작업 범위

세션 5에서 추가한 시나리오를 CI에 통합:

옵션 A — 기존 `e2e (scan-flow)` 잡에 흡수 (단순)
옵션 B — `e2e (manual-aligned)` 신규 잡 분리 (긴 시간 시나리오 격리)

`apps/frontend/tests/e2e/` 의 spec 수가 9 → 12+로 증가. 잡 시간이 6분 → 8~10분으로 연장 가능. 시간 압박 있으면 옵션 B (병렬).

### 6.2 신규 잡 (옵션 B 시)

`.github/workflows/ci.yml`:

```yaml
e2e-manual-aligned:
  needs: typecheck
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: docker-compose dev stack up
      run: docker-compose -f docker-compose.dev.yml up -d --wait
    - name: seed data
      run: docker-compose -f docker-compose.dev.yml exec -T backend python scripts/seed_e2e_user.py
    - name: Playwright install
      run: cd apps/frontend && npm ci && npx playwright install --with-deps
    - name: Run manual-aligned scenarios
      run: cd apps/frontend && npm run test:e2e -- --grep "@manual-aligned"
    - name: Tear down
      if: always()
      run: docker-compose -f docker-compose.dev.yml down -v
```

### 6.3 PR + 머지

본 PR이 통과하면 후속 PR이 매뉴얼 또는 신규 페이지 변경 시 자동으로 drift 감지 가능.

backlog 마지막 갱신:
```markdown
### ~~Manual Walkthrough — Phase 1 ~ 6~~ ✅ PR #<α>~#<ζ> (2026-05-XX)
**처리 결과**:
- Phase 1 matrix → Phase 2/3 walkthrough → Phase 4 매뉴얼 fix N개 + 시스템 버그 fix M개 → Phase 5 E2E 시나리오 K개 추가 → Phase 6 CI 통합
- 신규 issue → fix PR 처리 통계
- 매뉴얼 정합성 회복: EN/KO 모두 walkthrough 통과
```

---

## 4. 자율 실행 프로토콜 (모든 세션 공통 적용)

`docs/autonomous-execution-plan.md` §"자율 실행 프로토콜" 그대로:

```
LOOP per session:
  1. 시작 시 검증 (§2)
  2. 새 브랜치 생성 + push (-u origin)
  3. 에이전트 위임 또는 직접 구현 (Playwright 실행은 frontend-dev 또는 test-writer 에이전트)
  4. 로컬 검증 (lint + typecheck + test + i18n:check + Docusaurus build 해당 시)
  5. PR 생성 + CI 모니터링 (background polling, 사용자 task-notification 으로 깨움)
  6. CI 실패 시 fix + push (최대 3회 retry → 초과 시 BLOCKED 표시 + 다음 세션 이월)
  7. 머지 후 chore-backlog.md 에 ~~취소선~~ + PR # + commit sha
  8. 세션 종료 핸드오프 노트 작성 → 본 prompt 의 "현재 상태" 섹션 갱신
```

PR 분리 원칙: 한 PR = 한 chore 또는 한 영역 (user vs admin). 매뉴얼 fix와 시스템 버그 fix는 절대 같은 PR에 묶지 말 것.

## 5. 세션 종료 체크리스트 (매 세션 끝 반드시)

- [ ] 작업한 chore 가 머지됐는지 (`gh pr view <num> --json mergedAt`)
- [ ] main 으로 checkout + pull 완료
- [ ] `docs/chore-backlog.md` 에 ~~취소선~~ + PR # + commit sha 추가
- [ ] `docs/sessions/2026-05-XX-phase<N>-<topic>.md` 핸드오프 노트 작성
- [ ] 본 파일의 "현재 상태" 섹션 — main HEAD + 최근 commits + 처리율 갱신
- [ ] BLOCKED 항목 발생 시 본 파일 + chore-backlog 양쪽에 BLOCKED 표시
- [ ] **walkthrough 결과 파일** (Phase 2/3) — 다음 세션에서 reference. 절대 삭제 X

## 6. 세션 끊김 시 복구 절차

새 세션 시작:
1. 본 파일을 첫 메시지로 그대로 붙여넣음
2. **§2 시작 시 검증** 실행 → main HEAD 확인
3. `cat docs/chore-backlog.md | grep -E "✅|~~Phase|~~Chore"` 로 처리 완료 항목 파악
4. §3 우선순위 표에서 **첫 번째 미처리 phase** 선택
5. 해당 세션 prompt 그대로 실행

만약 직전 세션이 **walkthrough 중에 끊겼다면** (Phase 2/3):
1. `git status --short` 로 walkthrough 결과 파일 진행 상태 확인
2. `docs/sessions/walkthrough-screenshots/` 의 마지막 스크린샷 step ID 로 진행 위치 추정
3. 해당 단계부터 이어서 수행
4. dev stack `docker-compose -f docker-compose.dev.yml ps`로 살아있는지 확인. 죽었으면 `up -d` 후 seed 재실행

만약 **로컬 working tree 가 dirty 상태로 끊겼다면**:
1. `git status --short` 로 변경 사항 확인
2. 의도한 변경이면 commit + push, 아니면 `git stash` 또는 `git restore` 로 정리
3. **untracked walkthrough screenshot 디렉토리는 유지** (다음 세션에서 활용)

## 7. 참조 문서

- `CLAUDE.md` — 핵심 규칙 + 품질·보안 표준
- `docs/v2-execution-plan.md` — Phase 별 상세
- `docs/autonomous-execution-plan.md` — 자율 실행 프로토콜
- `docs/chore-backlog.md` — **본 세션의 단일 진실** (잔여 chore + 처리 결과)
- `docs/sessions/2026-05-09-post-ga-cleanup-complete.md` — 직전 6 세션 통합 핸드오프
- `docs/sessions/2026-05-08-uat-manual-test-scenarios.md` + `2026-05-09-uat-v2.0.0-scenarios.md` — 기존 27 시나리오
- `apps/frontend/tests/_harness/PortalPage.ts` — Playwright 하네스 entry point
- `MEMORY.md` — 장기 기억

## 8. 주의사항

- **매뉴얼 fix와 시스템 버그 fix를 절대 같은 PR에 묶지 말 것** — review 부담 + revert 비용 증가
- **walkthrough 중 발견한 의도하지 않은 변경은 본 prompt 외 작업** — backlog 등재 후 별도 chore로 분리
- **destructive 작업은 dev compose만 + backup 안전망** — 운영자가 별도 환경에서 실행 시 명시 승인 필요
- **에이전트 한도** — 한 prompt 당 한 에이전트는 약 80~150 도구 호출. walkthrough 9 페이지 한 번에 위임 시 timeout 위험 → 페이지별 또는 영역별 분할 권고
- **EN / KO 동시 정정** — 매뉴얼 fix 시 한 쪽만 고치지 말 것 (CLAUDE.md §8)
- **Memory `feedback_scope_assumptions`** — prompt 의 "기대 결과" 가정을 1차 가설로만 사용. 실제 시스템 동작과 다르면 시스템 동작을 진실로 (또는 시스템 버그 분류)
- **Memory `feedback_adversarial_input_parametrize`** — Phase 5 E2E 시나리오에 적대적 input 케이스 함께 추가 (특히 webhook URL / API Key scope / backup upload)
- **세션 내 1 PR 원칙** — walkthrough 결과 분량이 커도 1 PR. matrix / user / admin / E2E / CI 6개 PR 분리 유지

본 작업 예상 시간: 세션당 0.5~1.5 시간, 6 세션 전체 약 5~7 시간.
