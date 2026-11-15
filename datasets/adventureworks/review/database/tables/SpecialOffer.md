# SpecialOffer

**Rows:** 16 · **Columns:** 11

## Original records (first 10)

| SpecialOfferID | Description | DiscountPct | Type | Category | StartDate | EndDate | MinQty | MaxQty | rowguid | ModifiedDate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | No Discount | .0000 | No Discount | No Discount | 2022-04-30 00:00:00.000 | 2025-11-29 00:00:00.000 | 0 | NULL | 0290C4F5-191F-4337-AB6B-0A2DDE03CBF9 | 2022-03-31 00:00:00.000 |
| 2 | Volume Discount 11 to 14 | .0200 | Volume Discount | Reseller | 2022-05-30 00:00:00.000 | 2025-05-29 00:00:00.000 | 11 | 14 | D7542EE7-15DB-4541-985C-5CC27AEF26D6 | 2022-04-30 00:00:00.000 |
| 3 | Volume Discount 15 to 24 | .0500 | Volume Discount | Reseller | 2022-05-30 00:00:00.000 | 2025-05-29 00:00:00.000 | 15 | 24 | 4BDBCC01-8CF7-40A9-B643-40EC5B717491 | 2022-04-30 00:00:00.000 |
| 4 | Volume Discount 25 to 40 | .1000 | Volume Discount | Reseller | 2022-05-30 00:00:00.000 | 2025-05-29 00:00:00.000 | 25 | 40 | 504B5E85-8F3F-4EBC-9E1D-C1BC5DEA9AA8 | 2022-04-30 00:00:00.000 |
| 5 | Volume Discount 41 to 60 | .1500 | Volume Discount | Reseller | 2022-05-30 00:00:00.000 | 2025-05-29 00:00:00.000 | 41 | 60 | 677E1D9D-944F-4E81-90E8-47EB0A82D48C | 2022-04-30 00:00:00.000 |
| 6 | Volume Discount over 60 | .2000 | Volume Discount | Reseller | 2022-05-30 00:00:00.000 | 2025-05-29 00:00:00.000 | 61 | NULL | 8157F569-4E8D-46B6-9347-5D0F726A9439 | 2022-04-30 00:00:00.000 |
| 7 | Mountain-100 Clearance Sale | .3500 | Discontinued Product | Reseller | 2023-04-13 00:00:00.000 | 2023-05-29 00:00:00.000 | 0 | NULL | 7DF15BF5-6C05-47E7-80A4-22BD1CE59A72 | 2023-03-14 00:00:00.000 |
| 8 | Sport Helmet Discount-2002 | .1000 | Seasonal Discount | Reseller | 2023-05-30 00:00:00.000 | 2023-06-29 00:00:00.000 | 0 | NULL | 20C5D2CC-A38F-48F8-AC9A-8F15943E52AE | 2023-04-30 00:00:00.000 |
| 9 | Road-650 Overstock | .3000 | Excess Inventory | Reseller | 2023-05-30 00:00:00.000 | 2023-07-30 00:00:00.000 | 0 | NULL | 0CF8472B-F9E6-4945-9E09-549D7DDE2198 | 2023-04-30 00:00:00.000 |
| 10 | Mountain Tire Sale | .5000 | Excess Inventory | Customer | 2024-05-13 00:00:00.000 | 2024-07-28 00:00:00.000 | 0 | NULL | 220444AD-2EF3-4E4C-87E9-3AA6EE39A877 | 2024-04-13 00:00:00.000 |

## Column definitions

| Column | SQL type | PK | Not null |
|---|---|---|---|
| SpecialOfferID | INTEGER | True | True |
| Description | TEXT | False | True |
| DiscountPct | TEXT | False | True |
| Type | TEXT | False | True |
| Category | TEXT | False | True |
| StartDate | TEXT | False | True |
| EndDate | TEXT | False | True |
| MinQty | INTEGER | False | True |
| MaxQty | INTEGER | False | False |
| rowguid | TEXT | False | True |
| ModifiedDate | TEXT | False | True |
