# Entity 저장 사례와 데이터셋 변경

[처음 읽는 사람을 위한 용어·함수·통합 예시](../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [논문용 영어 LaTeX](../docs/paper/entity_identity_storage.tex)

## 현재 DB에서 확인한 사례

아래 타입명은 이 사례의 의미를 설명하는 이름이다. 기존 source-table 분류 개수나 legacy Gold 라벨을 새로운 전체 ET 정답으로 승인하는 표가 아니다. 구조 전체는 각 DB의 실제 PK·UNIQUE·FK 목록에서 확인할 수 있다.

| 요청한 사례 | 데이터셋과 실제 위치 | 대상과 식별자 해석 |
|---|---|---|
| 1. 한 테이블이 한 종류의 대상을 기술 | UniversityFlow `student` | student_id는 학생 한 명을 식별; name, major는 속성 |
| 2. 한 테이블이 여러 타입의 대상을 다룸 | UniversityFlow `registration` | (student_id, course_id)는 수강등록 한 건; 각 FK는 Student와 Course 참조 |
| 3. 같은 Entity를 여러 테이블에 나누어 저장 | HospitalFlow `admissions`, `admission_detail` | 같은 hadm_id의 입원 한 건; detail은 선택적 요약 서명 속성 |
| 4a. 이름은 다르나 같은 키 범위 | WarehouseFlow `goods_receipt.receiver_id`, `worker.worker_id` | receiver_id는 입고등록 자체의 ID가 아니라 참여 작업자 참조 |
| 4b. 이름과 키 값 모두 다름 | WarehouseFlow `worker_contact.staff_no`, `worker.payroll_no`, `worker.worker_id` | staff_no=PAY-1001은 worker 행의 대응을 통해 worker_id=1로 해석 |
| 선택적·부분 저장 | WarehouseFlow `worker_contact` | 작업자 7명 중 3명의 추가 속성; 새 Worker나 새 이벤트를 만들지 않음 |
| 복합키와 서로 다른 단위 | UniversityFlow `registration` | student_id 하나로 수강등록을 식별하지 않음; 학생 단위와 등록 단위 구분 |
| 같은 이름·값, 다른 대상 | HospitalFlow `lab_order.order_id`, `medication_order.order_id` | 30000117 등이 양쪽에 있지만 서로 다른 주문과 식별 범위 |
| 반복 이력 행과 대상의 구분 | UniversityFlow `assignment_grading` | (assignment_id, instructor_id, grading_time)가 채점 기록; assignment_id는 과제 참조. 동일 과제의 재채점은 별도 기록 |
| 조건부·NULL 참조 | WarehouseFlow `goods_movement` | 입고에는 receipt_id, 출고에는 dispatch_id; 한쪽이 NULL인 것은 대상 부재가 아닌 구조적 비해당 |
| 1:1 관계이나 다른 대상 | WarehouseFlow `receiving_request`, `goods_receipt` | 요청과 실제 입고등록은 별개 대상; UNIQUE FK만으로 같은 Entity로 합치지 않음 |
| 단일 컬럼이 아닌 참조 | PlateFlow `process_code`와 공정 이력 | (process_group, code) 전체가 코드 의미를 결정. 코드 사전 행을 무조건 분석 case로 승인하지 않음 |
| 모체·결과물 관계와 동일성의 구분 | PlateFlow `as_rolled_material`, `plate_material` | mother_material_id는 계보 관계; 같은 물체라는 판단을 FK만으로 하지 않음 |

이름이 다른 것은 Entity 자체의 이름이 바뀌는 것이 아니라 **동일 Entity를 식별하는 DB 표현이 다른 것**이다. 업무 역할명(receiver)도 별도 타입을 의미하지 않는다.

## 실제 변경 범위

- 기존 네 DB의 구조와 실제 데이터를 조사하여 [전체 기계 판독 목록](entity_identifier_inventory.json) 및 각 DB의 `docs/entity_identifiers.md`를 추가했다.
- WarehouseFlow의 기존 worker에 NULL 허용 UNIQUE payroll_no를 추가했다. 모든 현재 작업자에게 값이 있지만, 이후 미기록 값은 NULL로 표현할 수 있다.
- `worker_contact(staff_no PK/FK → worker.payroll_no, contact_channel)`를 추가했다. 세 행은 기존 작업자 1·3·5의 추가 속성이다. 정체성 대응은 문자열 패턴이 아니라 worker 행과 UNIQUE/FK로 보장된다.
- 기존 이벤트·질문·Gold SQL·Gold CSV는 변경하지 않았다. 새 테이블에는 timestamp가 없고 기존 case population도 늘어나지 않는다.
- 추가 속성 예제는 `python datasets/warehouseflow/entity_storage.py`로 재적용할 수 있다. warehouse builder도 생성 종료 시 같은 함수를 호출한다. 전체 레거시 builder 및 후속 코드 의미 migration의 재현성은 별도 문제이며 이번 검증은 현재 DB와 Gold에 대해 수행한다.
- 기본 사전·DDL·draw.io/PNG·테이블 미리보기를 갱신했다. 기존 legacy ET→ER 도표는 이 새 테이블이나 다중 식별자 모델의 정답이 아니므로 그 범위를 별도 표시한다.

## 빠뜨리기 쉬우나 이번에 실DB로 모두 추가하지 않은 사례

- **같은 ET, 서로 다른 인스턴스 집합:** 지역별 작업자 테이블처럼 타입은 같아도 서로 다른 사람일 수 있다. 동일 인스턴스 교집합이 ET 통합의 전제는 아니다.
- **동일 타입의 독립 범위와 불확실한 대응:** 서로 다른 시스템의 worker_id=1이 같은 사람인지 모를 수 있다. 불확실성을 실제 상이함과 구분한다.
- **하나의 테이블에 서로 다른 타입의 행이 혼재:** `party(kind, id, ...)`에서 개인·조직을 구별하는 경우. 여러 FK로 여러 대상을 참조하는 registration과 다르다.
- **시간에 따른 버전과 키 재사용:** 같은 대상의 여러 버전인지, 동일 번호를 재사용한 다른 대상인지 유효기간을 통해 판별해야 할 수 있다.
- **다대다, 동일 타입의 여러 역할, 명시적 N:1/1:N 대응:** 키 두 개를 합치거나 일반적 FK를 동일성 대응으로 해석하면 안 된다. 비유일 대응은 단일 Entity 해석으로 승인하지 않는다.
- **FK 없는 동일성:** 명시적 사전·업무 대응표가 근거가 될 수 있지만 값의 중복이나 이름 유사도만으로 확정하지 않는다.

## 검증과 사용 경계

`python tools/validation/validate_entity_storage.py`는 네 DB의 무결성과 모든 기존 Gold SQL/CSV 일치, 명시적 양성/음성 저장 사례, WarehouseFlow DDL 왕복 및 추가 예제의 재적용을 검사한다. 이 검증은 데이터 정합성 확인이며 ET 추론 정확도 실험이 아니다. SQL 사례와 사례 문서는 author-only이며 기본 model input에 넣지 않는다. 모델에는 DB와 일반 비즈니스 사전만 제공하고 정답 규칙은 주지 않는다.

| Dataset | 식별자 목록 |
|---|---|
| UniversityFlow | [PK·UNIQUE·FK](universityflow/docs/entity_identifiers.md) |
| HospitalFlow | [PK·UNIQUE·FK](hospitalflow/docs/entity_identifiers.md) |
| WarehouseFlow | [PK·UNIQUE·FK](warehouseflow/docs/entity_identifiers.md) |
| PlateFlow | [PK·UNIQUE·FK](plateflow/docs/entity_identifiers.md) |

## Case notion과 case

[개념 문서의 case 정의·함수·예시](../docs/system/ENTITY_IDENTITY_AND_STORAGE.md#5-case-notion과-case는-etentity와-어떻게-연결되는가)를 참고한다. Worker를 분석 단위로 선택하면 개별 작업자가 case가 된다. 작업자 1이 worker, worker_contact, goods_receipt에 여러 식별자로 등장해도 한 Worker case이며, 연락 속성 3행이 전체 작업자 모집단 7명을 대체하지 않는다. 같은 입고등록 발생도 Receipt·Receiving Request·Worker 관점에서 각각 다른 대상의 case에 귀속될 수 있다. 여러 관련 ET가 있다는 이유만으로 복합 case를 자동 생성하지 않는다.
