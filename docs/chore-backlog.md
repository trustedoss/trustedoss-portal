# TrustedOSS Portal v2 — Chore Backlog

> Step 1~12 (PR #16~#27) 머지 과정에서 시간 제약 또는 한도 도달로 미루어진 항목 정리.
>
> 각 항목은 독립적인 chore PR로 처리 가능. **우선순위 순서**로 나열했고, 같은 chore PR 안에 함께 묶을 수 있는 항목은 그룹으로 표시.

---

## 우선순위 1 — 사용자 가시성 / GA blocker

### Chore A1 — 비밀번호 찾기 + i18n 게이트 (frontend-only)
**기반 PR**: #22 (Step 7 backend — `/auth/forgot-password`, `/auth/reset-password` 존재)
**브랜치 제안**: `chore/frontend-bundle`
**예상 소요**: 0.5 세션

미흡:
- `/forgot-password` 프론트 화면 → backend `/auth/forgot-password` 연동 (현재 stub)
- `/reset-password` 프론트 화면 신규 (`?token=` 쿼리 파라미터 → `/auth/reset-password` POST)
- `i18next-parser` CI 게이트: EN/KO drift 0 강제

### Chore A2 — 인앱 알림 센터 + 채널 ON/OFF (backend + frontend)
**기반 PR**: 없음 (PR #22 는 outbound dispatcher 만 배포, in-app notification center 백엔드 미존재)
**브랜치 제안**: `chore/phase6-inapp-notifications`
**예상 소요**: 1.5 세션

미흡 — **백엔드 신규 작업 필요**:
- 백엔드: `notifications` 테이블 + Alembic + `/v1/notifications` (GET list, PATCH /:id/read), `/v1/users/me/notification-prefs` (PUT)
- 프론트: `/notifications` 페이지 + 헤더 벨 아이콘 (읽음/안읽음 카운트)
- 프론트: 사용자 설정 페이지 — 채널별 ON/OFF (email/slack/teams)

### Chore B — Frontend OAuth 버튼
**기반 PR**: #26 (Step 11 backend)
**브랜치 제안**: `chore/phase8-pr23-frontend-oauth`
**예상 소요**: 0.5 세션

미흡:
- `/login` 페이지에 "Sign in with GitHub" / "Sign in with Google" 버튼
- `redirect_after` 쿼리 파라미터 처리 (로그인 후 돌아갈 곳)
- `?error=oauth_*` 코드별 사용자 메시지 (i18n)
- e2e 테스트: OAuth 버튼 클릭 → 302 → mock callback → AppShell 마운트

### Chore C — /integrations 페이지
**기반 PR**: #20 (Step 5)
**브랜치 제안**: `chore/phase5-pr16-integrations-ui`
**예상 소요**: 0.5 세션

미흡:
- `/integrations` 페이지: API Key 생성/조회/폐기 UI
- 평문 키 1회 표시 + 복사 버튼 (이후 prefix만)
- Webhook 수신 URL 안내 (project별 webhook_secret 설정 안내)
- super_admin 외에는 자신 팀/프로젝트 키만 보임

---

## 우선순위 2 — 운영 안정성

### Chore D — 자동 백업 + 수동 백업/복원 UI + WebSocket 재연결
**기반 PR**: #23 (Step 8)
**브랜치 제안**: `chore/phase6-pr19-backup-ws`
**예상 소요**: 1 세션

미흡:
- Celery Beat 매일 자정 자동 백업 (pg_dump + workspace tar)
  - `tasks/backup.py`: 호스트 디스크에 `backups/auto-YYYYMMDD/` 생성
  - 7일 retention (이미 `scripts/backup.sh` 패턴 따라)
- 수동 백업/복원 Admin UI (`/admin/backup`)
  - 다운로드 버튼 + 업로드 복원 (확인 다이얼로그 + audit emit)
- WebSocket 재연결 (탭 이탈 후 복귀 시 진행률 즉시 동기화)
  - `useScanWebSocket` hook에 visibility 이벤트 리스너 추가
  - `document.visibilityState === 'visible'` → reconnect

### Chore E — backup.sh / restore.sh 실제 검증
**기반 PR**: #24 (Step 9)
**브랜치 제안**: `chore/phase7-pr20-install-uat`
**예상 소요**: 0.5 세션

미흡:
- fresh Linux machine에서 `bash scripts/install.sh` end-to-end 시나리오 테스트
- shellcheck CI 게이트 추가 (현재 syntax check만)
- 멀티 PostgreSQL 버전 (16.x → 17.x) 마이그레이션 시나리오 검증

---

## 우선순위 3 — Demo SaaS / GA 준비

### Chore F — GCP Terraform + Cloud Run + seed_demo
**기반 PR**: #26 (Step 11 backend)
**브랜치 제안**: `chore/phase8-pr23-gcp-terraform`
**예상 소요**: 1.5 세션

미흡:
- `terraform/` 디렉토리: Cloud Run + Cloud SQL PostgreSQL + Memorystore Redis
- `terraform plan` 오류 없음, 비용 추정 < $50/월
- `apps/backend/scripts/seed_demo.py`: 데모 시드 (3개 팀, 5개 프로젝트, 10개 스캔, 가짜 CVE)
- `docs-site/docs/installation/gcp-deploy.md` (EN/KO)

### Chore G — Admin OAuth identity 관리 UI
**기반 PR**: #26 (Step 11 backend)
**브랜치 제안**: `chore/phase8-admin-oauth-unlink`
**예상 소요**: 0.5 세션

미흡:
- 사용자 프로필 화면에 "Connected accounts" 섹션
- "Unlink GitHub" / "Unlink Google" 버튼 → DELETE `/v1/oauth/identities/{id}`
- 백엔드 엔드포인트 신규 (마지막 인증 수단 보호: password 없으면 unlink 차단)

---

## 우선순위 4 — 보안·성능·릴리스 강화

### Chore H — SAST HARD FAIL 전환
**기반 PR**: #27 (Step 12)
**브랜치 제안**: `chore/phase8-pr25-sast-hard-fail`
**예상 소요**: 0.5 세션

미흡:
- bandit advisory → HARD FAIL on High+ findings
- semgrep advisory → HARD FAIL on ERROR severity
- 기존 finding inventory 점검 후 false positive는 `# nosec`/`# nosemgrep` 명시
- Trivy CI 게이트 HARD FAIL 활성화 (현재 soft-fail)

### Chore I — 부하 테스트 (Locust)
**기반 PR**: #27 (Step 12)
**브랜치 제안**: `chore/phase8-pr25-locust`
**예상 소요**: 1 세션

미흡:
- `tests/load/locustfile.py`: 동시 스캔 3개, 동시 사용자 50명 시나리오
- `docker-compose.load.yml`: locust master + worker 2~3 노드
- 보고서: p95 < 1s 목표 검증
- CI 게이트는 NO (수동 실행만 — staging 환경)

### Chore J — SCA on self (dog-fooding)
**기반 PR**: #27 (Step 12)
**브랜치 제안**: `chore/phase8-pr25-sca-on-self`
**예상 소요**: 0.5 세션

미흡:
- 자신의 코드를 TrustedOSS Portal API로 스캔 (CI에서 nightly cron)
- Critical CVE 발견 시 GitHub Issue 자동 생성
- README에 "TrustedOSS Portal scans itself" 배지

### Chore K — v2.0.0 정식 릴리스
**기반 PR**: #27 (Step 12)
**브랜치 제안**: 직접 main에서 `bash scripts/release.sh v2.0.0`
**예상 소요**: 0.25 세션

미흡:
- CHANGELOG.md `## [Unreleased]` → `## [2.0.0] — YYYY-MM-DD`
- `bash scripts/release.sh v2.0.0` 실행
- GitHub Pages 첫 배포 검증 (docs.yml 트리거)
- 릴리스 공지 (LinkedIn/HN 등은 사용자 책임)

---

## 우선순위 5 — 테스트 / 코드 품질

### Chore L — API Keys / Webhooks 백엔드 테스트 보강
**기반 PR**: #20 (Step 5)
**브랜치 제안**: `chore/phase5-pr16-tests`
**예상 소요**: 0.5 세션

미흡 — Step 5는 시간 제약으로 단위/통합 테스트 미작성:
- `tests/unit/services/test_api_key_service.py`: 키 생성/회전/폐기 시나리오
- `tests/integration/test_api_keys_api.py`: 4-role matrix + RBAC
- `tests/integration/test_webhooks_github.py`: HMAC 검증 + 멱등성 + adversarial input
- `tests/integration/test_webhooks_gitlab.py`: 동일

---

## 진행 순서 권장

병렬 가능한 항목은 한 세션에 묶어서 처리:

| 세션 | 묶음 | PRs |
|-----|------|-----|
| 1 | 우선순위 1 | A + B + C 한 PR로 (`chore/frontend-bundle`) |
| 2 | 우선순위 2 | D 단독 |
| 3 | 우선순위 4 | H + I + J 한 PR로 (`chore/security-bundle`) |
| 4 | 우선순위 5 + 4 K | L + K 마지막 (정식 릴리스) |
| 5 | 우선순위 3 | F + G (Demo SaaS) — GA 후 진행 |

---

## 새 세션 시작 시 사용

`docs/sessions/_next-session-prompt-chore-backlog.md` 파일이 작성됨.
새 세션 첫 메시지에 그 파일 내용을 그대로 붙여넣으면 정확한 컨텍스트로 시작.
