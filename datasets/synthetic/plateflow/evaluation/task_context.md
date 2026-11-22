# Recorded manufacturing lifecycle convention

- Requests can select actual recorded starts, completions and point milestones. The full recorded lifecycle includes both actual starts and completions when present; an unfinished occurrence supplies its start only. Scheduled or database-maintenance times do not establish manufacturing work.
- A slab view includes its recorded receipt/preparation, related planning and issued instructions, and actual processing of its mother material and descendant pieces.
- A rolling-plan view includes its own submission/approval/release history, the issue of its related instruction, and the actual work and piece history performed under that instruction.
- A rolling-instruction view includes its issue and the actual work and piece history performed under that instruction.
- A mother-material view includes actual work on that material and the history of all plate pieces derived from it.
- A plate-piece view includes its identification, actual processing, inspections, reviews, release and packing.
- An equipment view includes actual work performed by that unit.
- An individual inspection, review or work-record view includes the actual start and completion documented by that particular record. Repeat records are distinct occurrences.
- Full recorded lifecycle means the entire scope above for the requested case concept. It does not infer undocumented casting or dispatch. An empty recorded case remains a case even though its event log contains no rows.
