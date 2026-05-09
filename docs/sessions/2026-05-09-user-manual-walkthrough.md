# User manual walkthrough — Developer persona

> 실행 시점: main HEAD = `c5dbefe` (2026-05-09 docs: next-session prompt — manual walkthrough verification)
> 환경: docker-compose dev stack
>   - postgres / redis / backend / frontend healthy
>   - ⚠ celery-worker 2일 전 (Chore P 이전) 빌드라 `ModuleNotFoundError: aiosmtplib` restart loop — 알림 outbound dispatch 단계 부분 검증 불가
>   - ⚠ postgres data volume 100% (`No space left on device`) — auth 가 audit_log INSERT 실패로 500 응답하는 경우 다수. 본 walkthrough 는 정적 (Tier 1) grep 검증을 메인으로, 동적 (Tier 2) curl 은 보조로 사용
> 페르소나: Developer (`dev@trustedoss.dev`)
> 검증 방법: Tier 1 정적 (frontend/backend grep + 코드 reading) 기본, Tier 2 dynamic (curl) 가능한 경우만, Tier 3 보류 = 외부/시각/운영 영역
> Phase 1 matrix: `docs/sessions/2026-05-09-manual-coverage-matrix.md`
> 본 PR 범위: docs-only (매뉴얼 fix / 코드 fix 절대 X — Phase 4 에서 별도 PR 로 분리)

## 결과 요약

- 총 검증 단계: **74** (matrix 의 207 사용자 단계 중 P0 ⚠ 4 + P1 신규 가드 부재 + P2 샘플링 + P3 매뉴얼 정확성 grep)
- ✅ 일치: **23** (31%)
- 📝 매뉴얼 오류: **31** (42%)
- 🐛 시스템 버그: **2** (3%) — Critical 0, High 0, Medium 1, Low 1
- ⏭ 보류: **18** (24%) — 외부 OAuth / SMTP / Slack / Teams / 시각 / 운영 판단 / GitHub-GitLab webhook 발신
- 미처리: 207 - 74 = **133** (대부분 P3 — matrix의 자동화 가능 분류 A 중 시간 한도 초과로 sampling 만 진행. Phase 5 E2E 시나리오 추가 시 일괄 검증 권장)

핵심 결론: **사용자 매뉴얼은 v2.0.0 의 실제 시스템보다 큰 폭으로 앞선 비전을 기술**한다. 매뉴얼이 약속한 다수 기능 (Reports menu, 모든 Excel/PDF report, 모든 expiry 옵션, scope=org/team/project 외 expiry preset, project Settings 의 visibility/container_image/tags/deploy key/CI-CD subtab/webhook secret rotate, Approvals 의 New request UI / bulk verdict / Reviewer column, Notifications dropdown / 5-recent / 10 trigger 매핑, Profile Password row, /audit team-admin 페이지, scan kind 선택 dialog, 컴포넌트 Type/Classification/Has-open-CVE 컬럼/필터, 취약점 component/discovered range 필터, scan cancel API 등) **이 v2.0.0 시점에서 실제 코드에 존재하지 않거나 지연 구현 상태**다. 시스템 버그가 적은 이유 = 매뉴얼이 시스템 부재 기능을 "있는 양" 기술하는 패턴 (Phase 4 매뉴얼 fix 가 핵심 작업).

---

## 1. user-guide/projects.md

### projects-1-1 (Anatomy 표 7 필드) — 📝 매뉴얼 오류

- **단계**: "Anatomy of a project" 표가 Name / Repository URL / Default branch / Visibility / Owning team / Container image / Tags 7 필드 정의를 약속
- **검증 방법**: Tier 1 — `apps/backend/models/scan.py:150-235` Project 모델 + `apps/backend/schemas/scan.py:116-243` ProjectCreate/Update/Public + `apps/frontend/src/features/projects/ProjectCreatePage.tsx` + `SettingsTab.tsx`
- **관찰 결과**:
  - 실제 모델 필드: `name`, `slug`, `description`, `git_url`, `default_branch`, `visibility`, `team_id`, `archived_at`, `webhook_secret`, `webhook_provider`, `created_by_user_id`, `latest_scan_id`
  - **`container_image` 필드 부재**, **`tags` 필드 부재**, manual claims `Repository URL` 이지만 schema/model 은 `git_url`
  - `visibility` enum 은 `team` / `organization` (model), 그러나 schema validator 가 `organization` 을 명시적으로 reject — Phase 3+ 까지 reserved (`apps/backend/schemas/scan.py:163-172`). manual 은 `team-only` / `org-wide` (대시 사용) 라벨
- **분류**: 📝 매뉴얼 오류 — Phase 4 정정 권고:
  - "Container image" / "Tags" 행 삭제 또는 "(roadmap)" 표시
  - "Repository URL" → "Git URL" (또는 코드 → schema rename, 둘 중 하나)
  - "team-only" / "org-wide" → `team` / `organization` (그리고 후자는 "(reserved for Phase 3+)" 표시)
  - "Owning team" 은 폼에서 자동 default 이고 사용자 입력 X — UI 와 일치하도록 표 행 수정

### projects-2-1~2-5 (Adding a project — UI) — 📝 매뉴얼 오류

- **단계**: 5단계: 사이드바 Projects → New project → 폼 (Name / Repository URL / Default branch / Visibility / Container image) → Create → Overview
- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/ProjectCreatePage.tsx` 전체 reading
- **관찰 결과**: 실제 폼 필드 = `name`, `description`, `git_url` (3개). **manual 이 약속한 5 필드 중 2개만 매핑**:
  - `Default branch` 입력 칸 부재 (PATCH 단계에서만 수정 가능 — SettingsTab 에 있음)
  - `Visibility` 입력 칸 부재 (서버가 자동으로 `team` 설정)
  - `Container image` 입력 칸 부재
  - 매뉴얼이 빠뜨린 `Description` textarea 가 실제로는 존재
- **분류**: 📝 매뉴얼 오류
- 관련 코드: `apps/frontend/src/features/projects/ProjectCreatePage.tsx:17-28, 86-203`

### projects-3-1 (API: POST /api/v1/projects) — 📝 매뉴얼 오류 + ⏭ 보류

- **단계**: `curl POST https://trustedoss.example.com/api/v1/projects` with `Authorization: ApiKey ${TOKEN}`
- **검증 방법**: Tier 1 — backend router + frontend api base
- **관찰 결과**:
  - **API prefix 가 `/api/v1` 이 아니고 `/v1`** (`apps/backend/main.py:144-174` + `apps/backend/api/v1/projects.py:72`: `prefix="/v1/projects"`). 프론트도 `/v1/...` 로 호출 (`apps/frontend/src/lib/projectsApi.ts:116-180`).
  - 매뉴얼 페이로드에 `container_image` 포함 — API 가 `extra="forbid"` 라서 422 응답할 것 (`apps/backend/schemas/scan.py:119`)
  - `visibility=team_only` 도 422 — enum 값은 `team` / `organization` (`apps/backend/schemas/scan.py:106`)
- **분류**: 📝 매뉴얼 오류 (path + payload 모두) + ⏭ 부분 보류 (실제 curl 은 disk full 로 검증 불가, static 만)

### projects-4-1 (Visibility 변경 = privileged action) — 📝 매뉴얼 오류

