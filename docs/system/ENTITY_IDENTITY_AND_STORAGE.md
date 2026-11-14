# Entity, Entity Type, Key, Table, Case notion, Case: 개념과 관계

이 문서는 NL2EventLog의 **목표 개념 모델**을 설명한다. 현재 DB와 SQL 실행으로 검증한 저장 사례는 [데이터셋별 목록](../../datasets/ENTITY_STORAGE_CASES.md)에 구분해서 제시한다. 기존 table→ET 도표와 legacy identity Gold는 이 모델 전체의 정답 주석이 아니다. 새로운 ET 추론 알고리즘을 구현하거나 성능을 측정했다는 의미도 아니다.

## 1. 무엇이 대상이고, 무엇이 저장 방식인가?

| 용어 | 정의 | 예 |
|---|---|---|
| Entity | 분석 도메인에서 다른 대상과 구별되는 개별 대상 | 작업자 1, 입원 20000001, 학생 S002의 강좌 C01 수강등록 |
| Entity Type (ET) | 동일한 비즈니스 의미와 인스턴스 단위를 공유하는 Entity의 유형 | Worker, Hospital Admission, Registration |
| Case notion | 어떤 대상 단위별로 이벤트를 묶을지 정하는 분석 관점; 본 연구에서는 ET 기반으로 정의 | Worker를 선택해 작업자별 이력 분석 |
| Case | 선택한 관점에서 개별 Entity를 나타내는 분석 단위 | 작업자 1의 case |
| Case ID | 출력 로그에서 case를 식별하는 값 | `L:1` |
| Trace | 한 case에 귀속된 이벤트를 정렬한 이력 | 작업자 1의 작업 이벤트 순서 |
| Instance granularity | 무엇을 하나의 독립된 인스턴스로 구분하여 세는지 | 환자 한 명과 입원 한 건은 단위가 다름 |
| Table | 행과 열로 속성·관계·기록을 저장하는 물리적 구조 | `worker`, `worker_contact`, `goods_receipt` |
| Row | 한 테이블에 저장된 하나의 레코드 | 입고등록 한 행; 작업자와 입고요청을 참조할 수 있음 |
| Key | 행 또는 대상을 식별할 때 사용하는 하나 이상의 컬럼과 그 식별 규칙 | `worker_id`; `(student_id, course_id)` |
| Primary key (PK) | 해당 테이블의 행을 유일하게 식별하도록 선언한 키 | 입고등록의 `receipt_id` |
| Candidate / alternate key | 행을 유일하게 식별할 수 있는 최소 컬럼 집합 / PK로 선택되지 않은 후보키 | 값이 존재할 때의 `worker.payroll_no`; 여기서는 NULL 허용 UNIQUE이므로 전체 행에 대한 엄밀한 후보키는 아님 |
| Foreign key (FK) | 다른 행의 PK 또는 유일 키를 참조하도록 선언한 제약 | `goods_receipt.receiver_id → worker.worker_id` |
| Identity namespace | 식별자 값이 대상을 구별하는 범위 | 검사주문 ID와 투약주문 ID의 범위는 서로 다름 |
| Entity reference | 특정 Entity를 가리키는 저장 표현 | 입고등록 행의 `receiver_id='1'`은 작업자 1 참조 |

**Entity는 테이블도, 행도, 키도 아니다.** DB의 행은 Entity의 속성이나 Entity 사이의 관계를 기록한다. 키 값은 정해진 범위와 의미 아래에서 Entity를 식별한다. PK는 우선 행의 유일성을 보장하며, 그것이 어떤 비즈니스 대상을 나타내는지는 별도로 해석해야 한다. Entity의 존재가 모든 표현에 FK가 선언되어 있어야 한다는 뜻은 아니다.

ET 판단은 두 질문으로 구성한다: **같은 종류의 대상을 나타내는가? 무엇을 하나로 세는가?** 저장 장소, 컬럼명 또는 키 값의 일치 자체는 이 기준이 아니다. 단위가 같아도 주문과 결제처럼 의미가 다를 수 있다. 같은 ET여도 서로 다른 Entity를 저장할 수 있다.

## 2. 실제 DB 예시: 한 작업자가 여러 이름과 키로 등장한다

WarehouseFlow의 실제 레코드 일부:

