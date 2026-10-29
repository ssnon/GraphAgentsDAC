# Scientific Research Readiness & Claim–Problem Handoff V4

## 목표: 문헌 연구를 기다리기만 하는 AI Scientist에서 자율적 실험 전 연구까지

V3 Pilot의 D00069–D00073은 모두 `actions=[]`, 신규 INFORMED Work 0개, 이전 평가 재사용 0회였다. 이것만으로 Controller가 틀렸다는 뜻은 아니다. 다만 당시의 모델 판단은 문헌과 실험 데이터의 불완전성을 조건부 이론 연구의 낮은 가치/준비 미달과 강하게 결부했다. 이미 존재하는 FRESH 원문 연구를 존중하면서도, 서로 다른 연구 질문/산출물을 갖는 INFORMED 기작 연구, 계산, 반례 검토가 독립적으로 가치 있는지 모델이 공정하게 평가하도록 한다.

**V4는 연구 행동을 강제하지 않는다.** FRESH/INFORMED Work 수, 호출 수, 세대 수, 모델 가설의 내용, 특정 Photocharge 방향을 고정하지 않는다. 신뢰할 만한 결과가 없을 때 과학적 HOLD도 허용한다. 단지 연구를 *시작*하기 위한 조건과 과학적/경험적 진실을 *인증*하기 위한 조건을 분리하고, 검토된 과학적 변화가 다음 INFORMED Work에 전달되도록 한다.

## 변경점

1. Opportunity Assessor가 각 후보 연구에 대해 **Theoretical readiness / Computational readiness / Empirical readiness**를 구별하도록 기존 프롬프트에 조언을 추가한다. 실험 자료가 없다는 이유만으로 물리적으로 일관적인 조건부 계산을 금지하지 않는다. 반면 실제 현상/인과기작의 검증을 주장하는 일은 허용하지 않는다.
2. Controller는 활성 FRESH 문헌 연구와 **실제로 같은 질문·방법·과학적 산출물**인지 비교하게 된다. 문헌 조사가 계속되고 있다는 이유 하나만으로 다른 INFORMED 기작 개발/경쟁 가설 검산을 중복으로 처리하지 않도록 조언한다. 새로운 Work를 **반드시 생성하지 않아도 된다.** 기존 E3R1 Controller의 `controller_plan`과 Journal 검증 규약이 그대로 적용된다.
3. Controller/Opportunity에는 마지막 **정상 커밋된** Novelty–Claim→P0–Problem Impact 판단의 연결을 제공한다. 새로운 INFORMED Worker는 자신이 물려받은 parent asset와 관련된 잠정적 신규성 평가, P0 기여/미해결 요건을 받는다. 이 정보는 `model_assessment_only=true`로 표시되며 독립 검증된 물리적 사실이 아니다. **FRESH Worker의 입력은 V3와 완전히 동일하다.**
4. V3의 과학적 입력 fingerprint에 V4 평가 계약 버전만 추가한다. 첫 V4 평가에서 예전 V3 Opportunity를 그대로 재사용하여 새 조언을 건너뛰는 상황을 방지한다. 기존 NVT/PMI의 durable 호출 ID 생성식과 프롬프트는 변경하지 않아 동일 입력의 저장 응답을 안전하게 재생한다. 이후 동일 과학적 입력/Work 포트폴리오에서는 V4 평가를 재사용할 수 있다. 이는 새 원문 근거가 계속 늘어날 때 의미론적 중복 판단까지 해결해 준다는 뜻은 아니다.
5. V3 ROOT를 **새 V4 ROOT로 append-only 복제**한다. 기존 모든 이벤트 해시, 원래 `UNCERTAIN` 모델 호출, 이미 `SAVED`된 재발행 호출, P0·자산·Work·Controller 계보를 보존한다. V3 원본은 변경하지 않는다. V2.1/e2core/V3 소스는 수정하지 않는다.

## A. ZIP 설치 및 무과금 검증

ZIP 파일을 `~/FAKG/ForAllKG/SCIENTIFIC_RESEARCH_READINESS_V4_20261028.zip`에 넣고 실행한다.

```bash
conda activate graphAgent311
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$HOME/GraphAgentsDAC/patchkits/SERS_DISCOVERY_COHORTS_20261028"
OLDPACK="$KIT/SCIENCE_IDENTIFIABILITY_AND_FRONTIER_20261028"
V2PACK="$KIT/SCIENTIFIC_CLAIM_PROBLEM_DELTA_V2_1_20261028"
V3PACK="$KIT/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028"
V4PACK="$KIT/SCIENTIFIC_RESEARCH_READINESS_V4_20261028"
SRC="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_EVOLUTION_CLOSED_LOOP_V3_20261028"
NEXT="$HOME/GraphAgentsDAC/evaluation/SCIENTIFIC_RESEARCH_READINESS_V4_20261028"

python -m zipfile -e \
  "$HOME/FAKG/ForAllKG/SCIENTIFIC_RESEARCH_READINESS_V4_20261028.zip" "$KIT"
cd "$V4PACK"
sha256sum -c SHA256SUMS.txt
PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK" \
  python -m unittest discover -s tests -q
```

실제 사용자 WSL의 전체 `e2core` 의존성이 존재해야 한다. 이 패키지에는 모델 키/런타임 설정/사용자 ROOT가 포함되지 않는다. 이 코드 작성 중 수행한 로컬 테스트는 사용자가 업로드한 6개 코어 소스를 기반으로 한 mock/Journaling 테스트였고, 누락된 외부 도구 보조 모듈은 테스트에서만 스텁을 사용했다. 유료 연구 테스트는 수행하지 않았다.

