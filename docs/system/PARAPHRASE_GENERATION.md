# GPT 6.1로 Q2·Q4 재생성

Python 3.10 이상, 표준 라이브러리만 사용합니다. 별도의 패키지 설치는 필요하지 않습니다.

현재 코드가 다루는 범위는 6개 데이터셋의 **Q1 90개 → Q2 90개**, **Q3 60개 → Q4 60개**입니다. 새 활동·새 정답을 생성하지 않고 질문 표현만 바꿉니다. 데이터셋별로 기존 pair ID를 보존합니다. 이 코드 추가 커밋 자체는 기존 질문이나 DB를 변경하지 않습니다.

## 1. 코드와 수정 DB 가져오기

이 브랜치는 이전 event-table 범위 수정도 포함합니다.

```bash
git fetch origin
git switch --track origin/feat/gpt61-question-paraphrases
```

DB를 재생성할 계획이면 **DB builder 실행을 먼저 끝낸 뒤** 아래 과정을 진행하세요. 기존 builder는 이전 질문 구성을 만들 수 있으므로, API 생성 후 builder를 다시 실행했다면 `prepare`부터 새로 진행해야 합니다.

## 2. API 설정

사용하는 서비스의 **정확한 GPT 6.1 모델/배포 ID**를 설정합니다. 코드가 모델 ID를 추측하거나 다른 모델로 대체하지 않습니다. `OPENAI_BASE_URL`에는 `/chat/completions` 앞까지의 OpenAI 호환 API URL을 넣습니다.

Bash 또는 zsh:

```bash
read -rsp "API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY

export OPENAI_BASE_URL='https://YOUR-PROVIDER/v1'
export NL2EVENTLOG_PARAPHRASE_MODEL='YOUR-EXACT-GPT-6.1-MODEL-ID'
```

`YOUR-...` 값을 실제 서비스 정보로 교체하세요. 공식 OpenAI endpoint를 이용한다면 base URL은 `https://api.openai.com/v1`입니다. 해당 서비스가 제공하는 모델 ID를 사용해야 하며, 모델의 계정별 접근 가능 여부는 이 코드에서 보장하지 않습니다.

키는 터미널의 숨김 입력으로만 받습니다. 코드·명령어 문자열·README·프롬프트·로그에 키를 넣지 마세요. `.env` 계열 파일은 gitignore에 추가했지만, 이 코드는 `.env`를 자동으로 읽지 않습니다. 다른 변수에 키를 넣었다면 `--api-key-env 변수명`을 사용하세요. HTTPS endpoint만 허용하고 redirect를 거부합니다.

## 3. 기존 Q2·Q4 제거

```bash
python paraphrase_questions.py prepare
```

- Q1·Q3의 원문, ID, ES와 정답 이벤트를 보존합니다.
- 활성 질문 파일, 모델 입력 파일, gold 메타데이터에서 기존 Q2·Q4를 제거합니다.
- 기존 Q2·Q4의 gold SQL/CSV와 이전 paraphrase 출력 캐시도 제거합니다.
- 각 원문과 생성할 질문 ID의 대응을 `datasets/*/source/paraphrase_plan.jsonl`에 저장합니다.
- 이 단계의 결과는 Q1·Q3 총 150개, gold CSV 141개입니다. 기존 pair를 필수로 요구하는 domain validator는 이 중간 상태에 맞지 않습니다. 아래 전용 `validate`를 사용하세요.

`prepare`는 명시적인 초기화입니다. **생성 중단 후 이어서 할 때는 prepare를 다시 실행하지 마세요.** 캐시를 초기화합니다. 기존 데이터는 Git 기록으로 복구할 수 있습니다.

## 4. 소량 시험 후 전체 생성

선택 사항: 원문 2개만 생성하고 checkpoint에 저장합니다. 이 시험에서는 활성 질문 파일에 pair를 적용하지 않습니다.

```bash
python paraphrase_questions.py generate --limit 2
```

이어서 전체 생성:

```bash
python paraphrase_questions.py generate
python paraphrase_questions.py validate
```

명시적인 인자로도 설정할 수 있습니다.

```bash
python paraphrase_questions.py generate \
  --model "$NL2EVENTLOG_PARAPHRASE_MODEL" \
  --base-url "$OPENAI_BASE_URL"
```

기본적으로 원문마다 생성 1회와 같은 모델의 의미 검토 1회를 호출합니다. 150쌍은 정상 경로에서 **300 API 호출**이며 실패 재시도는 추가됩니다. 비용은 서비스 요금에 따릅니다. 순차 실행하고 정상 응답을 즉시 checkpoint에 저장합니다. 중단됐다면 동일한 명령으로 재개하며, 같은 원문 hash·prompt version·model의 통과 기록을 재사용합니다.

