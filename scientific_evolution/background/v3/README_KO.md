# Scientific Evolution Closed Loop V3 — 재평가 비용 완화와 자율 연구 선택의 연결

## 이번 개발이 필요한 이유

V2 recovered 캠페인(`SCIENTIFIC_CLAIM_PROBLEM_DELTA_V2_RECOVER_20261028`)의 제공된 최종 보고서 기준으로 이벤트 1640개, Controller 결정 67개, 자산 112개, 활성 FRESH 문헌 연구 Worker 1개였다. 과학적 상태는 ONGOING이며 비용상한으로 중단됐다. 문헌 증거·강한 Null 검토에 비해, 실제 INFORMED 후속 가설 발전이 진행되지 않았고 NVT/PMI/OPP/Controller 호출이 반복되는 경향이 확인됐다.

V3는 ① 과학적 사건 기반 Controller 평가, ② 이전 평가의 정확한 재사용, ③ Controller가 병행 가능한 INFORMED 연구를 명시적으로 고려하도록 하는 **조언**에 집중한다. 결코 연구 방향/가설 개수/Work 수/지속시간을 강제하지 않는다. P0 불변, FRESH 입력 격리, 실제 도구 실행 진실성, 과거 HOLD와 UNKNOWN API 호출 상태를 보존한다.

## 변경 사항

- 최초 원본 recovery ROOT를 새 V3 ROOT로 **읽기 전용 복제**한다. 소스 이벤트 전체의 해시를 비교하고 마지막에 V3로 분기했다는 운영 기록 한 개만 추가한다. 이미 해결된 `NVT_REISSUE`는 SAVED, 원래 응답 미확보 호출은 여전히 UNCERTAIN으로 남는다. 새 프로그램은 후자의 존재를 임의로 삭제하지 않고, 검증된 재발행 영수증이 존재하는 *그 호출 하나*만 과거 불확실 상태로 인정한다.
- Controller 실행 시점을 기계적인 모든 자산 등록이 아니라 **과학적 신호** 중심으로 좁힌다. 새로운 HYPOTHESIS/PREDICTION/NULL_MODEL/COUNTEREXAMPLE/CALCULATION/SCOPED_NEGATIVE, 직접 관찰한 원문을 인용한 LITERATURE_CLAIM, 새로운 과학 하위 문제/완료 Work는 평가 대상으로 인정한다. Metadata-only LITERATURE_CLAIM이나 연구 상태 메타데이터만으로는 자동 평가를 촉발하지 않는다. 파일마다 내용의 의미를 완전히 이해하는 semantic gate가 아니므로 의미 변화 오분류는 있을 수 있다.
- NVT/PMI 결과를 **동일한 과학 입력 서명**인 경우 이전 정상 커밋 결정의 검증된 판단에서 계승한다. 이때 새 유료 NVT/PMI 호출을 하지 않는다. 직접 원문/PDF/부록 근거, 후보 가설, 관련 하위 문제 또는 P0가 달라지면 새로 평가한다. Metadata-only 파일 추가는 직접적인 과학적 판단 변화로 보지 않는다. 기계적으로 같은 입력에 대한 기존 응답은 원래의 출처 ID로 표시한다. Opportunity 평가는 과학 입력 및 활성 Work의 ID·모드·상태가 불변일 때 재사용한다. 이전 NVT/PMI/OPP 모델 답변을 검증된 과학적 사실로 재분류하지 않는다.
- Controller에는 활성 Work, 문헌 연구와 병행할 수 있는 연구의 가능성, P0의 실험 **전** 가설 기준을 전달한다. 이미 확보된 지식만으로 조건부 이론 가설을 발전시키는 과학적 가치와 새 문헌을 계속 찾는 과학적 가치를 비교하게 할 뿐 강제로 새 Work를 만들지 않는다. 병행 연구는 모델의 자율 판단이며, 기존 FRESH Worker를 중단하거나 과거 연구 결과를 FRESH에게 유출하지 않는다.
- 기반 `e2core`, V2.1, 기존 Recovery V1 패키지는 수정하지 않는다. 별도 운영 실행기에서 일시적으로 V2 Controller 함수만 대체한다. 모든 패치는 실행 후 원복된다. 복구 소스 6개 파일의 실제 SHA256 해시가 달라지면 유료 호출 전에 중단한다.

## A. 설치 (무과금)

ZIP을 `~/FAKG/ForAllKG/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028.zip`에 저장하고 아래를 실행한다.

```bash
conda activate graphAgent311
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$HOME/GraphAgentsDAC/patchkits/SERS_DISCOVERY_COHORTS_20261028"
OLDPACK="$KIT/SCIENCE_IDENTIFIABILITY_AND_FRONTIER_20261028"
V2PACK="$KIT/SCIENTIFIC_CLAIM_PROBLEM_DELTA_V2_1_20261028"
V3PACK="$KIT/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028"
SRC="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_CLAIM_PROBLEM_DELTA_V2_RECOVER_20261028"
NEXT="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028"

python -m zipfile -e \
  "$HOME/FAKG/ForAllKG/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028.zip" "$KIT"
cd "$V3PACK"
sha256sum -c SHA256SUMS.txt

PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK" \
  python -m unittest discover -s tests -q
```