- **단계**: visibility 변경 → audit log
- **검증 방법**: Tier 1 — `apps/backend/schemas/scan.py:213-223`
- **관찰 결과**: ProjectUpdate 의 visibility validator 가 `team` 외 모든 값을 reject. **org-wide 로 변경 자체가 불가능.** Audit log 는 PATCH 호출 시 자동 기록되지만 이 단계의 의미가 무의미
- **분류**: 📝 매뉴얼 오류 (Phase 3+ 까지는 Visibility 이라는 행위 자체가 비활성)

### projects-5-1 (Tags) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/models/scan.py:150-235`
- **관찰 결과**: tags 컬럼 부재. tag 추가 자체 불가
- **분류**: 📝 매뉴얼 오류

### projects-6-1 (Archive) — ✅ 일치 (단, 토글 UX 약간 차이)

- **단계**: Archive — 리스트에서 숨김, 새 스캔 disable, 기록 보존
- **검증 방법**: Tier 1 — `apps/backend/models/scan.py:178` `archived_at` 컬럼, `apps/backend/api/v1/projects.py:240` DELETE → soft-delete (`archive_project`)
- **관찰 결과**: archive_at soft-delete 로 동일 동작. UI 는 SettingsTab Archive 버튼 → 인라인 confirm strip (`SettingsTab.tsx:355-397`)
- **분류**: ✅ 일치 (UX 약간 차이는 매뉴얼이 정확)

### projects-6-2 (Delete = typed-name confirmation modal) — 🐛 시스템 버그 (Medium) + 📝 매뉴얼 오류

- **단계**: "Delete — permanently removes the project. Hidden behind typed-name confirmation modal."
- **검증 방법**: Tier 1 — `apps/backend/api/v1/projects.py:240` DELETE 는 archive (soft-delete) 만 수행 + `SettingsTab.tsx` UI 에 "Delete" 버튼 부재
- **관찰 결과**:
  - 실제로는 영구 삭제 기능 자체가 없음. DELETE = archive
  - Typed-name modal 도 없음 (인라인 confirm strip 만 있음)
- **분류**: 🐛 + 📝 — 시스템에 영구 삭제가 없는 것이 의도라면 매뉴얼만 수정 (📝). 영구 삭제가 의도라면 시스템에 추가 (🐛 Medium)
- 권고: **매뉴얼만 수정** — soft-delete + restore 가 더 안전하고, audit-log 보존 일관

### projects-7-1 (Private repo HTTPS+PAT) — ✅ 일치

- **단계**: HTTPS+PAT 형식 URL 등록, token encrypted-at-rest
- **검증 방법**: Tier 1 — git_url 은 `Text` column. encrypted-at-rest 검증은 unit test 영역
- **관찰 결과**: schema 가 https://*@github.com/... 패턴 수용 (`apps/backend/schemas/scan.py:142-161`)
- **분류**: ✅ 일치 (encrypted-at-rest 자체는 별도 검증 필요)

### projects-7-2 ⚠ (Project Settings → Repository → SSH deploy key 생성) — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류

- **단계**: Project Settings 화면에서 SSH deploy key 생성 UI
- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/components/SettingsTab.tsx` 전체 reading + grep `deploy_key`
- **관찰 결과**: SettingsTab 에 deploy key 생성 UI 없음. backend 에 `deploy_key` 컬럼 / endpoint 없음. SettingsTab 는 4 필드만 (name/description/git_url/default_branch). "Repository" 라는 별도 섹션도 없음.
- **분류**: ⚠ (matrix 의심 검증 결과) → 📝 매뉴얼 오류 (deploy key 생성은 git host 에서 manual 로 해야 함, portal 이 생성하지 않음)

### projects-8-1 (Risk score) — ✅ 일치

- **단계**: 0~100, severity + license + 경과시간 가중
- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/components/RiskGauge.tsx`
- **관찰 결과**: RiskGauge 컴포넌트 + Overview 에 노출됨
- **분류**: ✅ 일치 (정확한 식 검증은 unit 영역)

### projects-9-1 (Verify: status `Idle`) — ✅ 일치

- **검증 방법**: Tier 1 — `ProjectStatusBadge.tsx:45-48` `idle` tone, `projects.json:25` "Idle"
- **분류**: ✅ 일치

### projects-9-3 (Verify: audit log `project.create`) — ⏭ 보류 (Tier 1 제한)

- **단계**: `/admin/audit` 에 `project.create` 기록
- **검증 방법**: super_admin 페르소나 필요. Developer 로 `/admin/audit` 접근 불가 (RBAC 가드 검증).
- **관찰 결과**: audit endpoint 는 `require_super_admin_or_404` (`apps/backend/api/v1/admin/audit.py:123`)
- **분류**: ⏭ 보류 (Phase 3 admin walkthrough 에서 다룸)

### projects-10-1 (Trbl: Repository URL invalid — wizard validates HTTPS / git@ / ssh://) — ✅ 부분 일치

- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/ProjectCreatePage.tsx:44-49` (`/^https?:\/\//i` 만 통과)
- **관찰 결과**: **Frontend 가 git@ / ssh:// 거부** (HTTPS only). Backend 는 ssh / git+ssh 도 수용 (`schemas/scan.py:142-161`).
- **분류**: 📝 매뉴얼 오류 — Frontend 는 HTTPS only, manual 의 "git@ 또는 ssh:// 도 수용" 은 Backend 만 진실

---

## 2. user-guide/scans.md

### scans-1-1 (scan kinds 표) — ✅ 일치

- **검증 방법**: Tier 1 — `SCAN_KIND_VALUES = ("source", "container")` (`apps/backend/models/scan.py:82`)
- **분류**: ✅ 일치

### scans-2-1-2 ⚠ (우측 상단 Scan 클릭 → kind 선택 dialog) — 🐛 시스템 버그 (Medium) 또는 📝 매뉴얼 오류

- **단계**: project 열기 → 우측 상단 "Scan" 버튼 → "Source / Container" dialog → branch override → "Start scan"
- **검증 방법**: Tier 1 — `ProjectDetailPage.tsx`, `OverviewTab.tsx` grep
- **관찰 결과**:
  - **ProjectDetailPage 에 Scan 트리거 버튼 자체 없음.** OverviewTab 에 trigger UI 없음
  - Scan 트리거는 **ProjectListPage.tsx:139-145** 에만 있음 — `triggerScan(project.id, { kind: "source" })` hardcoded
  - Source/Container 선택 dialog 부재. Branch override 부재. "Start scan" 버튼 라벨 부재 (라벨은 단순 "Scan")
- **분류**: 📝 매뉴얼 오류 — UX 가 매뉴얼보다 단순. v2.0.0 시점에 dialog 미구현. Phase 4 정정 또는 "(roadmap — UI dialog 향후 구현)" 표시 권고

### scans-2-1-5 (Start scan → live progress + WebSocket) — ✅ 일치

- **검증 방법**: Tier 1 — `ScanProgress.tsx` + `useScanWebSocket.ts`
- **분류**: ✅ 일치

### scans-2-1-6 (탭 닫고 다시 열기 → reconnect) — ✅ 일치

- **검증 방법**: Tier 1 — `useScanWebSocket.ts` 의 reconnect handler
- **분류**: ✅ 일치 (정확한 backoff 측정은 unit 영역)

### scans-2-2 (API path) — 📝 매뉴얼 오류

