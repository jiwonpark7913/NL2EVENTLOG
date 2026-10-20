# Inspecting object/type membership

- This DB explicitly tests **different tables → one common semantic type**. Registry IDs do not contain precomputed event attribution.
- All 45 order objects share CLINICAL_ORDER; the subtype is checked separately.
- A common type selects the case population; it does not combine all orders into one case.

```sql
SELECT o.type_code,c.order_kind,o.object_id,l.order_id lab_local_id,m.order_id medication_local_id,p.order_id procedure_local_id FROM object o JOIN clinical_order c USING(object_id) LEFT JOIN lab_order l USING(object_id) LEFT JOIN medication_order m USING(object_id) LEFT JOIN procedure_order p USING(object_id) ORDER BY COALESCE(l.order_id,m.order_id,p.order_id),c.order_kind;
```

| Type | Subtype | Object | Local order ID |
| --- | --- | --- | --- |
| CLINICAL_ORDER | LAB | LAB:1 | 1 |
| CLINICAL_ORDER | MED | MED:1 | 1 |
| CLINICAL_ORDER | PROC | PROC:1 | 1 |
| CLINICAL_ORDER | LAB | LAB:2 | 2 |
| CLINICAL_ORDER | MED | MED:2 | 2 |
| CLINICAL_ORDER | PROC | PROC:2 | 2 |
| CLINICAL_ORDER | LAB | LAB:3 | 3 |
| CLINICAL_ORDER | MED | MED:3 | 3 |
| CLINICAL_ORDER | PROC | PROC:3 | 3 |
| CLINICAL_ORDER | LAB | LAB:4 | 4 |
| CLINICAL_ORDER | MED | MED:4 | 4 |
| CLINICAL_ORDER | PROC | PROC:4 | 4 |

- [All memberships as JSON](object_type_membership.json)
- Common-type full logs: HF03/HF03P. Subtype full logs: HF04–HF06 and their P pairs. H02/H02P explicitly request events across all three subtype tables.
- Membership triggers and composite subtype FKs reject wrong classifications. Private history links are an independent oracle and are not consulted by extraction SQL.