| Table | 저장 값 | 의미 |
|---|---|---|
| `worker` | `worker_id='1', payroll_no='PAY-1001', worker_name='Worker 1'` | 한 작업자에 대한 두 식별자의 대응과 기본 속성 |
| `worker_contact` | `staff_no='PAY-1001', contact_channel='internal messaging'` | 동일 작업자의 추가 속성 |
| `goods_receipt` | `receipt_id='001', request_id='001', receiver_id='1'` | 입고등록 001이 요청 001과 작업자 1을 참조 |

`worker_contact`의 행은 새 Contact Entity가 아니라 기존 Worker의 선택적 속성이다. 이것은 테이블 이름이나 1:1 관계에서 추측한 결론이 아니라, 데이터 사전의 명시적 의미와 키 제약으로 정한 설계다. 반대로 `goods_receipt`는 자기 입고등록을 식별하면서 별개의 요청과 작업자를 참조한다.

```sql
SELECT w.worker_id, w.payroll_no, c.staff_no, r.receipt_id
FROM worker AS w
LEFT JOIN worker_contact AS c ON c.staff_no = w.payroll_no
LEFT JOIN goods_receipt AS r ON r.receiver_id = w.worker_id
WHERE w.worker_id = '1';
```

여기서 `receiver_id`와 `worker_id`는 이름만 다르고 같은 식별자 범위를 사용한다. `staff_no`와 `payroll_no`도 같은 범위를 사용한다. 반면 `worker_id`와 `payroll_no`는 값도 다르므로 worker 행에 기록된 대응을 사용해야 한다. 문자열 변환으로 대응을 추측하지 않는다. 접미 숫자가 비슷하다는 사실은 근거가 아니다.

현재 작업자는 7명이고 추가 연락 속성은 3명만 갖는다. 연락 속성 테이블의 행 수를 작업자 수로 간주하거나 INNER JOIN으로 전체 작업자 집합을 구성하면 나머지를 놓친다. 이 추가 테이블에는 타임스탬프가 없으므로 새로운 이벤트를 생성하지 않는다.

## 3. 함수로 표현하기

ET들의 집합을 \(\mathcal T\), Entity 집합을 \(\mathcal E\), 각 타입의 Entity 집합을 \(\mathcal E_\tau\)로 둔다. 이 연구에서 분석에 사용하는 의미·단위별 분류를 \(\operatorname{type}:\mathcal E\to\mathcal T\)로 정의하고, \(\mathcal E_\tau=\{e\mid\operatorname{type}(e)=\tau\}\)로 쓴다. 이는 본 연구의 분류 규약이며 모든 도메인 온톨로지의 다중 타입을 부정하지 않는다.

테이블 \(T\)의 행 집합을 \(R_T\), 순서 있는 컬럼 목록을 \(C\)라고 하면 투영 \(\pi_C(r)\)는 행에서 그 컬럼 값의 튜플을 읽는다. PK \(P_T\)는 \(R_T\)에서 유일한 튜플을 보장하지만, 그것만으로 비즈니스 타입을 결정하지 않는다.

식별자 해석 \(\rho\)는 특정 테이블·컬럼 목록·필요한 행 조건·타입·식별 범위·검증된 대응 규칙을 명시한다. 각 해석은 부분 함수다.

\[
\mu_\rho:R_T\rightharpoonup\mathcal E_\tau.
\]

NULL 참조나 근거가 부족한 식별자는 함수가 정의되지 않는 경우다. 임의의 유일한 행 ID를 곧바로 Entity ID로 승인하지 않는다. 복합키는 전체 튜플을 사용한다. 타 테이블의 유일 행을 찾아 그 행의 정규 식별자로 변환하는 것도 검증된 대응 규칙에 포함될 수 있다.

예를 들어 작업자 타입에 대한 해석은 다음과 같다.

\[
\begin{aligned}
\mu_{worker,worker\_id}(r)&=e_{W,r.worker\_id},\\
\mu_{receipt,receiver\_id}(r)&=e_{W,r.receiver\_id},\\
\mu_{contact,staff\_no}(r)&=e_{W,w.worker\_id},\quad
 w\in R_{worker},\ w.payroll\_no=r.staff\_no.
\end{aligned}
\]

마지막 식은 worker의 payroll_no 유일성으로 대상이 최대 하나임을 보장한다. FK는 NULL이 아닌 staff_no에 대해 대응 행의 존재도 보장한다. 그러나 **FK가 있다는 사실 자체가 두 행이 동일 Entity의 속성이라는 의미를 보장하지는 않는다.** 동일 대상의 추가 속성인지 별개 대상 사이의 관계인지는 비즈니스 의미로 구분한다.

