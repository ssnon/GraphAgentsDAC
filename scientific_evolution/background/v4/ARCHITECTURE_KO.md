# V4 아키텍처 노트

```
V3 ROOT (D00073, FRESH ACTIVE, all events preserved)
   └── [verified append-only fork] -> V4 ROOT
        └── scientific source/hypothesis triggers (V3)
             └── NVT -> PMI -> Opportunity -> Autonomous Controller
                  ├── Readiness split: theory / computation / empirical
                  ├── Non-duplication by scientific question and output
                  ├── Prior-art / claim / P0 model-only handoff
                  └── free decision: FRESH, INFORMED, parallel, pause, HOLD
                        ├── FRESH input: literally unchanged (isolation)
                        └── INFORMED input: prior model-only claim→P0 delta
```

- 코어 스키마/과학적 허가 규칙을 추가하지 않는다. 모든 새 과학 자산은 Worker가 기존의 Journal 경로를 통해 출판해야 한다.
- V4의 `READINESS_TEMPLATE`는 과학적 인증기가 아니라 모델에게 판단 질문을 전달하기 위한 입력이다.
- 기존 `controller_plan`의 적합성·부모 자산·중복 배정·최종 과학적 상태 규약을 사용한다.
- V4 평가 서명은 V3 과학 fingerprint에 프로토콜 버전만 추가한다. NVT/PMI 요청을 바꾸지 않으므로 기존 저장 응답은 바이트 재생 방식으로 유지된다. 첫 V4 Opportunity는 새로운 프롬프트로 다시 실행될 수 있다.
- `v4_claim_problem_scientific_handoff`는 마지막 **커밋된** Controller 입력을 근거로 하며 `model_assessment_only=true`; 실험적 사실로 승격하지 않는다.
- FRESH가 읽지 못하게 해야 하는 이전 가설/의견은 FRESH Worker에 전달하지 않는다.
- 초기 V4 부팅 자체가 새 Work/가설을 생성한 것으로 기록되지 않는다. 후속 연구 여부는 실제 유료 실행의 모델 판단과 Work 기록으로만 입증된다.
