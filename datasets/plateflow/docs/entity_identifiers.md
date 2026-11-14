# plateflow — 식별자와 대상 참조 목록

실제 SQLite의 전체 PK·UNIQUE·FK를 조사한 구조 목록이다. ET 예측이나 table→ET Gold가 아니다.

[개념 설명](../../../docs/system/ENTITY_IDENTITY_AND_STORAGE.md) · [저장 사례](../../ENTITY_STORAGE_CASES.md)

| Table | Rows | 완전한 PK | UNIQUE 인덱스 | 선언된 참조 |
|---|---:|---|---|---|
| as_rolled_material | 26 | material_id | (instruction_id); (slab_id); (plate_no); (material_id) | (instruction_id) → rolling_instruction(instruction_id); (slab_id) → slab_material(slab_id) |
| dimension_inspection | 46 | inspection_id | (inspection_id) | (plate_id) → plate_material(plate_id) |
| equipment | 7 | equipment_id | (equipment_code); (equipment_id) |  |
| finishing_operation_history | 130 | operation_id | (operation_id) | (process_group, operation_code) → process_code(process_group, code); (equipment_id) → equipment(equipment_id); (plate_id) → plate_material(plate_id) |
| furnace_operation_history | 70 | operation_id | (operation_id) | (process_group, operation_code) → process_code(process_group, code); (equipment_id) → equipment(equipment_id); (material_id) → as_rolled_material(material_id) |
| planned_rolling_instruction | 28 | plan_id | (slab_id); (plan_id) | (slab_id) → slab_material(slab_id) |
| plate_material | 38 | plate_id | (plate_no); (plate_id) | (mother_material_id) → as_rolled_material(material_id) |
| plate_quality_review | 46 | review_id | (review_id) | (plate_id) → plate_material(plate_id) |
| process_code | 8 | process_group, code | (process_group, code) |  |
| rolling_instruction | 26 | instruction_id | (plan_id); (instruction_id) | (plan_id) → planned_rolling_instruction(plan_id) |
| rolling_operation_history | 44 | operation_id | (operation_id) | (process_group, phase_code) → process_code(process_group, code); (equipment_id) → equipment(equipment_id); (material_id) → as_rolled_material(material_id) |
| slab_material | 30 | slab_id | (slab_id) |  |

UNIQUE 인덱스에는 PK 인덱스도 포함될 수 있다. NULL 허용 UNIQUE는 전체 행의 완전한 식별을 보장하지 않는다. FK가 없는 동일성은 이 구조 목록만으로 판별할 수 없다.