하나의 테이블에는 여러 \(\mu_\rho\)가 존재할 수 있다. 예를 들어 goods_receipt의 receipt_id, request_id, receiver_id는 각각 Receipt, Receiving Request, Worker로 해석된다. 한 행에서 식별·참조되는 대상 집합을

\[
\operatorname{entities}(r)=\{\mu_\rho(r)\mid\rho\text{ applies to }T,\ \mu_\rho(r)\text{ is defined}\}
\]

로 정의할 수 있다. 따라서 일반적으로 Table→ET를 단일 함수로 고정하지 않는다. 스키마 수준에서 필요한 것은 **(table, columns, row condition)→ET 및 식별 규칙**의 집합이다. 실제 EEG는 이 규칙을 저장하며 모든 Entity 인스턴스를 노드로 저장할 필요가 없다.

정규 식별을 구현할 때는 `(ET, namespace, canonical key)`를 사용할 수 있다. 대응표로 연결된 별도 식별 범위는 정규 범위로 해석한 뒤 같은 Entity로 통합한다. 같은 타입의 독립 범위는 값이 같아도 분리한다. 대응을 모르는 범위는 동일성 미확정으로 남기며 실제로 다른 대상이라고 단정하지 않는다.

## 4. 저장 패턴과 빠뜨리기 쉬운 경계 사례

| 패턴 | 핵심 구분 | 현재 DB 사례 |
|---|---|---|
| 한 테이블, 한 주 대상 | 비식별 속성마다 ET를 만들지 않음 | UniversityFlow student |
| 한 테이블, 여러 대상 식별·참조 | 자신의 대상과 참조 대상을 구분 | registration: Registration + Student + Course |
| 같은 Entity의 속성 분할 | 같은 대상, 같은 단위, 선택적 확장 | admissions / admission_detail; worker / worker_contact |
| 다른 컬럼명, 같은 식별자 | 이름과 동일성을 분리 | receiver_id / worker_id |
| 다른 키 값, 같은 Entity | 명시적 유일 대응 필요 | staff_no → payroll_no → worker_id |
| 복합키 | 일부 컬럼만으로 대상 식별 불가 | registration(student_id, course_id) |
| 같은 컬럼명·값, 다른 대상 | 식별 범위와 타입을 보존 | HospitalFlow의 여러 order_id |
| 같은 ET, 다른 인스턴스 집합 | 타입 통합과 인스턴스 통합은 별개 | 별도 지역의 Worker 테이블 예시는 설명만 제공; 실DB 미추가 |
| 관계 자체가 독립 단위 | 연결된 두 대상을 병합하지 않음 | 수강등록은 학생도 강좌도 아님 |
| 반복 이력과 대상 | 이력의 PK와 참조 대상의 키를 구분 | assignment_grading의 반복 채점과 assignment |
| 행 조건에 따른 여러 참조 | 대상 컬럼이 NULL일 수 있음 | goods_movement의 receipt_id / dispatch_id |
| 1:1이어도 다른 대상 | cardinality만으로 동일성 판단 금지 | receiving_request / goods_receipt |
| 버전·역할·다형 참조·N:M | 추가 판별자, 유효기간 또는 연결 행이 필요할 수 있음 | 일반적 확장 사례; 이번 변경에서 전부 실DB에 추가한 것은 아님 |

‘여러 ET를 다루는 테이블’은 서로 다른 타입의 행을 섞어 저장하는 경우와, **각 행이 여러 타입의 대상을 참조하는 경우**가 다르다. 현재 registration은 후자다. 전자는 discriminator와 조건부 식별 규칙이 필요하며 이번 변경에서는 새로운 혼합 master 테이블을 추가하지 않았다.

## 5. Case notion과 case는 ET·Entity와 어떻게 연결되는가?

| 개념 | 질문 | Worker 예시 |
|---|---|---|
| Entity Type | 어떤 종류의 대상인가? | Worker |
| Entity | 그 종류에 속하는 어떤 개별 대상인가? | 작업자 1 |
| Case notion | 어떤 단위의 대상별로 이벤트를 묶어 프로세스를 볼 것인가? | 작업자 한 명을 한 case로 보는 관점 |
| Case | 선택한 분석 관점에서 하나의 이벤트 묶음이 귀속되는 개별 분석 단위 | 작업자 1을 나타내는 case |
| Case ID | 출력 로그에서 case를 식별하는 표현 | 현재 Worker Gold의 `L:1` |
| Trace | 한 case에 귀속된 이벤트들을 정해진 순서로 나열한 실행 이력 | 작업자 1의 입고등록·작업·점검 이벤트 이력 |