- **단계**: `POST /api/v1/projects/{id}/scans`
- **검증 방법**: Tier 1 — `apps/backend/api/v1/scans.py` + `main.py:151`
- **관찰 결과**: 실제 path = `/v1/projects/{id}/scans` (no `/api` prefix)
- **분류**: 📝 매뉴얼 오류

### scans-3-1 (Lifecycle 5 status) — ✅ 일치

- **검증 방법**: Tier 1 — `SCAN_STATUS_VALUES` + scans.py:68 pattern
- **관찰 결과**: 5 상태 (queued/running/succeeded/failed/cancelled) 정확
- **분류**: ✅ 일치

### scans-3-1 (Lifecycle 표 cancelled = "DELETE /v1/scans/{id}") — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/api/v1/scans.py` 에서 DELETE 메서드 grep
- **관찰 결과**: scans.py 에 `@router.delete` 없음. **Cancel API 자체 부재.** UI 도 cancel 버튼 없음.
- **분류**: 🐛 (manual 이 약속한 cancellation 기능 부재) 또는 📝 (cancel 은 향후 기능). Phase 4 트리아지 권고: cancel 기능을 v2.0.x patch 로 추가하거나 매뉴얼에서 lifecycle row 의 cancelled 행을 "(향후 기능)" 으로 표시

### scans-3-2-1~6 (Pipeline stages 6단계) — ⏭ 보류 (Tier 2 worker 의존)

- **검증 방법**: worker 가 restart loop 라 dynamic 검증 불가. 정적으로는 step 이름이 frontend `ScanProgress.tsx` 의 `PIPELINE_STEPS` 와 매뉴얼 6 단계 일치 여부 비교
- **관찰 결과** (Tier 1 부분):
```
PIPELINE_STEPS = ["queued", "preparing", "fetching", "detecting", "analyzing", "resolving", "persisting", "succeeded"]  // 약식
```
- **분류**: ⏭ 보류 — 매뉴얼은 6 단계 (Bootstrapping, Fetching source, Detecting components, Analyzing licenses, Resolving vulnerabilities, Persisting) 정확. 프론트 `PIPELINE_STEPS` 매핑 검증은 worker 복구 후 dynamic 확인 권장.

### scans-5-1 (사이드바 Scans → 전역 큐) — 📝 매뉴얼 오류

- **단계**: developer 가 사이드바 Scans 진입 가능
- **검증 방법**: Tier 1 — `ScansPage.tsx` + `apps/frontend/src/router.tsx`
- **관찰 결과**: `/scans` 라우트 + 사이드바 Scans 항목 존재. 다만 "Cancel any team's scan" 액션은 backend cancel API 부재로 실현 불가
- **분류**: 📝 매뉴얼 오류 (cancel 부분만)

### scans-6-1 (WebSocket 메시지 shape) — 📝 매뉴얼 오류 (큰 drift)

- **단계**: `{scan_id, stage, progress, message, ts}`
- **검증 방법**: Tier 1 — `apps/backend/api/v1/ws.py:231-241` `build_progress_frame`
- **관찰 결과**: 실제 shape = `{"percent": int, "step": str, "ts": iso8601}`. **`scan_id` 없음, `stage` → `step`, `progress` → `percent`, `message` 없음.** WS path 도 `wss://<host>/api/v1/scans/{id}/progress` 가 아니라 `ws://<host>/ws/scans/{scan_id}` (`apps/backend/api/v1/ws.py:340` + `apps/frontend/src/lib/wsBase.ts:53-57`)
- **분류**: 📝 매뉴얼 오류 — path 와 shape 모두 정정 필요. 클라이언트 코드 작성자가 매뉴얼만 보면 작동 안 함.

### scans-7-1 ⚠ (Verify: status switches to **Completed**) — 📝 매뉴얼 오류

- **단계**: "The project status switches to **Completed**"
- **검증 방법**: Tier 1 — `apps/frontend/src/locales/en/scans.json:8,26` `"succeeded": "Succeeded"` + `project_detail.json:73`
- **관찰 결과**: 실제 라벨 = **"Succeeded"**. lifecycle 표는 `succeeded`. manual Verify 섹션의 "Completed" 가 일관성 위반
- **분류**: 📝 매뉴얼 오류 (matrix ⚠ 검증 결과: drift 확인됨)

### scans-7-3 (Verify: Vulnerabilities count visible) — ✅ 일치

- **검증 방법**: 부분 가드 `vulnerabilities.spec.ts:78`
- **분류**: ✅ 일치

### scans-8-1 (Trbl: scan stuck — `docker-compose ps worker`) — ⏭ 보류 (Tier 1 만)

- **분류**: ⏭ 부분 보류 — 명령은 정확하지만 외부 docker-compose 실행 필요. 이번 walkthrough 의 worker stale 자체가 이 시나리오의 라이브 사례 ("worker unhealthy → restart")

---

## 3. user-guide/vulnerabilities.md

### vulns-1-1 (Severity 표 5 단계) — ✅ 일치

- **검증 방법**: Tier 1 — `VULN_SEVERITY_VALUES` 5 (critical/high/medium/low/info)
- **분류**: ✅ 일치

### vulns-1-2 (build gate fail = Critical only, owner lower to High) — ⏭ 보류

- **단계**: per-project gate config
- **검증 방법**: Tier 1 — `apps/backend/api/v1/policy_gate.py` + UI grep
- **관찰 결과**: per-project gate config UI 미확인 (별도 grep 필요)
- **분류**: ⏭ 보류 (Phase 5 E2E 권고 — gate config 화면 검증)

### vulns-2-1 (VEX 7-state 표) — ✅ 일치

- **검증 방법**: Tier 1 — `VULN_FINDING_STATUS_VALUES` 7개 (new/analyzing/exploitable/not_affected/false_positive/suppressed/fixed) + `project_detail.json:154-160`
- **분류**: ✅ 일치 (memory `feedback_vex_status_enum` 적용 확인됨)

### vulns-2-2 (justification ≥10 chars) — ✅ 일치

- **검증 방법**: Tier 1 — `vulnerabilities.spec.ts:197` setVulnerabilityStatus
- **분류**: ✅ 일치 (정확한 10자 경계 검증은 unit / E2E 영역)

### vulns-3-1 (6 컬럼) — 📝 매뉴얼 오류

- **단계**: CVE / Component / Severity / State / Discovered / Last seen
- **검증 방법**: Tier 1 — `project_detail.json:137-144` `vulnerabilities.column.*`
- **관찰 결과**: 실제 컬럼 = `cve_id / severity / cvss / summary / affected / status / discovered`. **"Last seen" 부재. "CVSS" 와 "Title (summary)" / "Affected" 가 추가**. Component 컬럼 = `affected` (component name)?
- **분류**: 📝 매뉴얼 오류 — 컬럼 명세 정정 필요

### vulns-3-2 (filter — severity / state / component / discovered range) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/components/VulnerabilitiesToolbar.tsx`
- **관찰 결과**: 실제 filter = severity + status + search + sort + order. **component 별도 필터 없음 (search 로 cover), discovered range 필터 없음**
- **분류**: 📝 매뉴얼 오류

### vulns-3-3 (행 클릭 → drawer) — ✅ 일치

- **검증 방법**: `vulnerabilities.spec.ts:130` (S3 drawer detail render)
- **분류**: ✅ 일치