위 명령의 회귀 테스트는 출처·Journal 계약과 모의 모델 응답을 검증한다. 실제 SERS 신규 가설이 개선된다는 시험은 아니다.

## B. V2 복구 ROOT에서 V3 후속 ROOT 생성 (무과금)

```bash
cd "$V3PACK"
PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK" \
  python scientific_closed_loop_v3.py fork \
    --source-root "$SRC" \
    --out-root "$NEXT"

PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK" \
  python scientific_closed_loop_v3.py inspect --root "$NEXT"

PYTHONPATH="$KIT" python -m e2core.cli verify --root "$NEXT"
```

**중요:** V2 recovery ROOT가 종료 상태(`HOLD_WITH_RATIONALE`, `SCOPED_NEGATIVE`, `REVIEW_WORTHY_CANDIDATE`)면 새로운 과학적 연구를 무조건 계속하지 않는다. V3는 종료 결정을 존중한다. 새 ROOT가 이미 있으면 덮어쓰지 않는다. `prepare`, 원본 복구 `fork` 또는 `uncertain_nvt_recovery.py run`을 다시 호출하지 않는다.

## C. 무과금 실행 사전 점검

```bash
unset FAKG_RESEARCH_ALLOW_PAID
PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK" \
  python scientific_closed_loop_v3.py run \
    --root "$NEXT" --preflight
```

`V3_PREFLIGHT`에서 `replacement_status=SAVED`, `historical_unknown_status=UNCERTAIN`, 다른 `unknown_calls=[]`, 기존 Controller/자산 계보가 그대로인지를 확인한다. 기존 UNKNOWN 과금 여부는 확정하지 않는다.

## D. tmux에서 작은 유료 Pilot

```bash
tmux new -s scientist_v3
```

tmux 안에서 위의 `KIT`, `OLDPACK`, `V2PACK`, `V3PACK`, `NEXT`를 다시 설정하고:

```bash
cd "$V3PACK"
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT

  PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK" \
  python scientific_closed_loop_v3.py run \
    --root "$NEXT" --paid --model openai/gpt-5.6-luna \
    --slice-budget 12 --max-total-new-calls 24 \
    --checkpoint-iterations 12 --max-parallel 2 --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    | tee "$HOME/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_PILOT.log"
)
```

`--max-total-new-calls 24`는 **이 실행에서 새로 청구될 수 있는 호출의 최대 개수**다. 사용자가 기존 `Ctrl+C` 사고를 반복하지 않도록 tmux에서는 `Ctrl+B` 다음 `D`로 세션만 분리한다. `OPERATOR_COST_GUARD`는 과학적 종료가 아니다.

## E. 평가 방법

과학적 성과를 검토할 때 다음을 구분한다.

- 구조적 연결: 새 문헌/반례가 논문 선행 내용, 잔여 예측, P0 미해결 상태를 실제로 변경했는가?
- 행동: Controller가 FRESH 연구가 진행 중인 와중에 **가치 있는 INFORMED** 연구를 자율적으로 선택했는가? 단지 숫자를 채우는 행동은 제외한다.
- 과학적 진전: 조건부 새 물리적 명제와 구별 가능한 정량 예측/실험 제안이 생겼는가? 기존 기작을 잘 요약한 것만으로 Level II를 인정하지 않는다.
- 효율: 4단계 평가·관리 호출 비율과 비용이 줄었는가? 반복 결과 재사용량(`v3_reused_novelty_impact`, `v3_reused_opportunity`)을 구분한다.
- 안전: 소스와 영수증 보존, 원래 UNKNOWN 결과의 UNKNOWN 유지, 새 UNKNOWN 발생 시 즉시 중지, 실험 전 가설과 실험 사실의 구분.

주의: V3는 Controller에게 병행 연구 가능성을 제시하지만, 그렇게 행동해야 한다고 강제하지 않는다. Controller가 여전히 의미 있는 병행 연구를 선택하지 않으면 '선택 유도만으로 부족'이라는 연구 설계 결론으로 해석해야 한다.

## 제한 및 진실성

공개된 유료 연구 실행은 사용자의 WSL에만 존재하는 `SRC` Journal을 요구한다. 이 패키지를 만들면서 실제 유료 호출을 실행하지 않았고, 사용자 ROOT를 수정하지 않았다. 로컬 합성 환경에서는 8개 테스트가 통과했다. 필요한 `e2core` 보조 모듈 중 몇 개는 이번 업로드에 포함돼 있지 않아 로컬 테스트에서 모의 함수를 사용했다. 실환경의 완전한 통합 성공이나 과학적 성과 향상은 아직 입증되지 않았다.
