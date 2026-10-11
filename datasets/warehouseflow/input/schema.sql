PRAGMA foreign_keys=ON;
CREATE TABLE warehouse (warehouse_number TEXT NOT NULL, address TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity > 0), PRIMARY KEY (warehouse_number));
CREATE TABLE goods (goods_id TEXT NOT NULL, goods_name TEXT NOT NULL, PRIMARY KEY (goods_id));
CREATE TABLE loader (name TEXT NOT NULL, phone TEXT NOT NULL, loader_id TEXT NOT NULL, PRIMARY KEY (loader_id));
CREATE TABLE transaction_record (transaction_id TEXT NOT NULL, occurred_at TEXT NOT NULL, warehouse_number TEXT NOT NULL, transaction_type TEXT NOT NULL CHECK(transaction_type IN ('IN','OUT')), PRIMARY KEY (transaction_id), FOREIGN KEY (warehouse_number) REFERENCES warehouse(warehouse_number));
CREATE TABLE goods_transaction_detail (goods_id TEXT NOT NULL, transaction_id TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0), PRIMARY KEY (goods_id,transaction_id), FOREIGN KEY (goods_id) REFERENCES goods(goods_id), FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id));
CREATE TABLE loader_transaction (loader_id TEXT NOT NULL, transaction_id TEXT NOT NULL, PRIMARY KEY (loader_id,transaction_id), FOREIGN KEY (loader_id) REFERENCES loader(loader_id), FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id));

-- Authored lifecycle extensions
CREATE TABLE transaction_record_activity (event_id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL, activity TEXT NOT NULL, occurred_at TEXT NOT NULL, outcome TEXT NOT NULL, FOREIGN KEY (transaction_id) REFERENCES transaction_record(transaction_id));
CREATE TABLE lifecycle_case_link(event_id TEXT NOT NULL,case_table TEXT NOT NULL,case_id TEXT NOT NULL,PRIMARY KEY(event_id,case_table,case_id));
