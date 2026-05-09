# 다음 세션 시작 prompt — Chore Backlog 처리 (세션 2 시작점)

> Step 1~12 (PR #16~#27) 머지 완료 + Chore frontend bundle (PR #28) 머지 완료 (2026-05-09).
> 이 prompt를 새 세션 첫 메시지에 그대로 붙여넣어 시작한다.

---

TrustedOSS Portal v2 작업을 `~/projects/trustedoss-portal/` 에서 이어서 진행한다.

## 0. 현재 상태 (2026-05-09 기준)

- main HEAD = `df5bb5e` (PR #28 — chore frontend bundle: A1 + B + C)
- 누적 머지: PR #1 ~ #28 (Step 1~12 + chore PRs)
- chore-backlog 처리율: 11 항목 중 **3 done (A1, B, C)** + 1 신규 (A2 deferred). 잔여 9 항목.

```bash
git log --oneline -3
# df5bb5e chore: frontend bundle (Chore A1 + B + C) — password reset wiring, OAuth buttons, /integrations page (#28)
# 2ff9c1e docs: chore backlog + next-session prompt for post-Step-12 cleanup
# c75f11c plan: Step 12 DONE (PR #27) — 모든 12 steps 완료
```

세션 1 핸드오프: `docs/sessions/2026-05-09-chore-frontend-bundle.md`

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

### ~~세션 1 — 사용자 가시성 (우선순위 1)~~ ✅ PR #28 머지 (2026-05-09)
~~A + B + C 통합~~ → A1 + B + C 처리됨. A2 (인앱 알림 센터) 는 백엔드 신규 작업 필요라 세션 6 으로 분리.

### 세션 2 — 운영 안정성 (우선순위 2) ← **이번 세션 시작점**
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

**가장 먼저** Chore D (자동 백업 + 수동 백업/복원 UI + WebSocket 재연결) 를 작업한다. 이유:
- 백엔드는 `scripts/backup.sh` 가 이미 존재. Celery Beat task + Admin UI + WS reconnect 만 추가.
- backend-developer + scan-pipeline-specialist + frontend-dev 3개 에이전트 협업.
- GA 운영성 (백업 미존재는 prod 배포 blocker).

새 브랜치 생성:
```bash
git checkout main && git pull --ff-only
git checkout -b chore/phase6-pr19-backup-ws
git push -u origin chore/phase6-pr19-backup-ws
```

그리고 `docs/chore-backlog.md` Chore D 의 미흡 목록 그대로 적용:
- `tasks/backup.py` (Celery Beat 매일 자정, pg_dump + workspace tar, 7일 retention)
- `/admin/backup` 페이지 (다운로드 + 업로드 복원 + audit emit)
- `useScanWebSocket` hook 에 `visibilitychange` listener (탭 복귀 시 reconnect)

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