### vulns-4-1 (Drawer 6 섹션) — 📝 부분 매뉴얼 오류

- **단계**: CVE summary / Affected versions / References / Fix availability / Project history / Triage
- **검증 방법**: Tier 1 — `project_detail.json:183-225` drawer 키
- **관찰 결과**: 실제 drawer 섹션 = summary / references / affected (with fixed_in) / analysis (= triage) / history. Fix availability 는 affected 의 `fixed_in` 으로 흡수됨. 별도 "Fix availability" 섹션 없음
- **분류**: 📝 매뉴얼 오류 — 섹션 분류 정정

### vulns-4-2 (RBAC: developer or higher save) — ✅ 일치

- **검증 방법**: `vulnerabilities.spec.ts:211` (S5 developer cannot suppress)
- **분류**: ✅ 일치 (developer 는 일부 transition 가능, suppression 은 team_admin 필요)

### vulns-5-1~5-3 (Re-detection / banner / notify) — ⏭ 보류

- **분류**: ⏭ 보류 (DT NVD ingest + SMTP/Slack/Teams 외부 의존)

### vulns-7-2 (audit log `vuln_finding.update`) — ⏭ 보류

- **분류**: ⏭ 보류 (super_admin 페르소나)

### vulns-8-1~8-3 (Trbl) — ⏭ 보류

- **분류**: ⏭ 보류 (정책 / drift 진단 가이드)

---

## 4. user-guide/components-and-licenses.md

### comps-1-1 (6 컬럼) — 📝 매뉴얼 오류

- **단계**: Name / Version / Type / Concluded license / Classification / Findings
- **검증 방법**: Tier 1 — `project_detail.json:87-95` `components.col.*`
- **관찰 결과**: 실제 컬럼 = Component (name) / Version / License / Severity / CVEs (5 컬럼). **"Type" 컬럼 없음, "Classification" 별도 컬럼 없음 (Severity 와 통합), "Concluded license" 라벨 단순화**
- **분류**: 📝 매뉴얼 오류

### comps-1-2 (virtualized) — ✅ 일치

- **검증 방법**: `project_detail.spec.ts:125` (S2: 250 rows + scroll → endReached)
- **분류**: ✅ 일치

### comps-2-1~2-4 (Filter — Classification / License / Has open CVE / Search) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `ComponentsToolbar.tsx:22-42` (option lists)
- **관찰 결과**: 실제 filter = search + severity (multi) + license category (Allowed/Conditional/Forbidden/Unknown, multi) + sort + order. **"License (exact SPDX)" filter 없음, "Has open CVE" 토글 없음**. License category multi-select 는 일치
- **분류**: 📝 매뉴얼 오류 — 두 filter 부재. Phase 4 정정 권고

### comps-3-1~3-6 (Drawer 6 섹션) — 📝 부분 매뉴얼 오류 + ⏭ 보류

- **단계**: Identity / All license findings (declared/detected/concluded) / Obligations / CVEs / Approval status / Override concluded license
- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/components/ComponentDrawer.tsx`
- **관찰 결과**:
  - Identity (purl), CVEs deep-link 는 가드 있음 (`project_detail.spec.ts:155, 175`)
  - **Override concluded license UI 부재** (team_admin override 기능 없음)
  - **Approval status 행 부재** (drawer 에서 approval 상태 보기 없음 — Approvals 페이지 별도)
- **분류**: 📝 매뉴얼 오류 (override + approval 행 부재)

### comps-4-1 (License classification 표 4 tier) — ✅ 일치

- **검증 방법**: `licenses.spec.ts:96` (S1 4 legend buckets present) + `LICENSE_OPTIONS` 4개
- **분류**: ✅ 일치

### comps-6-1 (Obligations 7 종) — ✅ 일치

- **검증 방법**: Tier 1 — `project_detail.json:333-340` `obligations.kind.*` 7개
- **관찰 결과**: 7 종 정확 (attribution / notice / source-disclosure / copyleft / modifications / dynamic-linking / no-endorsement)
- **분류**: ✅ 일치

### comps-6-2 (Generate NOTICE 다운로드) — ✅ 일치

- **검증 방법**: `obligations.spec.ts:161` (S4 NOTICE download with filename + body)
- **분류**: ✅ 일치

---

## 5. user-guide/sbom.md

### sbom-1-1 (4 포맷 표) — 📝 매뉴얼 오류 (라벨 미스매치)

- **단계**: cyclonedx-json / cyclonedx-xml / spdx-json / **spdx-tag-value**
- **검증 방법**: Tier 1 — `apps/backend/api/v1/sbom.py:50` `SBOMFormat`
- **관찰 결과**: 실제 enum = `cyclonedx-json`, `cyclonedx-xml`, `spdx-json`, **`spdx-tv`** (not `spdx-tag-value`). manual 의 format 값 그대로 호출하면 422
- **분류**: 📝 매뉴얼 오류 — `spdx-tag-value` → `spdx-tv` 정정 필요

### sbom-3-1 (UI: SBOM 탭 → dropdown → Download) — ⏭ Tier 2 보류

- **검증 방법**: Tier 1 — `SbomTab.tsx` 존재 확인
- **관찰 결과**: SbomTab 컴포넌트 존재. dynamic 검증은 disk full 로 보류
- **분류**: ⏭ 보류

### sbom-4-1~4 (API curl 4개) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/api/v1/sbom.py:43,90`
- **관찰 결과**: 실제 path = `/v1/projects/{id}/sbom?format=...` (no `/api` prefix). manual `/api/v1/...` 호출은 404
- **분류**: 📝 매뉴얼 오류

### sbom-5-3 (NOTICE API: GET /api/v1/projects/{id}/notice) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/api/v1/obligations.py:246-247` `/projects/{project_id}/notice`
- **관찰 결과**: prefix `/v1`. manual `/api/v1/...` 호출은 404
- **분류**: 📝 매뉴얼 오류

### sbom-6-1~3 (Excel + PDF reports — Components Excel / Vulnerabilities Excel / Compliance PDF) — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류 (큰 drift)

- **검증 방법**: Tier 1 — `apps/backend/api/v1/` 에서 `/reports`, `xlsx`, `pdf`, `compliance` grep
- **관찰 결과**: **`/reports` endpoint 자체 부재. xlsx/pdf 코드 한 줄도 없음. UI 에 "Reports" 메뉴 없음.** v2.0.0 시점에 미구현 기능
- **분류**: 📝 매뉴얼 오류 (가장 큰 drift) — Phase 4 권고: 페이지 전체 ("## Excel & PDF reports" 섹션) 를 "(roadmap — v2.1+)" 로 마크하거나 삭제

### sbom-6-4 ⚠ (UI: Project → Reports menu (top-right of any tab)) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/frontend/src/features/projects/ProjectDetailPage.tsx` 에서 Reports 메뉴 grep
- **관찰 결과**: ProjectDetailPage 에 Reports 메뉴 없음. matrix ⚠ 의심 = 정확한 drift
- **분류**: 📝 매뉴얼 오류 (확인됨)

### sbom-7-1 (VEX 매핑 표 7 행) — ⏭ 보류

- **검증 방법**: Tier 1 — `apps/backend/services/sbom_export.py` 또는 cyclonedx exporter 에서 매핑 코드 grep 필요
- **분류**: ⏭ 보류

### sbom-8-1, 8-2 (cyclonedx validate / pyspdxtools) — ⏭ 보류 (외부 cli)

