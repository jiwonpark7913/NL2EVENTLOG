PRAGMA foreign_keys=ON;
CREATE TABLE admission_detail(hadm_id INTEGER PRIMARY KEY NOT NULL REFERENCES admissions(hadm_id), discharge_summary_signed_at TEXT NOT NULL);
CREATE TABLE "admissions"(
        hadm_id INTEGER PRIMARY KEY NOT NULL,
        subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
        admittime TEXT NOT NULL,
        dischtime TEXT,
        deathtime TEXT,
        admission_type TEXT NOT NULL,
        admit_provider_id TEXT,
        admission_location TEXT,
        discharge_location TEXT,
        insurance TEXT,
        language TEXT,
        marital_status TEXT,
        race TEXT,
        edregtime TEXT,
        edouttime TEXT,
        hospital_expire_flag INTEGER NOT NULL DEFAULT 0 CHECK(hospital_expire_flag IN (0,1)),
        CHECK(dischtime IS NULL OR admittime<=dischtime),
        CHECK(edouttime IS NULL OR edregtime IS NOT NULL),
        CHECK(edouttime IS NULL OR edregtime<=edouttime)
    );
CREATE TABLE emar(emar_id INTEGER PRIMARY KEY NOT NULL, pharmacy_id INTEGER NOT NULL REFERENCES pharmacy(pharmacy_id), charttime TEXT NOT NULL, event_txt TEXT NOT NULL CHECK(event_txt IN ('Administered','Not Given')), storetime TEXT NOT NULL, CHECK(charttime<=storetime));
CREATE TABLE lab_order(order_id INTEGER PRIMARY KEY NOT NULL, subject_id INTEGER NOT NULL REFERENCES patients(subject_id), hadm_id INTEGER REFERENCES admissions(hadm_id), specimen_received_at TEXT, results_verified_at TEXT);
CREATE TABLE labevents(labevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES lab_order(order_id), itemid INTEGER NOT NULL, charttime TEXT NOT NULL, storetime TEXT NOT NULL, valuenum REAL, valueuom TEXT, CHECK(charttime<=storetime));
CREATE TABLE medication_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), medication TEXT NOT NULL, stopped_at TEXT);
CREATE TABLE order_history(history_id INTEGER PRIMARY KEY NOT NULL, lab_order_id INTEGER REFERENCES lab_order(order_id), medication_order_id INTEGER REFERENCES medication_order(order_id), procedure_order_id INTEGER REFERENCES procedure_order(order_id), action TEXT NOT NULL CHECK(action IN ('E','R','C')), occurred_at TEXT NOT NULL, CHECK((lab_order_id IS NOT NULL)+(medication_order_id IS NOT NULL)+(procedure_order_id IS NOT NULL)=1));
CREATE TABLE "patients"(
        subject_id INTEGER PRIMARY KEY NOT NULL,
        gender TEXT NOT NULL CHECK(gender IN ('F','M')),
        anchor_age INTEGER NOT NULL CHECK(anchor_age BETWEEN 0 AND 91),
        anchor_year INTEGER NOT NULL,
        anchor_year_group TEXT NOT NULL,
        dod TEXT
    );
CREATE TABLE pharmacy(pharmacy_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES medication_order(order_id), dispensed_at TEXT NOT NULL);
CREATE TABLE procedure_episode(procedureevent_id INTEGER PRIMARY KEY NOT NULL, order_id INTEGER NOT NULL REFERENCES procedure_order(order_id), starttime TEXT NOT NULL, endtime TEXT, storetime TEXT NOT NULL, CHECK(endtime IS NULL OR starttime<=endtime));
CREATE TABLE procedure_order(order_id INTEGER PRIMARY KEY NOT NULL, hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id), procedure_name TEXT NOT NULL, preparation_completed_at TEXT);
CREATE TABLE transfers(
        subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
        hadm_id INTEGER REFERENCES admissions(hadm_id),
        transfer_id INTEGER PRIMARY KEY NOT NULL,
        eventtype TEXT CHECK(eventtype IN ('ed','admit','transfer','discharge')),
        careunit TEXT,
        intime TEXT,
        outtime TEXT,
        CHECK(outtime IS NULL OR intime IS NULL OR intime<=outtime)
    );
