# AI_USAGE.md

## Tool Used

- Tool/model: ChatGPT (GPT-5.6 Sol)
- Purpose: AI-assisted extraction/cleaning, explanation of errors, and debugging of regex/data-cleaning logic.

## How I Documented AI-assisted Cleaning

For each AI-assisted cleaning step, I kept the input prompt, the input supplied, the output returned, changes I accepted or rejected, and any records I manually verified after the AI response.

I compared AI-assisted cleaning against the regex output and the original raw records.

---

## Prompt 1 — Clinical CSV Extraction

**Goal:** produce an AI-assisted table comparable to the regex output.

**Prompt:**

Clean the attached `messy_samples.csv` into a structured CSV. Preserve the raw fields and add standardized fields. Normalize sample IDs to `S####`; dates to `YYYY-MM-DD`; sex to `Male`, `Female`, or `Unknown`; and enrollment sites to `Site A`, `Site B`, or `Site C`. Normalize glucose to mg/dL. For rows labeled mmol/L, convert using 1 mmol/L = 18.0182 mg/dL. Strip a trailing `*` from the numeric value but preserve it in a separate `glucose_flag` column. Do not silently drop missing values. If a date is ambiguous from the characters alone, leave the standardized date blank and set a status explaining the ambiguity rather than guessing. Return only a CSV-compatible table.

**What I checked manually:**
- lowercase/hyphenated sample IDs such as `s-0003`
- blank/`U`/`unknown` sex values
- `SITE-A`, `site_a`, `siteB`, and double-spaced `Site  C`
- starred glucose values such as `241.2*`
- dot-formatted two-digit-year dates

**Decision:** I accepted the conservative handling of ambiguous
dot-formatted dates. I didn't allow the model to fill them from patient age.

---

## Prompt 2 — FASTA Header Extraction

**Prompt:**

Parse every record in the attached `messy_sequences.fasta`. Return a table with `record_id_raw`, a normalized `record_id`, `organism`, `gene`, `declared_length_bp`, `observed_length_bp`, `length_check`, `note`, `sequence`, and `header_raw`. Normalize `Homo_sapiens`, `Homo sapiens`, `H.sapiens`, and `Hsapiens` to `Homo sapiens`. Recognize `gene` and `target` as equivalent header keys. Recognize `len`, `length`, and an unlabeled `<number> bp` token as possible declared lengths. Do not invent a declared length when the header does not contain one. Compute observed length from the sequence and flag declared/observed mismatches.

**What I checked manually:**
- `sample-003`, where the header says 150 bp but the sequence is 157 bp
- `sample005`, where the header says 130 bp but the sequence is 144 bp
- `seq6|Hsapiens|EGFR`, which has unlabeled position fields
- `Sample_007` contains a note but no length
- `sample-8`, where `len:NA` should remain missing

---

## Prompt 3 — Date Parsing Error Explanation

**Prompt:**

My Python cleaning script raises a `ValueError` when I try to parse dates such as, `05-Dec-1968`, using one date format. Explain why this error may have happened and provide a conceptual fix. Don't rewrite the whole script. The following date formats should be supported: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY`, and `MM.DD.YY`.

**What I Changed:**
I changed the parser to identify a format with a regex pattern first and then call `datetime.strptime()` with the matching format. This avoided forcing every date through a 'one size fits all' format.

---

## Prompt 4 — Diagnose an ID-normalization Bug

**Prompt:**

The regex `^S\d{4}$` works for `S0001` but not for `s-0003`. Explain why and suggest a rule that extracts the numeric suffix without changing the identity of the sample. Provide only the relevant regex and a short example in Python.

**What I changed:**
I used the trailing numeric portion as the stable identifier and formatted it as `S####`. I retained `sample_id_raw` so the original value was never lost.

---

## Prompt 5 — FASTA Parsing Miss Explanation

**Prompt:**

My attempt to parse a FASTA file correctly reads `sample_001|organism=Homo_sapiens|gene=BRCA1|len=120` but incorrectly parses the gene in headers such as `sample005 Homo sapiens; TP53; 130 bp` and in `seq6|Hsapiens|EGFR`. Explain why a key-value-only regex fails on these headers. Suggest a potential fix that does not invent new fields.

**What I Changed:**
I kept key-value extraction as the first rule and added a fallback search for the known gene entries present in this dataset. For lengths, I added a
fallback for an explicit `<number> bp` token. I did not infer missing declared lengths from sequence length.

---

## Prompt 6 — Checking a Questionable Unit Conversion

**Prompt:**

A raw record contains glucose `159.9` with unit `mmol/L`. Multiplying by 18.0182 gives about 2881.1 mg/dL, which is implausibly high. Explain the difference between mathematically converting the labeled unit and changing the source unit because the result appears to be incorrect.

**What I Changed:**
The conversion formula was retained because it follows the recorded unit. I added a `glucose_qc` review flag for implausible converted values. I rejected any suggestion to silently relabel the source as mg/dL because that would alter the data without evidence.

---

## Prompt 7 — Investigating Regex/AI Disagreement

**Prompt:**

My regex parser converts `06.07.96` to `1996-06-07`, while the AI-assisted output marks it as ambiguous because both 06 and 07 could be month or day depending on the intended date formatting convention. Explain what assumption the regex parser is making and what evidence would be needed to resolve the date safely.

**How I used the response:**
Rather than forcing the outputs to match, I documented the disagreement. The regex result assumes a format of `MM.DD.YY` for the whole dataset, while the AI output doesn't assume a format for each given record.

---