## B. 원본 V3를 보존한 새 V4 ROOT (무과금)

**V3에서 사용했던 `SRC`를 지정한다. V2 Recovery ROOT나 V1.1 HOLD ROOT에서 다시 시작하지 않는다.** V4 목표는 V3의 D00073까지의 과학적 계보를 그대로 이어받는 것이다.

```bash
PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK" \
  python scientific_research_readiness_v4.py fork \
    --source-root "$SRC" \
    --out-root "$NEXT"

PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK" \
  python scientific_research_readiness_v4.py inspect --root "$NEXT"

PYTHONPATH="$KIT" python -m e2core.cli verify --root "$NEXT"
```

다음 값을 확인한다: `historical_unknown_status=UNCERTAIN`, `replacement_status=SAVED`, `other_unknown_calls=[]`, `controller_decisions=72`, `assets=117`, `v4_research_readiness_separated=true`. 데이터에 추가 변동이 있었으면 Controller/자산 수는 실제 상태에 따라 달라질 수 있다. `NEXT`가 이미 있으면 덮어쓰지 않는다. 생성 도중 실패했을 경우 원본 `SRC`는 그대로 유지된다.

## C. 사전점검 (무과금)

```bash
unset FAKG_RESEARCH_ALLOW_PAID
PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK" \
  python scientific_research_readiness_v4.py run \
    --root "$NEXT" --preflight
```

## D. tmux Pilot (유료 호출 승인 시에만 실행)

`tmux new -s scientist_v4`에서 conda와 위 환경 변수를 다시 설정한다. 기존 `Ctrl+C`로 UNKNOWN 호출이 발생한 사고가 있으니 tmux에서는 `Ctrl+B`, `D`로 빠져나온다.

```bash
cd "$V4PACK"
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT

  PYTHONPATH="$KIT:$OLDPACK:$V2PACK:$V3PACK:$V4PACK" \
  python scientific_research_readiness_v4.py run \
    --root "$NEXT" \
    --paid --model openai/gpt-5.6-luna \
    --slice-budget 12 \
    --max-total-new-calls 24 \
    --checkpoint-iterations 12 \
    --max-parallel 2 \
    --max-tokens 16000 \
    --science-cpu-seconds 120 \
    --science-wall-seconds 160 \
    | tee "$HOME/SCIENTIFIC_RESEARCH_READINESS_V4_PILOT.log"
)
```

`--max-total-new-calls`는 **이번 실행에서 추가**되는 유료 호출 수 제한이지 과학 연구의 step/Work 한도가 아니다. `OPERATOR_COST_GUARD`는 과학적 HOLD가 아니다. 위 `run`은 V4 preflight 이후 기반 V3의 preflight와 checkpoint도 출력하므로 V3 이벤트 이름이 보이는 것은 정상이다.

## E. 결과 평가

- **과학적 연구 행동:** Controller가 `FRESH ACTIVE`와 무관하게 독립적인 이론·계산 연구를 가치 있게 평가했는가? 신규 INFORMED Work가 있다면 실제 질문·부모 자산·작업 종류·목표 예측을 조사한다. 무조건 `actions > 0`이 성공은 아니다.
- **판단 근거:** `actions=[]`이면 이론적/계산적 준비성을 실험적 인증과 구분해서 검토했는가? 여전히 자료 완결성만 이유로 보류하면 병목이 남아 있는 것이다.
- **과학적 Delta:** 기존 논문과 겹치는 명제를 정확히 한정하고 새로운 물리적 주장, 대안, 반례, 예측이 남았는가? 그 결과 P0의 미해결 조건과 다음 연구 질문이 구체적으로 변했는가?
- **전달:** INFORMED Worker의 V4 입력에 `v4_claim_problem_scientific_handoff`가 포함되어 이전 주장·논문 관계를 모델의 잠정 판단으로만 사용했는가? FRESH 입력에는 포함되지 않았는가?
- **비용/효율:** 기존 평가 결과 재사용 여부와 실제 과학 Worker 호출 비율을 비교한다. 새 primary text가 연이어 도착하는 동안 의미론적으로 동일한 새 문헌이 재평가될 가능성은 남아 있다.
- **인증:** 실험 전 조건부 모델을 실증된 발견처럼 선언하지 않았는가? 새 Level II 판단은 독립적인 과학적 검토를 거쳐야 한다.

## F. 한계와 독립적인 다음 선택

이 버전은 **연구자의 가치 판단 입력과 결과 전달 계약**을 바꾸는 것이지 강제 배정 규칙이 아니다. Pilot에서도 같은 `actions=[]`가 계속될 수 있다. 그 경우 원인은 평가 맥락보다 더 깊은 자율 선택 정책, 연구 전략, 실제 정보가치 판단에 있을 수 있다. 기존 논문 연구가 성실하고 생산적이라면 병행 연구를 하지 않는 결정이 과학적으로 옳을 수도 있다.

동일한 프로토콜 버전에서 restart할 때 운영상의 durable call-replay는 유지된다. 소스 버전을 변경한 뒤 같은 ROOT의 이미 저장된 호출 ID와 프롬프트를 다르게 해석하지 않는다. 새 UNKNOWN 과금/응답 기록이 발생하면 자동 재시도하지 않는다. 적절한 추가 복구는 수동으로 판단한다.
