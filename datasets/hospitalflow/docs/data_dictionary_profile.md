# Business data dictionary field profile

- **Basis:** Harvard HMS Data Dictionary and OSF How to Make a Data Dictionary, consulted 2026-11-03.
- These are documentation guides, not one mandatory universal or certified dictionary standard. The following is the project's chosen relational-data profile.
- Harvard lists variable name, human-readable name, unit, allowed values and definition. OSF also describes optional synonyms and extended descriptions.
- OSF's Other resources heading is a section linking further resources; it is not a mandatory per-variable field. Definition references are a useful optional project addition.

## 1. Dataset/document context

| Item | Purpose | HospitalFlow treatment |
|---|---|---|
| Dictionary/dataset name and identifier | Identify the documented data | HospitalFlow and a stable dictionary ID |
| Version/review date | Track changes | Version 2026-11-03 |
| Description and provenance | Explain the represented data and source | MIMIC-inspired, authored adaptations, wholly synthetic records |
| Language and DBMS | State interpretation/storage context | English and SQLite |
| Datetime convention | Avoid ambiguous time representations | UTC RFC 3339 text with second precision |
| Maintainer | Identify responsibility | NL2EVENTLOG project maintainers |

- This short context section is useful, but it does not substitute for variable definitions and is not mandated by the Harvard variable checklist.
- Dictionary status must not imply ISO registration, certification or an independent clinical review.

## 2. Table-level relational documentation

| Item | Purpose | Status in this project |
|---|---|---|
| Physical table name | Match the actual database | Required |
| Readable table name | Explain abbreviations | Required |
| Business definition | Explain what is recorded | Required |
| Row grain | Explain exactly what one record represents | Required |
| Primary key and uniqueness | Define physical identity | Required when declared |
| Declared foreign keys | Describe enforced references | Required when declared |
| Documented logical relationships | Describe relationships not declared as FKs | Conditional; must be distinguished from SQL enforcement |
| Table CHECK constraints / DDL | Preserve actual structural rules | Required where applicable |

## 3. Variable-level documentation

| Item | Meaning | Source/profile status |
|---|---|---|
| Variable name | Exact physical column name | Harvard/OSF core guidance |
| Readable name | Short human-readable label | Harvard/OSF core guidance |
| Definition | Context-specific, non-circular meaning | Harvard/OSF core guidance |
| Measurement unit | Unit of a measured quantity | Harvard/OSF core guidance; Not applicable for identifiers or point-in-time values |
| Allowed values and code meanings | Controlled vocabulary or documented domain; actual bounds when defined | Harvard/OSF core guidance |
| Synonyms | Justified contextual alternative terms | OSF optional; empty if no justified synonym |
| Extended description | Interpretation details beyond a concise definition | OSF optional |
| Definition references | Provenance of a definition or business convention | Optional project addition |
| Declared SQL type and semantic representation | Distinguish TEXT storage from a datetime meaning | Relational project extension |
| Format, timezone and precision | Specify how dates/numbers are represented | Conditional relational extension |
| Required/nullable and NULL meaning | Distinguish absent, pending or inapplicable values | Relational project extension |
| PK/FK membership and uniqueness | Document identity and references | Relational project extension |
| Default, length and CHECK constraints | Describe actual storage constraints | Relational project extension |
| Domain enforcement basis | Distinguish SQL restrictions from documented conventions | Relational project extension |

- Do not infer allowed ranges from observed sample minima/maxima. Sample values can be examples but are not an allowed-value definition.
- An unset minimum/maximum means no additional business bound has been declared; it does not cancel the underlying SQL datatype/key rules.
- UTC is a timezone, not a measurement unit. The numeric laboratory result uses the unit specified by valueuom in the same row.
- A column's NULL meaning must be stated specifically. NULL does not universally establish that a business action never occurred.
- Do not invent synonyms from evaluation paraphrases or missing clinical code descriptions from sample IDs.
- Metadata should faithfully describe the schema. It should not silently add a constraint that the DB does not enforce.

## 4. Material outside the model-facing business dictionary

- Table event/row/column classification, activity-carrier answers, selected event-time counts, query-specific scope catalogues, Gold ES/SQL and model evaluation instructions belong in author/evaluation material.
- Ordinary code meanings, datetime meanings and documented identifier relationships remain legitimate business metadata.
- The HospitalFlow default model-input manifest excludes README, source, design, docs, private and the optional explicit activity-scope catalog.

## References

- [Harvard HMS Data Dictionary](https://datamanagement.hms.harvard.edu/collect-analyze/documentation-metadata/data-dictionary)
- [OSF How to Make a Data Dictionary](https://help.osf.io/article/217-how-to-make-a-data-dictionary)
- [SQLite CREATE TABLE](https://www.sqlite.org/lang_createtable.html)

## Author notes moved out of model inputs

- Basic information is document context, not a mandatory per-variable field in a universal standard. Harvard/OSF guidance does not certify the dictionary.
- UTC is a timezone, not a measurement unit. Identifier and datetime units are Not applicable; numeric results use the corresponding valueuom.
- Unset minimum/maximum does not remove underlying datatype/key rules. Observed sample minima/maxima are not allowed-value constraints.
- The DB is not declared STRICT. Documented types and RFC 3339 datetime conventions are not complete SQL format validators. Foreign-key enforcement requires PRAGMA foreign_keys=ON.
- SQL CHECK accepts TRUE or UNKNOWN. Specifically, NULL discharge authorization does not prevent recording discharge; this interpretation remains with the relevant table definition because it affects business data.
- No special missing-value sentinel is defined. Clinical timestamp NULL means occurrence status unknown; structural reference NULL has its column-specific non-applicable/no-association meaning.
- Full model JSON omits documentation_basis and document-maintainer/provenance commentary. The reviewed author profile retains that material separately. The business MD contains no guidance-method introduction or documentation-reference appendix.
- [Current clinical-time and NULL review](semantic_review.md) · [Dictionary input conditions](dictionary_ablation.md)
