# 정리된 코드 계층과 보존 정책

## 사용 (기본 경로)

| 구성 요소 | 용도 | 변경 여부 |
|---|---|---|
| `e2core` | Journal 검증·해시·모델 호출·Controller 스키마 | 변경 없음 |
| `scientific_problem_evolution.py` (V2) | Novelty / PMI / Claim·Problem Delta | 변경 없음 |
| `scientific_closed_loop_v3.py` (V3) | 과학적 이벤트 재평가·런타임 | 변경 없음 |
| `scientific_research_readiness_v4.py` (V4) | 실험 전 이론 준비성 구분·INFORMED 인계 | 변경 없음 |
| `scientific_v4_clean_baseline.py` | 안전한 D77 스냅샷 분기·검증·실행 단일 진입점 | 새로 추가 |

V5 판단표/마이그레이션/복구 시스템은 이번 실행 경로에서 사용하지 않는다.

## 왜 D00077인가?

V4 실제 실행에서 마지막 성공한 Controller 결정은 D00077이고, D00078은 V5로 넘어가는 과정에서 호출 재생 충돌과 계획 검증 실패를 겪었다. 새 분기는 원본 V4의 마지막으로 커밋된 Controller 결정까지의 이벤트 접두부에서 출발한다. 이후 V4에서 추가된 연구 자료가 있다면 그것도 의도적으로 제외되므로 `source-audit`와 별도 승인이 필수다.

## 원본 Journal 보존

1. 원본 전체 Journal(`SRC`)을 먼저 검증하고 추가 UNCERTAIN/INTENT를 거부한다.
2. `CONTROLLER_DECISION D00077`의 위치와 서명·후속 이벤트를 감사한다.
3. 파일/Blobs 전체를 별도 staging 디렉터리에 복사한다.
4. 새 디렉터리에서만 D77 뒤의 이벤트 파일들을 제외한다(원본 파일은 손대지 않음).
5. 접두부의 **해시가 원본과 정확히 일치하는지** 검증한다.
6. 계승된 P0/모델 호출/자산·Work 상태를 검증한 후 운영 영수증을 1개 append한다.
7. 배포되기 전 `v4.inspect()`까지 실행해 실제 V4 계약을 통과해야 한다.
8. 원본 HEAD 변경 검사 후 staging을 최종 목적지로 이동한다.

원본의 D77 뒤 이벤트는 삭제되지 않는다. 새 분기가 제외한 이벤트 ID와 종류 및 원본 HEAD의 SHA256을 영수증에 남긴다. 이어지는 모델 호출은 새 과금 가능성이 있다. 최초 NVT UNCERTAIN과 공식 재발행 SAVED는 접두부에 남겨 둔다.

## 별도 후속 리팩터링 후보 (미구현)

- `V3/V4`의 monkey-patch 기반 prompt/runtime 조합을 독립적인 policy object로 옮겨 의존성 분리.
- 단일 단계에서 4번 이상 중복 호출되는 검증·Journal 전체 스캔 비용을 계측 후 최적화.
- 기회별 연구 선택에 대한 모델 판단과 실제 P0 연구의 정보 가치를 동일시하지 않도록 반례·누적 판단을 검증.
- 운영 오류 `MODEL_REPLAY_INPUT_CHANGED`, `E3R1_BAD_PORTFOLIO_SOURCES`, provider preflight를 공통 운영 진단으로 분리.

새 모델 판단 정책은 이 기준선에서 임의로 수정하지 않는다. 과학적 연구 행동의 개선은 별도 branch에서 새 baseline을 비교해 시험한다.