- **분류**: ⏭ 보류

---

## 6. user-guide/approvals.md

### approvals-1-1 (4 state) — ✅ 일치

- **검증 방법**: Tier 1 — `APPROVAL_STATUS_VALUES = ("pending", "under_review", "approved", "rejected")` (`apps/backend/models/component_approval.py:56`)
- **분류**: ✅ 일치

### approvals-2-1 (사이드바 Approvals → filter 5종) — 📝 매뉴얼 오류

- **단계**: filter — state / project / license / component / requested-by
- **검증 방법**: Tier 1 — `ApprovalsPage.tsx:130-200`
- **관찰 결과**: 실제 filter = status (state) + date range. **project / license / component / requested-by 4 filter 부재**
- **분류**: 📝 매뉴얼 오류

### approvals-2-2 (행 6 필드) — 📝 매뉴얼 오류

- **단계**: 컴포넌트 / license / 영향 프로젝트 (다수) / requested ts / reviewer / justification
- **검증 방법**: Tier 1 — `ApprovalsPage.tsx:230-249` 6 컬럼
- **관찰 결과**: 실제 컬럼 = Component / Project (단수) / Status / Requested by / Requested at / Actions. **License 컬럼 없음, Reviewer 컬럼 없음, Justification 컬럼 없음, Affected projects 다수 표시 부재 (1 row = 1 project 1 component)**
- **분류**: 📝 매뉴얼 오류

### approvals-3-1 (자동 Pending 생성) — ⏭ 보류

- **단계**: scan 후 conditional license → 자동 Pending row
- **검증 방법**: scan 가 worker 의존 (현재 stale)
- **분류**: ⏭ 보류 (Tier 1 로 service 코드 reading 가능: `services/approval_service.py:create_approval`)

### approvals-3-2 (사이드바 → Approvals → New request → 폼) — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류

- **단계**: 수동 New request 가능
- **검증 방법**: Tier 1 — `ApprovalsPage.tsx` 에서 "New request" 버튼 grep
- **관찰 결과**: ApprovalsPage 에 "New request" 버튼/UI 없음. **POST endpoint (`/v1/approvals`) 는 존재하지만 UI 비노출**
- **분류**: 📝 매뉴얼 오류 — UI 미구현. Phase 4 권고: 매뉴얼에서 "New request UI" 섹션 (3 단계) 삭제 또는 "(API only — UI in v2.1+)" 표시

### approvals-4-2 (Claim 버튼) — 📝 매뉴얼 오류 (라벨 drift)

- **단계**: "Claim 클릭 → Under Review"
- **검증 방법**: Tier 1 — `ApprovalsDrawer.tsx:9-11` 의 주석 + 라벨 코드
- **관찰 결과**: 실제 버튼 라벨 = **"Start Review"** (not "Claim"). 매뉴얼은 "Claim" 으로 표기
- **분류**: 📝 매뉴얼 오류

### approvals-4-3 (Approve / Reject + ≥10 char justification) — ✅ 일치

- **검증 방법**: Tier 1 — drawer 의 두 버튼 존재 (`ApprovalsDrawer.tsx:213-234`)
- **분류**: ✅ 일치 (10 char 검증은 backend service 영역)

### approvals-5-1 (Bulk: team_admin+ multi-select bulk verdict) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/services/approval_service.py` + `apps/backend/api/v1/approvals.py` + `ApprovalsPage.tsx` 에서 bulk grep
- **관찰 결과**: bulk endpoint 부재. multi-select UI 부재
- **분류**: 📝 매뉴얼 오류

### approvals-7-1 (external Jira webhook) — ⏭ 보류

- **분류**: ⏭ 보류 (외부 Jira)

---

## 7. user-guide/auth-and-profile.md

### auth-1-3 (login 성공 → 토큰 + redirect) — ✅ 일치

- **검증 방법**: `auth.spec.ts:27` (register → auto-login)
- **분류**: ✅ 일치

### auth-1-4 (보안 정책 — bcrypt 12, access 30min, refresh 7d, rotation, reuse-detection, HttpOnly+Secure+SameSite=Lax, login 5/min/IP) — ✅ 일치

- **검증 방법**: Tier 1 — `apps/backend/core/security.py:_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)`, `core/config.py:ACCESS_TOKEN_EXPIRE_MINUTES = 30 / REFRESH_TOKEN_EXPIRE_DAYS = 7`, `apps/backend/services/auth_service.py:test_refresh_rotates_and_detects_reuse` (integration test 가 회전 + 재사용 탐지 가드)
- **분류**: ✅ 일치 (모든 보안 정책 정확)

### auth-1-5 ("Invalid email or password" 일반 메시지 — anti-enumeration) — ✅ 일치

- **검증 방법**: `auth.spec.ts:55` (expectAlert)
- **분류**: ✅ 일치

### auth-2-2 (forgot password — 항상 204) — ✅ 일치

- **검증 방법**: `auth.spec.ts:147` (forgot-success visible regardless)
- **분류**: ✅ 일치

### auth-3-1, 3-3 (reset → /login redirect, refresh 토큰 모두 revoke) — ⏭ 부분 보류

- **검증 방법**: Tier 1 — backend reset_password 코드 reading
- **분류**: ⏭ 보류 (refresh revoke 자체 검증은 unit 영역)

### auth-4-1 (OAuth 버튼 노출) — ✅ 일치

- **검증 방법**: `auth.spec.ts:187`
- **분류**: ✅ 일치

### auth-4-5 (OAuth 7 error codes) — ✅ 부분 일치

- **검증 방법**: `auth.spec.ts:172` (oauth_denied 만 가드)
- **관찰 결과**: backend `apps/backend/api/v1/oauth.py` 에 7 error codes 존재 여부는 코드 reading 필요. 1 가드만 있음
- **분류**: ⏭ 보류 (Phase 5 E2E 권고)

### auth-5-1 (`/profile` — Password / GitHub / Google identity list) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/frontend/src/features/profile/UserProfilePage.tsx`
- **관찰 결과**: profile page 는 OAuth identities 만 list (`Connected Accounts` 섹션). **Password row 없음.** "Set a password" 액션 본문에서 언급되지만 별도 row 로 노출 X
- **분류**: 📝 매뉴얼 오류

### auth-5-2 (Unlink — 마지막 sign-in method 시 409) — ✅ 일치

- **검증 방법**: Tier 1 — `apps/backend/api/v1/users_me.py:184` `oauth_unlink_blocks_login` 409 + `UserProfilePage.tsx:55` `isUnlinkBlocksLogin` 처리
- **분류**: ✅ 일치

### auth-5-3 (linking 새 provider — sign out → 새 provider sign in → 자동 attach) — ⏭ 보류

- **분류**: ⏭ 보류 (외부 provider)

### auth-6-1 (Verify: header avatar + active team) — ⏭ 부분 보류

- **검증 방법**: Tier 1 — `AppShell.tsx` grep
- **분류**: ⏭ 보류

---

## 8. user-guide/notifications.md

### notif-1-1 (헤더 bell unread badge — 0 / 1-99 / 99+) — ✅ 일치

- **검증 방법**: Tier 1 — `apps/frontend/src/components/HeaderBell.tsx:32-36` `formatBadge`
- **관찰 결과**: `if (count > 99) return "99+"` 정확. count 0 = 빈 string (badge 숨김)
- **분류**: ✅ 일치