**ET와 Entity는 도메인의 대상·유형이고, case notion과 case는 그 대상을 프로세스 분석에 사용하는 역할이다.** Worker가 DB에 존재한다고 해서 항상 case notion인 것은 아니다. “작업자별 업무 이력”이라는 요청에서 Worker를 분석 단위로 선택할 때 case notion으로 사용한다. 개별 작업자는 이 관점에서 case를 나타낸다. 별개의 비즈니스 대상을 새로 생성하는 것은 아니다.

우리의 **Entity 기반 case 모델**에서는 다음 연결을 기본으로 한다.

- **Case notion의 핵심 결정:** 어떤 ET의 인스턴스를 case로 삼을지 선택한다.
- **Case:** 선택한 ET의 개별 Entity를 나타내는 분석 단위다.
- **Case population:** 그 ET의 Entity 중 식별이 검증되고 요청의 모집단 조건을 만족하는 대상들의 집합이다.
- **Case ID:** 해당 Entity의 정규 식별을 출력에 표현한 값이다. 임의의 source table PK 하나와 같아야 하는 것은 아니다.
- **Trace:** 그 case에 속하도록 승인된 이벤트의 순서 있는 이력이다. case 자체와 trace는 구분한다.

일반적인 process mining에서 case notion이 반드시 기존 ET 하나와 같아야 한다는 뜻은 아니다. 세션·시간 창·복합 업무 단위 등 다른 상관 규칙도 가능하다. **여기서 ET 선택으로 설명하는 것은 본 연구의 Entity 기반 정의**다. 선택한 ET가 granularity를 제공하고, 식별 규칙과 모집단 조건이 실제 case 집합을 확정한다. 활동 선택과 이벤트 귀속 규칙은 같은 case 단위에서 어떤 이력을 추출할지 결정하며 ET 자체의 정의와는 구분한다.

### 같은 DB를 다른 case notion으로 보기

WarehouseFlow의 `goods_receipt` 행 `receipt_id='001', request_id='001', receiver_id='1'`은 세 대상을 식별·참조한다. 이 행에서 기록된 Receipt Registered 발생은 요청의 관점에 따라 다르게 귀속될 수 있다.

| 분석 요청 | Case notion으로 사용하는 ET | 개별 case의 대상 | 입고등록 이벤트의 귀속 |
|---|---|---|---|
| 입고등록별 처리 이력 | Receipt | 입고등록 001 | 그 입고등록 case |
| 입고요청별 처리 이력 | Receiving Request | 입고요청 001 | request_id가 가리키는 요청 case |
| 작업자별 수행 이력 | Worker | 작업자 1 | receiver_id가 가리키는 작업자 case |

한 테이블에서 기록된 이벤트를 분석한다고 해서 그 테이블의 PK가 항상 case ID가 되는 것은 아니다. 반대로 작업자 1을 `worker_id`, `receiver_id`, `payroll_no`, `staff_no`로 발견해도 동일성이 검증되면 Worker 관점에서 **한 case**다. 여러 저장 표현의 수만큼 case를 생성하지 않는다. 참조 경로만으로 모든 관련 이벤트를 포함하지 않고, 해당 요청의 활동 범위와 검증된 귀속 의미를 적용한다.

### 함수와 집합으로 표현하기

요청을 \(q\), case notion으로 선택한 ET를 \(\tau\), 승인된 식별 규칙으로 얻은 Entity 집합을 \(\widehat{\mathcal E}_\tau\)라고 하자. 요청의 모집단 조건을 \(P_q(e)\)라고 하면 대상 집합은

\[
\mathcal E_{q,\tau}=\{e\in\widehat{\mathcal E}_\tau\mid P_q(e)\}.
\]

여기서 모집단 조건은 “특정 창고의 요청” 같은 대상 필터다. 이벤트 시간 필터를 case 생성일 필터로 자동 해석하지 않는다. case 대응 함수 \(c_{q,\tau}\)는 대상 Entity마다 서로 다른 case를 부여한다.

\[
c_{q,\tau}:\mathcal E_{q,\tau}\overset{1:1}{\longrightarrow}\mathcal C_{q,\tau},
\qquad
\mathcal C_{q,\tau}=\{c_{q,\tau}(e)\mid e\in\mathcal E_{q,\tau}\}.
\]

