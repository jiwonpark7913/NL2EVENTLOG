PRAGMA foreign_keys=ON;
CREATE TABLE slab_material (slab_id TEXT PRIMARY KEY, charge_id TEXT NOT NULL);
CREATE TABLE planned_rolling_instruction (plan_id TEXT PRIMARY KEY, slab_id TEXT NOT NULL REFERENCES slab_material(slab_id), planned_reheat_at TEXT NOT NULL);
CREATE TABLE rolling_instruction (instruction_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL UNIQUE REFERENCES planned_rolling_instruction(plan_id), released_at TEXT NOT NULL);
CREATE TABLE as_rolled_material (material_id TEXT PRIMARY KEY, as_rolled_plate_no TEXT NOT NULL UNIQUE, slab_id TEXT NOT NULL UNIQUE REFERENCES slab_material(slab_id), instruction_id TEXT NOT NULL UNIQUE REFERENCES rolling_instruction(instruction_id), furnace_charged_at TEXT , crop_shear_passed_at TEXT , latest_operation_completed_at TEXT , created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE furnace_charge_tracking (tracking_id TEXT PRIMARY KEY, material_id TEXT NOT NULL UNIQUE REFERENCES as_rolled_material(material_id), yard_instruction_received_at TEXT NOT NULL, lot_charging_started_at TEXT NOT NULL);
CREATE TABLE cutting_finishing_instruction (instruction_id TEXT PRIMARY KEY, material_id TEXT NOT NULL UNIQUE REFERENCES as_rolled_material(material_id), released_at TEXT NOT NULL, cut_method TEXT NOT NULL CHECK(cut_method='SPLIT'));
CREATE TABLE plate_material (plate_material_id TEXT PRIMARY KEY, plate_no TEXT NOT NULL UNIQUE, parent_as_rolled_plate_no TEXT NOT NULL REFERENCES as_rolled_material(as_rolled_plate_no), dimension_inspected_at TEXT , latest_operation_completed_at TEXT );
CREATE TABLE operation_code (code TEXT PRIMARY KEY, meaning TEXT NOT NULL UNIQUE);
CREATE TABLE material_operation_history (transaction_id TEXT PRIMARY KEY, material_id TEXT NOT NULL, operation_code TEXT NOT NULL REFERENCES operation_code(code), started_at TEXT NOT NULL, completed_at TEXT NOT NULL CHECK(completed_at > started_at), created_at TEXT NOT NULL);
CREATE TRIGGER validate_history_material BEFORE INSERT ON material_operation_history WHEN NOT EXISTS(SELECT 1 FROM as_rolled_material WHERE material_id=NEW.material_id) AND NOT EXISTS(SELECT 1 FROM plate_material WHERE plate_material_id=NEW.material_id) BEGIN SELECT RAISE(ABORT,'Unknown material'); END;

-- Authored lifecycle extensions
CREATE TABLE slab_material_activity (event_id TEXT PRIMARY KEY, slab_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (slab_id) REFERENCES slab_material(slab_id));
CREATE TABLE planned_rolling_instruction_activity (event_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (plan_id) REFERENCES planned_rolling_instruction(plan_id));
CREATE TABLE rolling_instruction_activity (event_id TEXT PRIMARY KEY, instruction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (instruction_id) REFERENCES rolling_instruction(instruction_id));
CREATE TABLE furnace_charge_tracking_activity (event_id TEXT PRIMARY KEY, tracking_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (tracking_id) REFERENCES furnace_charge_tracking(tracking_id));
CREATE TABLE cutting_finishing_instruction_activity (event_id TEXT PRIMARY KEY, instruction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (instruction_id) REFERENCES cutting_finishing_instruction(instruction_id));
CREATE TABLE plate_material_activity (event_id TEXT PRIMARY KEY, plate_material_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (plate_material_id) REFERENCES plate_material(plate_material_id));
CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id));
