# ProductVendor

**Rows:** 460 · **Columns:** 11

## Original records (first 10)

| ProductID | BusinessEntityID | AverageLeadTime | StandardPrice | LastReceiptCost | LastReceiptDate | MinOrderQty | MaxOrderQty | OnOrderQty | UnitMeasureCode | ModifiedDate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1580 | 17 | 47.8700 | 50.2635 | 2022-08-28 00:00:00.000 | 1 | 5 | 3 | CS  | 2022-08-28 00:00:00.000 |
| 2 | 1688 | 19 | 39.9200 | 41.9160 | 2022-08-28 00:00:00.000 | 1 | 5 | 3 | CTN | 2022-08-28 00:00:00.000 |
| 4 | 1650 | 17 | 54.3100 | 57.0255 | 2022-08-28 00:00:00.000 | 1 | 5 | NULL | CTN | 2022-08-28 00:00:00.000 |
| 317 | 1578 | 19 | 28.1700 | 29.5785 | 2022-08-28 00:00:00.000 | 100 | 1000 | 300 | EA  | 2022-08-28 00:00:00.000 |
| 317 | 1678 | 17 | 25.7700 | 27.0585 | 2022-08-24 00:00:00.000 | 100 | 1000 | NULL | EA  | 2022-08-24 00:00:00.000 |
| 318 | 1578 | 19 | 34.3800 | 36.0990 | 2022-08-28 00:00:00.000 | 100 | 1000 | NULL | EA  | 2022-08-28 00:00:00.000 |
| 318 | 1678 | 17 | 31.9800 | 33.5790 | 2022-08-24 00:00:00.000 | 100 | 1000 | 300 | EA  | 2022-08-24 00:00:00.000 |
| 319 | 1556 | 19 | 44.2100 | 46.4205 | 2022-08-28 00:00:00.000 | 100 | 1000 | 300 | EA  | 2022-08-28 00:00:00.000 |
| 319 | 1578 | 19 | 46.2700 | 48.5835 | 2022-08-28 00:00:00.000 | 100 | 1000 | NULL | EA  | 2022-08-28 00:00:00.000 |
| 319 | 1678 | 17 | 43.8700 | 46.0635 | 2022-08-24 00:00:00.000 | 100 | 1000 | NULL | EA  | 2022-08-24 00:00:00.000 |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| ProductID | INTEGER | True | True |
| BusinessEntityID | INTEGER | True | True |
| AverageLeadTime | INTEGER | False | True |
| StandardPrice | TEXT | False | True |
| LastReceiptCost | TEXT | False | False |
| LastReceiptDate | TEXT | False | False |
| MinOrderQty | INTEGER | False | True |
| MaxOrderQty | INTEGER | False | True |
| OnOrderQty | INTEGER | False | False |
| UnitMeasureCode | TEXT | False | True |
| ModifiedDate | TEXT | False | True |
