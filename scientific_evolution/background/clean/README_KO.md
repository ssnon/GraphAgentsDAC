# Scientific V4 — Clean Baseline / D00077 Checkpoint (2026-10-29)

## 의도와 한계

**V5의 실패한 D00078 Controller 응답을 복구하지 않는다.** 원본 V4 연구 ROOT의 **마지막으로 정상 커밋된 Controller 결정 D00077**까지의 Journal 접두부를 검증한 후 새로운 연구 분기를 만든다. 원본 V4/V5 ROOT는 수정하지 않는다. V5의 Arbitrator/복구 패치와 과학적 판단 정책을 새 분기에 포함하지 않는다.

이 패키지는 원래 과학적 판단 엔진 `e2core + V2 + V3 + V4`의 소스를 바꾸지 않고, 운영 진입점만 단일화하는 **안전한 1차 코드 정리**다. V4의 과학적 연구 선택 병목 (`actions=[]` 지속)은 해결되지 않았으며, 이 패키지는 Level II 후보를 생성한다고 주장하지 않는다. V3–V4 monkey-patch 의존성 자체를 제거하는 심층 리팩터링도 아직 수행하지 않았다. 그러한 변경은 과학적 결정의 재현성을 해칠 수 있어 별도 단계로 남긴다.

## 구성

- `scientific_v4_clean_baseline.py`: `source-audit`, `fork`, `inspect`, `run` 단일 진입점.
- `tests/`: 독립적인 무과금 Journal 분기, SHA/P0/UNCERTAIN 보존, 유료 실행 사전 차단 테스트.
- `ARCHITECTURE_KO.md`: 코드 계층, 사용/보류 모듈, 복구 경계.
- `SHA256SUMS.txt`: 배포물 검사.

## 적용 전 필독: D00077 이후 자료 제외

이 방식은 **V4 현재 ROOT 전체를 복사하는 일반적인 fork가 아니라 과거 커밋 시점의 새 분기 생성**이다. D00077 이후에 별도로 작성된 문헌·자산·Worker 단계가 있다면 **새 분기에는 계승되지 않는다.** 해당 자료는 원본 V4 ROOT에서 계속 읽을 수 있고, 새 분기에는 제외된 이벤트 ID/종류와 원본 해시를 감사 영수증으로 남긴다.

D00077 이후 `MODEL_CALL_SAVED`로 저장된 응답은 새 분기에 포함되지 않는다. 이 상태에서 연구를 계속하면 **이미 과금된 질문이 새로 호출될 수 있다.** 따라서 자동으로 제외하지 않고 두 가지 명시적 승인 플래그를 요구한다:

1. `--acknowledge-excluded-saved-calls`: 유료 호출 재발생 가능성 인지.
2. `--acknowledge-excluded-scientific-events`: D00077 이후 과학적 자산·Worker 진행 기록이 새 분기에서 제외될 수 있음을 인지.

기본은 두 플래그 없이 실행을 차단한다. 미해결/UNCERTAIN 호출이 추가로 생긴 원본은 무조건 차단한다. 과거 검증된 최초 NVT UNCERTAIN과 재발행 SAVED 계보는 D00077 이전이므로 그대로 보존된다.

## 1. 설치·검증 (무과금)

ZIP을 `~/FAKG/ForAllKG/SCIENTIFIC_V4_CLEAN_BASELINE_20261029.zip`에 복사한다.

```bash
conda activate graphAgent311
unset FAKG_RESEARCH_ALLOW_PAID
KIT="$HOME/GraphAgentsDAC/patchkits/SERS_DISCOVERY_COHORTS_20261028"
OLDPACK="$KIT/SCIENCE_IDENTIFIABILITY_AND_FRONTIER_20261028"
V2PACK="$KIT/SCIENTIFIC_CLAIM_PROBLEM_DELTA_V2_1_20261028"
V3PACK="$KIT/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028"
V4PACK="$KIT/SCIENTIFIC_RESEARCH_READINESS_V4_20261028"
CLEANPACK="$KIT/SCIENTIFIC_V4_CLEAN_BASELINE_20261029"
PYS="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK:$CLEANPACK"

python -m zipfile -e \
 "$HOME/FAKG/ForAllKG/SCIENTIFIC_V4_CLEAN_BASELINE_20261029.zip" "$KIT"
cd "$CLEANPACK"
sha256sum -c SHA256SUMS.txt
PYTHONPATH="$PYS" python -m unittest discover -s tests -q
```