지정한 모든 데이터셋의 모든 질문이 통과해야 활성 질문·gold 파일에 일괄 적용합니다. 중간 실패 시 이미 생성한 checkpoint는 남고 활성 파일은 유지됩니다. 파일별 atomic replace와 Python 오류 시 rollback을 사용하며, 프로세스 강제 종료까지 전체 파일의 원자성을 보장하지는 않습니다.

원문이나 ID가 바뀌면 오래된 캐시를 붙이지 않고 중단합니다. `--datasets hospitalflow`처럼 데이터셋을 지정할 수 있으며 `prepare`와 `generate`에 같은 범위를 지정하세요.

## 생성·검증 규칙

- **Q1 → Q2:** 활동을 자연스러운 비즈니스 표현으로 바꾸되, 활동 집합·시작/완료 단계·case·대상 범위·반복·하위 객체 포함 조건·기존 제한을 유지합니다.
- **Q3 → Q4:** 전체 recorded lifecycle의 의미를 유지하고 활동을 열거하거나 예시로 추가하지 않습니다.
- 모델에는 원문 질문과 source ID/type, target type만 전달합니다. DB, dictionary, task catalog, private gold, answerability, 이전 paraphrase는 전달하지 않습니다.
- 응답 ID/type, 형식, 중복 원문, 원문 hash를 검사합니다. 같은 모델이 의미 동등성과 implicit scope 유지 여부를 추가 판정하며, 실패하면 최대 `--attempts`회 재생성합니다.
- **같은 모델의 의미 판정은 독립적인 검증이 아닙니다.** 최종 결과는 특히 단계 표현·반복·하위 객체 범위를 표본 검토하세요. 기계적 검증만으로 자연어 동등성을 증명하지 않습니다.
- 새 pair의 ES와 gold SQL/CSV는 원문에서 로컬 복사합니다. Q1·Q3의 실제 정답을 LLM이 수정하지 않습니다.
- 질문 파일이 여러 schema를 사용하는 점을 처리하고, 모델 입력에는 질문 ID와 텍스트만 남깁니다.

## 생성 결과와 GitHub 업로드

- `source/paraphrase_plan.jsonl`: 원문 및 ID 대응, 원문 hash
- `source/paraphrase_generations.jsonl`: 생성 요청·원본 응답·의미 검토 응답·요청/응답 model ID·token usage·시각
- `private/paraphrase_state.json`: seeds-only 또는 generated 상태
- 기존 질문 파일 및 `input/model_questions.jsonl`: 새 표현과 pair 연결
- `private/gold.jsonl`, `private/gold_sql/`, `private/gold_logs/`: 원문과 동일한 정답을 새 pair에 연결
- `docs/questions.md`, README 통계: 현재 질문 상태

생성 후에는 300개 질문, 282개 gold CSV로 돌아옵니다. 기존 Q2·Q4와 ID는 같을 수 있지만 문장은 새 API 출력입니다.

```bash
python paraphrase_questions.py validate
python validate_lifecycles.py
python validate_timestamp_columns.py
python validate_event_scope.py

git diff --stat
git status --short
git add datasets README.md event_scope_audit.json EVENT_TABLE_SCOPE.md
git commit -m "Regenerate Q2/Q4 paraphrases with GPT 6.1"
git push origin HEAD
unset OPENAI_API_KEY
```

`git status`에서 업로드할 파일을 확인하세요. API 키 파일을 stage하지 마세요. 생성 provenance는 질문 텍스트와 API 응답만 저장하며 인증 header나 키는 저장하지 않습니다. `validate_event_scope.py` 보고서의 질문 수는 실제 활성 질문에 맞춰 갱신됩니다.

OpenAI 호환 Chat Completions API와 JSON mode를 사용합니다. endpoint가 `response_format={"type":"json_object"}`를 지원해야 합니다. 지원하지 않거나 모델 접근이 거절되면 오류로 중단하며 다른 모델/API 형식으로 자동 전환하지 않습니다.

API 형식 참고: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

## 코드 자체의 오프라인 테스트

```bash
python -m unittest discover -s tests -p 'test_paraphrase_questions.py' -v
```

테스트는 임시 데이터 복사본과 명시적인 fake API만 사용합니다. 실제 모델 생성 결과가 아닙니다. 전체 150쌍의 제거·생성·resume, ID/원문/정답 보존, 잘못된 매핑·의미 검증 실패·stale cache 거부를 확인합니다.