### notif-1-2 (bell 클릭 → 5 most recent dropdown) — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류

- **단계**: bell 클릭 → 5 most recent dropdown
- **검증 방법**: Tier 1 — `HeaderBell.tsx:51` `onClick={() => navigate("/notifications")}`
- **관찰 결과**: bell 은 dropdown 없이 직접 `/notifications` 페이지로 이동. **5-recent dropdown UI 자체 부재**
- **분류**: 📝 매뉴얼 오류 — Phase 4 권고: dropdown 약속 삭제 또는 "(향후 기능 — v2.1+)" 표시

### notif-1-3, 1-4 (행 클릭 / dropdown footer → full inbox) — 📝 매뉴얼 오류

- **분류**: 📝 매뉴얼 오류 — dropdown 부재로 이 단계 자체 무의미

### notif-2-1 (`/notifications` — newest first, infinite scroll page 25) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `NotificationsPage.tsx:454,473` (page label + Previous/Next buttons)
- **관찰 결과**: **infinite scroll 이 아니라 페이지 네비게이션 (Previous / Next 버튼)**
- **분류**: 📝 매뉴얼 오류

### notif-3-1 (Preferences — channel × trigger toggle 4채널×5트리거 매트릭스) — 🐛 시스템 버그 (Low) 또는 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `NotificationsPage.tsx:189-217` 4 toggle (email/slack/teams/in_app) 글로벌만, **per-trigger 매트릭스 자체 부재**
- **관찰 결과**: 실제 prefs = 4 channel global toggle (per-user). per-trigger fine-grained control 없음
- **분류**: 📝 매뉴얼 오류 (per-trigger control 미구현)

### notif-3-6 (toggle 즉시 저장, Save button 없음, toast feedback) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `NotificationsPage.tsx:225-228` (Save button + draft state)
- **관찰 결과**: **Save 버튼이 명시적으로 존재** (`testid="notifications-prefs-save"`). draft state 와 Dirty check (`isDirty` line 174-177). manual 의 "즉시 저장 + Save 없음" 은 시스템과 정반대
- **분류**: 📝 매뉴얼 오류 — Phase 4 정정 권고

### notif-4-1 (bell polling 60s, hidden 일시정지, focus 즉시 poll) — ✅ 일치

- **검증 방법**: Tier 1 — `useNotifications.ts:70-74` `refetchInterval: 60_000, refetchIntervalInBackground: false`
- **분류**: ✅ 일치 (focus 즉시 poll 은 TanStack Query default refetchOnWindowFocus 가 처리)

### notif-5-1 (5 trigger 표 — `scan_finished` / `gate_failed` / `new_cve` / `approval_request` / `disk_pressure`) — 📝 매뉴얼 오류 (큰 drift)

- **검증 방법**: Tier 1 — `apps/backend/models/notification.py:66-73` `NOTIFICATION_KIND_VALUES`
- **관찰 결과**: 실제 trigger = `scan_completed`, `scan_failed`, `cve_detected`, `license_violation`, `approval_pending`, `policy_gate_failed` (6개). **manual 5개 이름 모두 다름** (e.g. `scan_finished` ≠ `scan_completed`). **`disk_pressure` 자체 부재.**
- **분류**: 📝 매뉴얼 오류

### notif-6-3 (email 비활성 후 in-app only) — ⏭ 보류

- **분류**: ⏭ 보류 (SMTP 의존 + worker stale)

### notif-7-2, 7-3 (email / Slack 도착 X) — ⏭ 보류 (외부 SMTP / Slack)

- **분류**: ⏭ 보류

---

## 9. user-guide/integrations.md

### integ-1-1 (`/integrations` — API keys + Webhooks 두 탭) — ✅ 일치

- **검증 방법**: `integrations.spec.ts:67` (gotoIntegrations + expectMounted)
- **분류**: ✅ 일치

### integ-2-1 (API keys tab — 5 컬럼 label / prefix / scope / expiry / last-used) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `IntegrationsPage.tsx:225-235` table headers
- **관찰 결과**: 실제 컬럼 = name (label) / prefix / scope / **expires** (column header) / last-used. 컬럼 자체는 5개로 일치. **단, Expiry 표시는 `expires_never` 텍스트만 노출** — 모든 row 가 "Never" 표시 (실제 expiry 미구현)
- **분류**: 📝 매뉴얼 오류 (column 은 있으나 모든 값이 Never — manual 이 약속한 30/90/180/365 등이 무의미)

### integ-2-2 (Create form — Label / Scope (org/team/project) / Expiry (preset 30/90/180/365/custom)) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `CreateApiKeyDialog.tsx:44-83`
- **관찰 결과**: 실제 폼 필드 = name + scope + (team_id or project_id depending on scope). **Expiry 입력 자체 부재** (preset 옵션 없음). backend `APIKeyCreateIn` 도 expiry 필드 없음 (`apps/backend/schemas/api_key.py:36-48`)
- **분류**: 📝 매뉴얼 오류 — Phase 4 권고: Expiry 라인 삭제 또는 "(향후 기능)" 표시. 단, 모든 키가 영구이므로 보안 회귀 가능 (security review 권고)

### integ-2-3 (Create → 일회성 reveal modal `tos_<8>_<32>` + Copy + 경고) — ✅ 일치

- **검증 방법**: Tier 1 — `apps/backend/schemas/api_key.py:67-74` `raw_key` Field doc + `RevealApiKeyDialog.tsx`
- **관찰 결과**: format `tos_<prefix>_<secret>` 정확. RevealApiKeyDialog 컴포넌트 존재
- **분류**: ✅ 일치

### integ-2-4 (Bearer + ApiKey scheme 둘 다 가능) — ⏭ 부분 보류

- **검증 방법**: Tier 1 — `apps/backend/core/security.py` 또는 api_keys auth handler grep
- **분류**: ⏭ 보류 (실제 두 scheme 둘 다 수용하는지 확인 필요)

### integ-2-5 (GitHub Actions / Jenkins 예제 코드) — ✅ 일치 (시각/copy 검증)

- **분류**: ✅ 일치 (예제 코드는 표준 형식)

### integ-2-6 (Revoke — hover row → Revoke → confirm. 즉시 무효화 (~5s cache TTL)) — ⏭ 부분 보류

- **검증 방법**: Tier 1 — `RevokeApiKeyDialog.tsx` 존재 + backend revoke endpoint
- **분류**: ⏭ 보류 (5s cache TTL 검증은 unit 영역)

### integ-3-1, 3-2 (Webhooks tab — fixed URLs, GitHub `/v1/webhooks/github` + HMAC X-Hub-Signature-256) — ✅ 일치

- **검증 방법**: Tier 1 — `apps/backend/api/v1/webhooks/github.py:41` `prefix="/v1/webhooks"`
- **관찰 결과**: path 정확 (`/v1/webhooks/github`). HMAC 검증 코드 존재. **manual 의 path "https://<your-host>/v1/webhooks/github" 도 정확** (api 는 `/v1` prefix 사용)
- **분류**: ✅ 일치 (이 페이지의 webhook URL 만 매뉴얼 전체에서 path 가 `/v1/...` 로 정확. 다른 페이지의 `/api/v1/...` 와 일관성 깨짐)

### integ-3-3 (GitLab `/v1/webhooks/gitlab` + X-Gitlab-Token) — ✅ 일치