이것은 분석 관점 안에서의 1:1 대응이다. 동일 Entity가 다른 분석에서도 사용될 수 있다. case ID 직렬화는 namespace와 복합키를 보존하여 충돌하지 않아야 한다. 예시의 `L:1`은 현 데이터셋의 표기 관례이며 모든 DB에 통용되는 식별 규칙은 아니다.

요청에 맞게 선택된 실제 이벤트 발생 집합을 \(V_q\)라 하고, 검증된 이벤트 귀속 관계를

\[
A_{q,\tau}\subseteq V_q\times\mathcal C_{q,\tau}
\]

로 둔다. `(event occurrence, case)` 쌍을 통해 어떤 발생이 어느 case의 이력에 포함되는지 표현한다. 이 관계는 DB의 FK 관계와 같지 않다. case의 trace는

\[
\operatorname{trace}_{q,\tau}(c)
=\operatorname{order}_q\bigl(\{v\in V_q\mid(v,c)\in A_{q,\tau}\}\bigr).
\]

\(\operatorname{order}_q\)는 timestamp와 명시한 동률 처리 정책을 사용한다. 동일 timestamp의 정렬용 event ID가 실제 인과 순서를 증명하는 것은 아니다. 귀속 이벤트가 없는 case도 모집단에 남을 수 있으며, 일반 이벤트 행 CSV에는 나타나지 않을 수 있다. 같은 발생이 여러 case에 귀속되는 것을 허용한다면 그 다중성을 명시하고, 조인으로 생긴 같은 `(event, case)` 중복과 구분한다.

### 여러 ET가 요청에 관련될 때

여러 ET를 해석 후보로 유지하거나 최종 요청에 여러 ET가 관련되는 것은 가능하다. 이때 **관련 ET 수**, **case notion 수**, **case 수**는 다른 개념이다.

1. 주문별 분석에 고객·결제·배송이 관련되어도 case notion은 Order일 수 있다. 관련된 ET를 전부 case notion으로 삼는 것은 아니다.
2. “요청별 이력과 작업자별 이력”을 함께 요구하면 Receiving Request와 Worker 관점의 case 집합과 로그를 각각 정의할 수 있다. 한 ET를 초기에 강제로 고를 필요는 없다.
3. 두 ET를 한 복합 case로 사용하려면 “어떤 Entity 조합을 한 case로 보는가?”를 별도 정의해야 한다. 단순 ET 집합이나 PK 컬럼 나열은 복합 case의 의미·유효 조합·이벤트 귀속을 결정하지 못한다.
4. 객체 중심 이벤트 데이터로 여러 타입의 Entity와 이벤트 연결을 그대로 유지하는 출력도 별도 선택지다. 이를 기존 case 기반 CSV와 동일한 형식으로 간주하지 않는다.

위 식은 ET별 관점 하나를 설명한다. 여러 관점을 선택하면 각 \(\tau\)에 대해 적용한다. 복합 case 또는 객체 중심 출력을 현재 SQL compiler가 구현했다는 주장은 하지 않는다.

## 6. ET 발견과 이벤트 로그 추출에 주는 의미

1. 모든 테이블에서 PK·UNIQUE·FK와 식별자 후보를 조사한다. timestamp가 없는 테이블도 정체성 근거가 될 수 있다.
2. 행의 단위, 각 식별자의 의미, 자체 대상과 참조 대상을 구분한다. 코드 사전의 PK나 저장용 row_id를 자동으로 case ET로 만들지 않는다.
3. 동일 의미·동일 인스턴스 단위인 후보를 ET로 분류한다. 키 값의 중복은 타입 분류의 필수조건도 충분조건도 아니다.
4. 같은 ET 안에서 공유 식별자, 대응 식별자, 독립 식별 범위, 불확실성을 별도 결정한다. FK는 구조 근거이고, 의미 검토와 실제 유일성·참조 검증을 함께 사용한다.
5. Event candidate는 source table에 남긴다. 해당 행에서 어떤 ET 인스턴스를 식별할 수 있는지 검증된 규칙으로 연결한다. 연결 가능성과 그 Entity의 lifecycle에 포함할지는 별도 판단이다.
6. case population은 승인된 Entity 표현의 합집합을 동일성 기준으로 정규화한다. Entity 통합 때문에 서로 다른 event occurrence를 합치지 않는다.

이 절차는 설계 제안이다. 현재 저장소의 legacy 단일 table→ET 라벨 전체를 자동으로 올바른 새 ET 라벨로 변환한 것으로 해석해서는 안 된다.
