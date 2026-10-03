# AI_USAGE.md

## Tool Used

- Tool/model: ChatGPT (GPT-5.6 Sol)
- Purpose: AI-assisted extraction/cleaning, explanation of errors, and debugging of regex/data-cleaning logic.
- Data status: The Lab 3 files are synthetic and contain no real PHI/PII.

## How I Documented AI-assisted Cleaning

For each AI-assisted cleaning step, I kept the input prompt, the input supplied, the output returned, changes I accepted or rejected, and any records I manually verified after the AI response.

The AI output was treated as a second parsing approach, not as ground truth.
I compared it against the regex output and the original raw records.

---

## Prompt 1 — Clinical CSV Extraction

**Goal:** produce an AI-assisted table comparable to the regex output.

**Prompt:**

> Clean the attached `messy_samples.csv` into a structured CSV. Preserve the raw 
> fields and add standardized fields. Normalize sample IDs to `S####`; dates to 
> `YYYY-MM-DD`; sex to `Male`, `Female`, or `Unknown`; and enrollment sites to 
> `Site A`, `Site B`, or `Site C`. Normalize glucose to mg/dL. For rows labeled 
> mmol/L, convert using 1 mmol/L = 18.0182 mg/dL. Strip a trailing `*` from the 
> numeric value but preserve it in a separate `glucose_flag` column. Do not 
> silently drop missing values. If a date is ambiguous from the characters alone, 
> leave the standardized date blank and set a status explaining the ambiguity 
> rather than guessing. Return only a CSV-compatible table.

**What I checked manually:**
- lowercase/hyphenated sample IDs such as `s-0003`;
- blank/`U`/`unknown` sex values;
- `SITE-A`, `site_a`, `siteB`, and double-spaced `Site  C`;
- starred glucose values such as `241.2*`;
- dot-formatted two-digit-year dates.

**Decision:** I accepted the conservative handling of ambiguous
dot-formatted dates. I did not allow the model to fill them from patient age or
other invented context.

---

## Prompt 2 — FASTA Header Extraction

**Prompt:**

> Parse every record in the attached `messy_sequences.fasta`. Return a table with
> `record_id_raw`, a normalized `record_id`, `organism`, `gene`,
> `declared_length_bp`, `observed_length_bp`, `length_check`, `note`,
> `sequence`, and `header_raw`. Normalize `Homo_sapiens`, `Homo sapiens`,
> `H.sapiens`, and `Hsapiens` to `Homo sapiens`. Recognize `gene` and `target`
> as equivalent header keys. Recognize `len`, `length`, and an unlabeled
> `<number> bp` token as possible declared lengths. Do not invent a declared
> length when the header does not contain one. Compute observed length from the
> sequence and flag declared/observed mismatches.

**What I checked manually:**
- `sample-003`, where the header says 150 bp but the sequence is 157 bp;
- `sample005`, where the header says 130 bp but the sequence is 144 bp;
- `seq6|Hsapiens|EGFR`, which has unlabeled positional fields;
- `Sample_007`, which contains a note but no declared length;
- `sample-8`, where `len:NA` should remain missing.

---

## Prompt 3 — Date Parsing Error Explanation

**Prompt:**

> My Python cleaning script raises a `ValueError` when I try to parse
> `05-Dec-1968` using one date format. Explain why this happens and identify the
> smallest conceptual fix. Do not rewrite the whole script. I need to support
> `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY`, and `MM.DD.YY`.

**What I learned / changed:**
I changed the parser to identify a format with a regex pattern first and then call `datetime.strptime()` with the matching format. This avoided forcing every date through one format.

---

## Prompt 4 — Diagnose an ID-normalization Bug

**Prompt:**

> The regex `^S\d{4}$` works for `S0001` but not for `s-0003`. Explain why and
> suggest a normalization rule that extracts the numeric suffix without changing
> the numeric identity of the sample. Please show only the relevant regex and one
> short Python example.

**What I changed:**
I used the trailing numeric portion as the stable identifier and formatted it as
`S####`. I retained `sample_id_raw` so the original value was never lost.

---

## Prompt 5 — FASTA Parsing Miss Explanation

**Prompt:**

> My FASTA parser correctly reads
> `sample_001|organism=Homo_sapiens|gene=BRCA1|len=120` but misses the gene in
> `sample005 Homo sapiens; TP53; 130 bp` and in `seq6|Hsapiens|EGFR`.
> Explain why a key-value-only regex fails on these headers. Suggest a narrow
> fallback that does not invent fields that are absent.

**What I changed:**
I kept key-value extraction as the first rule and added a fallback search for
the known gene tokens present in this synthetic dataset. For lengths, I added a
fallback for an explicit `<number> bp` token. I did not infer missing declared
lengths from sequence length.

---

## Prompt 6 — Checking a Questionable Unit Conversion

**Prompt:**

> A raw record contains glucose `159.9` with unit `mmol/L`. Multiplying by
> 18.0182 gives about 2881.1 mg/dL, which is implausibly high. Is the conversion
> arithmetic correct? Explain the difference between mathematically converting
> the labeled unit and changing the source unit because the result looks
> implausible. Do not recommend silently rewriting the original unit.

**What I accepted / rejected:**
The conversion formula was retained because it follows the recorded unit. I
added a `glucose_qc` review flag for implausible converted values. I rejected
any suggestion to silently relabel the source as mg/dL because that would alter
the data without evidence.

---

## Prompt 7 — Investigating Regex/AI Disagreement

**Prompt:**

> The regex parser converts `06.07.96` to `1996-06-07`, while the AI-assisted
> output marks it ambiguous because both 06 and 07 could be month or day.
> Explain what assumption the regex parser is making and what evidence would be
> needed to resolve the date safely. Do not choose a date for me.

**How I used the response:**
I documented the disagreement rather than forcing both outputs to match. The
regex result reflects a dataset-wide `MM.DD.YY` rule; the AI output reflects a
record-level "do not guess" rule.