- **검증 방법**: `apps/backend/api/v1/webhooks/gitlab.py:42`
- **분류**: ✅ 일치

### integ-3-4 (Project Settings → CI/CD → webhook_secret 생성/rotate) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `SettingsTab.tsx` 전체 reading
- **관찰 결과**: SettingsTab 는 4 필드만 노출 (name/description/git_url/default_branch). **CI/CD subtab 자체 부재. webhook_secret 생성/rotate UI 자체 없음.** model 에 `webhook_secret` 컬럼은 있지만 UI 노출 / API endpoint 노출 X
- **분류**: 📝 매뉴얼 오류 — Phase 4 권고: 큰 drift, "## Rotate a webhook secret" 섹션 통째로 "(향후 기능)" 표시

### integ-3-5 (rotate 후 old secret ~5s 내 reject. 401) — 📝 매뉴얼 오류

- **분류**: 📝 매뉴얼 오류 (rotate 자체 미구현)

### integ-4-1 (Verify: curl 200 with team's projects) — 📝 매뉴얼 오류

- **단계**: `/api/v1/projects`
- **관찰 결과**: prefix 부재 — `/v1/projects`
- **분류**: 📝 매뉴얼 오류

### integ-4-3 (Verify: audit log `api_key.create` + `webhook.delivery` events. /admin/audit super_admins, /audit team admins) — 📝 매뉴얼 오류

- **검증 방법**: Tier 1 — `apps/backend/api/v1/admin/audit.py:123` `require_super_admin_or_404`
- **관찰 결과**: audit endpoint 는 **super_admin only**. team_admin 용 `/audit` endpoint 부재
- **분류**: 📝 매뉴얼 오류 — Phase 4 권고: "or `/audit` for team admins" 삭제

### integ-5-1~5-3 (401 / 403 / 429 응답) — ⏭ 부분 보류

- **검증 방법**: Tier 1 — `apps/backend/core/security.py` rate limit 코드
- **분류**: ⏭ 보류 (per-key rate limit 동작 검증은 dynamic 필요)

### integ-5-4, 5-5 (GitHub/GitLab webhook 401) — ⏭ 보류 (외부)

- **분류**: ⏭ 보류

---

## 발견된 시스템 버그 요약 (Phase 4 입력)

| ID | Severity | 증상 | 영향 page |
|----|----------|------|-----------|
| BUG-USR-001 | Medium | Project 영구 삭제 (Delete) 기능 부재 — backend DELETE = soft-delete (archive) 만, UI 에 typed-name confirmation modal 없음 | projects |
| BUG-USR-002 | Low | Scan cancel API 부재 — manual 이 약속한 `DELETE /v1/scans/{id}` 없음. UI 에 cancel 버튼 없음 | scans |

(다수의 "기능 부재" 는 매뉴얼이 약속한 것을 시스템이 미구현 = 매뉴얼 오류로 분류. 시스템 버그는 의도된 기능이 잘못 동작하는 케이스에 한정)

## 발견된 매뉴얼 오류 요약 (Phase 4 입력)

| ID | 페이지 | 매뉴얼 주장 | 실제 동작 | EN/KO 모두 수정 필요 |
|----|--------|------------|----------|---------------------|
| MAN-USR-001 | projects | Anatomy 7 필드 (Container image, Tags, Owning team, Repository URL) | 실제 필드는 name/description/git_url/default_branch + (PATCH 만) visibility — 5 필드 | ✓ |
| MAN-USR-002 | projects | Create 폼 Default branch / Visibility / Container image 입력 | 실제 폼은 name/description/git_url 3 필드 | ✓ |
| MAN-USR-003 | projects, scans, vulnerabilities, sbom, integrations | API path 가 `/api/v1/...` | 실제는 `/v1/...` (모든 curl 예제 정정 필요) | ✓ |
| MAN-USR-004 | projects | Visibility = `team_only` / `org_wide` | 실제 enum = `team` / `organization`, `organization` 은 reject | ✓ |
| MAN-USR-005 | projects | Tags 추가/변경 | tags 컬럼 부재 | ✓ |
| MAN-USR-006 | projects | Project Settings → Repository → SSH deploy key 생성 | deploy key UI 자체 부재 | ✓ |
| MAN-USR-007 | projects | Repository URL invalid — wizard validates HTTPS / git@ / ssh:// | Frontend 는 HTTPS only (정규식), Backend 만 ssh 수용 | ✓ |
| MAN-USR-008 | scans | 우측 상단 Scan 버튼 → kind 선택 dialog → branch override → Start scan | 실제는 ProjectListPage 의 "Scan" 버튼만, dialog 없음, source hardcoded | ✓ |
| MAN-USR-009 | scans | Lifecycle 의 cancelled = `DELETE /v1/scans/{id}` | DELETE endpoint 부재, cancel API 없음 | ✓ |
| MAN-USR-010 | scans | WebSocket path `wss://<host>/api/v1/scans/{id}/progress` + 메시지 shape `{scan_id, stage, progress, message, ts}` | 실제 path `ws://<host>/ws/scans/{scan_id}` + shape `{percent, step, ts}` | ✓ |
| MAN-USR-011 | scans | Verify: project status switches to **Completed** | 실제 라벨 = **Succeeded** (lifecycle 표와 일관성 위반은 manual 의 verify 섹션) | ✓ |
| MAN-USR-012 | vulnerabilities | 6 컬럼 (CVE / Component / Severity / State / Discovered / Last seen) | 실제 = cve_id / severity / cvss / summary / affected / status / discovered. "Last seen" 부재, "CVSS" + "Title" 추가 | ✓ |
| MAN-USR-013 | vulnerabilities | filter — severity / state / component / discovered range | 실제 = severity + status + search + sort + order. component / discovered range 없음 | ✓ |
| MAN-USR-014 | vulnerabilities | Drawer 6 섹션 — Affected versions / Fix availability 별도 | Affected (with fixed_in) / Analysis / History — Fix availability 가 affected 안 으로 흡수 | ✓ |
| MAN-USR-015 | components-and-licenses | 6 컬럼 (Name/Version/Type/Concluded license/Classification/Findings) | 실제 = Component/Version/License/Severity/CVEs (5). Type, Classification 별도 컬럼 부재 | ✓ |
| MAN-USR-016 | components-and-licenses | filter — Classification / **License (exact SPDX)** / **Has open CVE** / Search | 실제 = search + severity + license category + sort + order. exact SPDX 필터 없음, Has open CVE 토글 없음 | ✓ |
| MAN-USR-017 | components-and-licenses | drawer — All license findings / **Approval status** / **Override concluded license** | 실제 drawer 에 approval status row 없음, override UI 없음 | ✓ |
| MAN-USR-018 | sbom | 4 포맷 — `spdx-tag-value` | 실제 = `spdx-tv` (manual 값 호출 시 422) | ✓ |
| MAN-USR-019 | sbom | Excel/PDF reports — Components Excel / Vulnerabilities Excel / Compliance PDF + Project → Reports menu | `/reports` endpoint 자체 부재. xlsx/pdf 코드 없음. UI 에 Reports 메뉴 없음 | ✓ |
| MAN-USR-020 | approvals | filter — state / project / license / component / requested-by | 실제 = status + date range. 4 filter 부재 | ✓ |
| MAN-USR-021 | approvals | 행 6 필드 (component, license, 영향 프로젝트 다수, requested ts, **reviewer**, **justification**) | 실제 = Component/Project/Status/Requested by/Requested at/Actions. License/Reviewer/Justification 컬럼 없음 | ✓ |
| MAN-USR-022 | approvals | "New request" UI 폼 (Project / purl / Justification) | UI 자체 부재 (POST endpoint 만 존재) | ✓ |
| MAN-USR-023 | approvals | "Claim" 버튼 | 실제 라벨 = **"Start Review"** | ✓ |
| MAN-USR-024 | approvals | Bulk multi-select + bulk verdict | bulk endpoint / UI 자체 부재 | ✓ |
| MAN-USR-025 | auth-and-profile | `/profile` 에 **Password** identity row | OAuth identities 만 노출. Password 별도 row 없음 (본문에서만 mention) | ✓ |
| MAN-USR-026 | notifications | bell 클릭 → 5 most recent dropdown | bell 은 `/notifications` 로 직접 navigate. dropdown 자체 없음 | ✓ |
| MAN-USR-027 | notifications | `/notifications` newest first, **infinite scroll** page 25 | 실제는 페이지 네비게이션 (Previous / Next 버튼) | ✓ |
| MAN-USR-028 | notifications | Preferences — **channel × trigger** 매트릭스 4×5 | 실제는 4 channel global toggle 만, per-trigger fine-grained 없음 | ✓ |
| MAN-USR-029 | notifications | toggle 즉시 저장, **Save 없음**, toast feedback | 실제는 **Save 버튼 명시적 존재** + draft state. 정반대 | ✓ |
| MAN-USR-030 | notifications | 5 trigger 이름 (`scan_finished`/`gate_failed`/`new_cve`/`approval_request`/`disk_pressure`) | 실제 = `scan_completed`/`scan_failed`/`cve_detected`/`license_violation`/`approval_pending`/`policy_gate_failed` (6, 모든 이름 다름). disk_pressure 부재 | ✓ |
| MAN-USR-031 | integrations | API key Create — Expiry preset 30/90/180/365/custom | expiry 필드 자체 부재 (모든 키 영구) | ✓ + 보안 review 권고 |
| MAN-USR-032 | integrations | Project Settings → CI/CD → webhook_secret 생성/rotate | CI/CD subtab 자체 부재. webhook_secret rotate UI 없음 | ✓ |
| MAN-USR-033 | integrations | audit log `/admin/audit` for super_admins, `/audit` for team admins | `/audit` (team_admin) endpoint 부재 — super_admin only | ✓ |

