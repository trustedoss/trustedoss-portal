# 다음 세션 시작 prompt — Chore Backlog 처리

> Step 1~12 (PR #16~#27) 모두 머지 완료 (2026-05-08 ~ 05-09).
> 이 prompt를 새 세션 첫 메시지에 그대로 붙여넣어 시작한다.

---

TrustedOSS Portal v2 작업을 `~/projects/trustedoss-portal/` 에서 이어서 진행한다.

## 0. 현재 상태 (2026-05-09 기준)

- main HEAD = `c75f11c` (plan: Step 12 DONE)
- 누적 머지: PR #1 ~ #27 (Step 1~12 + 사전 Phase 0~4 PRs)
- 12 단계 자율 실행 모두 완료. 남은 작업은 미흡 항목 정리뿐.

```bash
git log --oneline -3
# c75f11c plan: Step 12 DONE (PR #27) — 모든 12 steps 완료
# 81addbb Phase 8 PR #24 — SAST CI (bandit + semgrep) + CHANGELOG + release helper (#27)
# 2a3ec5a plan: Step 11 DONE (PR #26) → Step 12 IN_PROGRESS
```

## 1. 단일 진실

- `docs/chore-backlog.md` — **이 세션에서 처리할 chore PR 목록**. 우선순위 1~5, 11개 항목.
- `docs/autonomous-execution-plan.md` — Step 1~12 모두 `[x] DONE`. 각 Step의 "미흡 (별도 chore)" 섹션에 chore-backlog.md 항목들이 매핑.
- `CLAUDE.md` — 핵심 규칙 13개 (PostgreSQL only, alembic forward-only, docker-compose V1, os.getenv() 런타임 등) + 품질·보안 표준.
- `CHANGELOG.md` — v2.0.0-rc.1 릴리스 정리. 정식 릴리스는 Chore K (release.sh).
- `MEMORY.md` — 사용자 피드백 + 프로젝트 상태 인덱스.

## 2. 시작 시 검증 (반드시)

```bash
# 환경 건강 확인
docker-compose -f docker-compose.dev.yml ps           # 6/6 healthy
gh run list --limit 3                                 # main 최신 success
git status                                            # working tree clean
git checkout main && git pull --ff-only               # 최신 반영
cat docs/chore-backlog.md | head -80                  # backlog 우선순위 확인
```

main의 working tree 잔여 (무시):
- `.claude/scheduled_tasks.lock`
- `apps/frontend/@/` (artifact 폴더)
- `docs/review-binaryanalysis-ng.md` (분석 자료)
- `docs/sessions/2026-05-08-uat-manual-test-scenarios.md` (UAT 시나리오 메모)
- `docs/sessions/_next-session-prompt-phase4-pr15-plus-chore-pr9.md` (이전 prompt)

## 3. 처리 순서 (chore-backlog.md 권장 순서)

### 세션 1 — 사용자 가시성 (우선순위 1)
**브랜치**: `chore/frontend-bundle`
**묶음**: Chore A + B + C
- A: 알림 센터 + 비밀번호 찾기 + i18n 게이트
- B: Frontend OAuth 버튼
- C: /integrations 페이지 (API Key 관리 UI)

이 세 가지는 모두 frontend-only 또는 백엔드는 이미 존재. 한 PR에 묶어도 OK 또는 분리.

### 세션 2 — 운영 안정성 (우선순위 2)
**브랜치**: `chore/phase6-pr19-backup-ws`
- D: 자동 백업 + 수동 백업/복원 UI + WebSocket 재연결

### 세션 3 — 보안·성능 (우선순위 4)
**브랜치**: `chore/security-bundle`
- H: SAST HARD FAIL 전환
- I: 부하 테스트 (Locust)
- J: SCA on self

### 세션 4 — 정식 릴리스 (우선순위 4 + 5)
**브랜치**: `chore/phase5-pr16-tests` + 직접 main
- L: API Keys / Webhooks 백엔드 테스트 보강
- K: v2.0.0 정식 릴리스 (`bash scripts/release.sh v2.0.0`)

### 세션 5 — Demo SaaS (우선순위 3)
**브랜치**: `chore/phase8-pr23-gcp-terraform`
- F: GCP Terraform + Cloud Run + seed_demo
- G: Admin OAuth identity 관리 UI

## 4. 이 세션의 권장 시작점

**가장 먼저** 묶음 1 (Chore A + B + C — frontend-bundle)을 작업한다. 이유:
- 백엔드 API는 이미 PR #20, #22, #26에서 완성됨
- 프론트엔드 작업만 필요 (frontend-dev 에이전트 1개)
- 사용자 가시성 (UI 미완 → GA blocker)

새 브랜치 생성:
```bash
git checkout -b chore/phase6-7-8-frontend-bundle
git push -u origin chore/phase6-7-8-frontend-bundle
```

그리고 frontend-dev 에이전트 위임 (chore-backlog.md의 Chore A/B/C 통합 prompt 작성).

## 5. 자율 실행 프로토콜 (chore-backlog 단위 적용)

`docs/autonomous-execution-plan.md` §"자율 실행 프로토콜" 그대로 따른다:

```
LOOP:
  1. 구현 (에이전트 배치 또는 직접)
  2. ruff/mypy/tsc/vitest 로컬 실행
  3. PR 생성 + CI 모니터링
  4. CI 실패 시 fix + push
  5. 머지 후 chore-backlog.md에서 해당 항목 ✓ 표시
  6. 다음 chore로 이동

  최대 3회 retry. 실패 시 BLOCKED 표시 후 다음 세션으로 이월.
```

## 6. 세션 종료 체크리스트

세션을 종료하기 전:
1. `docs/chore-backlog.md` 에서 처리한 항목에 `~~취소선~~` + 머지 PR # 추가
2. 남은 항목과 BLOCKED 항목 정리
3. 새 세션용 prompt가 변경되면 이 파일 갱신
4. main 최신 commit + CI 상태 핸드오프 노트 추가

## 7. 참조 문서

- `CLAUDE.md` — 핵심 규칙
- `docs/v2-execution-plan.md` — Phase 별 상세
- `docs/autonomous-execution-plan.md` — Step 1~12 완료 기록
- `docs/chore-backlog.md` — **이 세션의 단일 진실**
- `MEMORY.md` — 장기 기억

## 8. 주의사항

- **추측하지 말 것**: `docs/chore-backlog.md` 의 각 항목 설명을 그대로 따른다. 그 외 새 기능을 임의로 추가하지 않는다.
- **하나씩 머지**: 각 chore는 독립 PR. 한 세션에 여러 chore를 묶을 때도 별도 commit으로 분리하면 revert 용이.
- **CI 모니터링**: PR 생성 후 `gh run list --limit 2` + `until !` 패턴으로 backgrounded 모니터링 (autonomous-execution-plan.md의 패턴).
- **에이전트 한도**: 단일 에이전트에 너무 많은 작업을 주면 한도 도달. Chore 1~2개씩 분리해서 위임.

본 작업 예상 시간: 세션당 1~2시간, 5세션 전체 약 8~10시간.