**주의:** `V5PACK`, `SCIENTIFIC_V5_*` 복구 패키지를 `PYS`에 포함하지 않는다. 기존 `V2PACK` 등 경로는 실제 WSL 설치를 그대로 사용하며 해당 소스 버전은 V3의 PINNED_SOURCE_HASHES로 검증한다. 원본 V4 소스도 별도 SHA256으로 검증한다.

## 2. V4 원본 감사 (무과금·읽기 전용)

```bash
SRC="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_RESEARCH_READINESS_V4_20261028"
NEXT="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_V4_CLEAN_D77_20261029"
PYTHONPATH="$PYS" python scientific_v4_clean_baseline.py source-audit \
 --source-root "$SRC" --last-controller D00077 \
 | tee "$HOME/SCIENTIFIC_V4_CLEAN_SOURCE_AUDIT.json"
```

`checkpoint_controller_id=D00077`, `excluded_model_call_events`, `excluded_scientific_events`, `source_event_count`를 직접 확인한다. 의도와 다르면 fork를 진행하지 않는다.

## 3. D00077 분기 생성 (무과금)

```bash
PYTHONPATH="$PYS" python scientific_v4_clean_baseline.py fork \
 --source-root "$SRC" --out-root "$NEXT" --last-controller D00077 \
 --acknowledge-excluded-saved-calls \
 --acknowledge-excluded-scientific-events

PYTHONPATH="$PYS" python scientific_v4_clean_baseline.py inspect --root "$NEXT"
PYTHONPATH="$PYS" python scientific_v4_clean_baseline.py run --root "$NEXT" --preflight
PYTHONPATH="$KIT" python -m e2core.cli verify --root "$NEXT"
```

`NEXT`가 이미 있으면 덮어쓰지 않는다. `SRC`는 경로·모델 호출·원본 P0 모두 변경되지 않는다. fork는 기존 Journal 접두부를 **바이트 일치**로 재구성한 후, 다른 ROOT에 `V4_CLEAN_COMMITTED_DECISION_CHECKPOINT_FORK_20261029` 운영 영수증 1개를 추가한다. 제외된 이벤트를 새 실험의 증거처럼 숨기거나 V5의 기각된 Controller 결정을 승인하지 않는다.

## 4. 새로운 유료 Pilot (작은 호출 한도)

API 키를 **같은 터미널/tmux 내부**에서 설정한다. 키 자체는 출력하지 않는다.

```bash
[ -n "${OPENROUTER_API_KEY:-}" ] && echo 'KEY PRESENT' || echo 'KEY MISSING'
```

PRESENT라면, V4 소스만 이용해 다음처럼 재개한다.

```bash
cd "$CLEANPACK"
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  PYTHONPATH="$PYS" python scientific_v4_clean_baseline.py run \
    --root "$NEXT" --paid --model openai/gpt-5.6-luna \
    --slice-budget 8 --max-total-new-calls 8 \
    --checkpoint-iterations 12 --max-parallel 2 \
    --max-tokens 16000 --science-cpu-seconds 120 --science-wall-seconds 160 \
    | tee "$HOME/SCIENTIFIC_V4_CLEAN_D77_PILOT.log"
)
```

* 8회는 이번 실행 추가 모델 호출의 상한이며 과학적 Work/STEP 한도는 아니다.
* 원본 V4에는 D00078용 저장 응답이 있지만 정상 Controller 결정으로 커밋되지 않았으므로, **그 저장 응답들을 새 분기에 복사하거나 재생하지 않으며**, 중복 과금 가능성을 사용자가 명시적으로 인정한다.
* 새로운 `UNCERTAIN`이 발생하면 자동 재시도하지 않는다.
* V4가 다시 `actions=[]`을 선택할 수 있다. 이를 막기 위한 임의 Work 강제 생성은 없다.

## 5. 그다음의 코드 정리 방향

이번 단계는 운영 복잡도와 복구 계층을 줄인 **검증 가능한 연구 기준선**이다. Pilot 전에 V3/V4/기반 Controller를 하나의 새로운 구현으로 합치는 것은 요청 ID나 입력 프롬프트 바이트를 바꾸어 재생·출처 관계를 깨뜨릴 위험이 크다. 다음 코어 리팩터링에서는 이 분기를 원본 보존된 참조 실행으로 두고, 새 코드가 동일한 모의 Provider 입력·Journal 결과를 생성하는지 비교할 수 있다.

과학적 후속 과제는 유지한다: 실제 Claim/P0 delta 때문에 새로운 독립적인 과학 연구가 발생하는지 검증하고, 이론 연구 가능성과 실험적 인증의 분리를 Controller의 연구 선택으로 연결한다. V5의 기존 성공 주장이나 미커밋 결정을 계승한 것으로 주장하지 않는다.