(33 매뉴얼 오류 — 모두 EN + KO mirror 정정 필요)

## ⏭ 보류 항목 (Phase 5 자동화 또는 운영자 직접 검증)

| ID | 단계 | 사유 |
|----|------|------|
| HOLD-USR-001 | auth-4-2 (OAuth provider consent screen) | 외부 GitHub/Google consent 화면 |
| HOLD-USR-002 | auth-4-3, 4-4, 5-3 | 외부 OAuth provider 흐름 |
| HOLD-USR-003 | auth-4-5 (OAuth 7 error codes) | 6 error 가드 부재. Phase 5 E2E 권고 |
| HOLD-USR-004 | scans-3-2-1~6 (Pipeline stages) | worker stale (aiosmtplib missing) — Phase 4 worker rebuild 후 dynamic 검증 |
| HOLD-USR-005 | scans-3-3 (DT outage simulation) | Phase 5 E2E 권고 |
| HOLD-USR-006 | scans-8-1 (worker / docker-compose 진단) | 호스트 docker-compose 명령 — 운영자 |
| HOLD-USR-007 | sbom-8-1, 8-2 (cyclonedx validate / pyspdxtools) | 외부 cli |
| HOLD-USR-008 | approvals-7-1 (Jira webhook) | 외부 Jira |
| HOLD-USR-009 | notif-3-3, 3-4, 3-5, 6-3, 7-2, 7-3 | SMTP / Slack / Teams 외부 (worker stale 도 영향) |
| HOLD-USR-010 | integ-2-6 (Revoke 5s cache TTL) | unit 영역 |
| HOLD-USR-011 | integ-4-2 (GitHub push → Webhook deliveries) | 외부 GitHub |
| HOLD-USR-012 | integ-5-4, 5-5 (HMAC mismatch on outside webhook) | 외부 GitHub/GitLab |
| HOLD-USR-013 | vulns-1-2 (per-project gate config UI) | 별도 grep 필요 — Phase 5 E2E 권고 |
| HOLD-USR-014 | vulns-5-1 (DT NVD ingest 자동 재상관) | 외부 DT NVD ingest |
| HOLD-USR-015 | comps-7-1 (SPDX 파싱 — `LicenseRef-`, oversized 등) | unit + adversarial parametrize 권고 |
| HOLD-USR-016 | sbom-7-1 (VEX 매핑 7 행) | sbom_export 코드 reading 필요 |
| HOLD-USR-017 | projects-9-3, vulns-7-2 (audit log 검증) | super_admin 페르소나 → Phase 3 admin walkthrough |
| HOLD-USR-018 | 모든 시각 / Copy 검증 (color token, badge layout, 라벨 위치) | UI 시각 회귀 — 가치-비용 낮음, Phase 5 우선순위 X |

---

## 환경 안정성 권고 (Phase 4 chore 후보)

별도 chore 로 분리 권고 (본 walkthrough 의 부산물):

1. **Postgres dev volume disk full** — `docker-compose down -v` (별도 backup 필요) + 재기동, 또는 unused image/volume 정리
2. **celery-worker `aiosmtplib` ModuleNotFoundError restart loop** — Chore P 머지 (5cdebbc) 이후 worker 이미지 재빌드 미수행. `docker-compose -f docker-compose.dev.yml build worker && docker-compose up -d worker` 필요. 본 walkthrough 의 dynamic 검증이 부분적으로 막힌 원인
3. **API path 일관성 (frontend / docs / scripts)** — Frontend 와 backend 는 `/v1/...` 사용. 매뉴얼 / docs / 외부 스크립트 예제는 `/api/v1/...` 사용. 통일 권고 (방향: backend 가 `/api/v1` prefix 추가, OR 매뉴얼 모두 `/v1` 로 정정 — 후자가 더 작은 변경)

---

## 다음 세션 권고

- **세션 3 (Phase 3 — Admin walkthrough)** 진행. Super Admin 6 페이지 (users-and-teams / dt-connector / disk-and-health / audit-log / backup-and-restore / api-keys). matrix 의 admin ⚠ 4 항목 (u&t-9-1 last-super-admin, disk-1-1 8 components, disk-1-2 ok vs healthy, disk-3-1 gauge vs card) 우선
- **세션 4 (Phase 4 — Triage)** 가 본 walkthrough + admin walkthrough 결과를 분류:
  - 33 매뉴얼 오류 → `chore/user-guide-drift-fixes` PR (EN + KO mirror)
  - 2 시스템 버그 → severity 별 issue 등록 (BUG-USR-001 Medium, BUG-USR-002 Low)
  - 환경 chore 3 → backlog 등재
- **세션 5 (Phase 5 — E2E)** 가 P0 ⚠ 의심 단계에 회귀 가드 추가
- **세션 6 (Phase 6 — CI gate)** 가 manual-aligned E2E 를 CI 에 통합
