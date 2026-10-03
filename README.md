
# Lab 3: Parsing Messy Health and Genomic Data

This repository contains the scripts to clean both provided datasets with a regex-based workflow, includes comparable AI-assisted reference outputs, compares the two approaches, identifies failure modes, and creates a graduate **samples × features × metadata** table.

## Repository Contents

``` text
applied-computing-HDS-lab3/
├── README.md
├── AI_USAGE.md
├── .gitignore
├── environment.yml
│
├── scripts/
│   ├── clean_regex.py
│   └── compare_outputs.py
│
├── outputs/
│   ├── regex/
│   │   ├── cleaned_samples_regex.csv
│   │   └── cleaned_sequences_regex.csv
│   ├── ai/
│   │   ├── cleaned_samples_ai.csv
│   │   └── cleaned_sequences_ai.csv
│   └── samples_features_metadata.csv
│
└── data/
    ├── messy_samples.csv
    └── messy_sequences.fasta
```

The source files are **not** included in this submission. Keep them locally (for example, under `data`) or provide their paths on the command line.

## Setup and Reproducible Run

Python 3 with pandas/numpy is sufficient to run the included scripts.

**Note:** You must be currently in the folder `applied-computing-HDS-lab3` in your terminal window to run the regex cleaner (or copy and paste the correct file path to `clean_regex.py`). Enter the following to run the regex cleaner script:

``` bash
python scripts/clean_regex.py \
  --samples data/messy_samples.csv \
  --fasta data/messy_sequences.fasta \
  --outdir outputs/regex \
  --feature-output outputs/samples_features_metadata.csv
```

Expected outputs:

- `outputs/regex/cleaned_samples_regex.csv` — 60 cleaned clinical records
- `outputs/regex/cleaned_sequences_regex.csv` — 8 parsed FASTA records
- `outputs/samples_features_metadata.csv` — 60-row graduate analytic table

After saving the AI-assisted outputs documented in `AI_USAGE.md`, compare them by running `compare_ouputs.py` (copy and paste file path if not currently in `applied-computing-HDS-lab3`):

``` bash
python scripts/compare_outputs.py
```

## 1. Regex-Based Cleaning

### Clinical Samples

The regex workflow standardizes the following fields while retaining raw values for auditability:

- Sample IDs such as `s-0003` → `S0003`
- Four DOB formats → `YYYY-MM-DD`
- `M`, `m`, `Male` → `Male`
- `F`, `f`, `Female` → `Female`
- Flank, `U`, and `unknown` → `Unknown`
- `SITE-A`, `site_a`, `Site A` → `Site A` (similarly for Sites B/C);
- `mg/dL`, `mg/dl`, `MG/DL` → numeric mg/dL;
- `mmol/L` → mg/dL using `1 mmol/L = 18.0182 mg/dL`
- Trailing `*` stripped from glucose values, keeping the numeric feature and moving `*` to `glucose_flag`.

The raw file contains 18 slash dates, 18 day-month-name dates, 15 dot dates, and 9 "ISO" (`YYYY-MM-DD`) dates. The cleaned table contains 22 `Male`, 20 `Female`, and 18 `Unknown` values after sex standardization, and 23 Site A, 20 Site B, and 17 Site C records after site normalization.

Thirteen records are labeled `mmol/L`. Conversion by the recorded unit produces very high mg/dL values, so those rows are flagged `review_unit_or_value` rather than being silently relabeled.

### FASTA Records

The FASTA parser supports pipe-, semicolon-, and space-delimited headers, multiple key names (`organism`/`species`, `gene`/`target`, `len`/`length`), and unlabeled gene/length tokens when they are explicit in the header. It standardizes human-organism aliases to `Homo sapiens`, computes observed sequence length, and maintains separation between declared and observed lengths.

Two records contain a disagreement between declared and observed length:

- `sample-003`: header reports **150 bp**, observed sequence is **157 bp**.
- `sample005`: header reports **130 bp**, observed sequence is **144 bp**.

These are retained as `length_check = mismatch` and the parser does not overwrite one value with the other.

## 2. AI-Assisted Cleaning

The reference AI outputs use the same target schema so that comparison is exact, field-for-field. The clinical prompt is intentionally conservative about dates that are ambiguous. If a dot-formatted date has two fields that could be either a month or a day (for example `06.07.96`), the AI reference output leaves the standardized date blank and records `ambiguous_MM_DD_vs_DD_MM` instead of guessing.

The FASTA AI prompt explicitly says not to invent a declared length. It extracts the fields, computes observed length, and flags the same two metadata mismatches as the regex workflow.

See `AI_USAGE.md` for exact prompts and for how debugging/correction prompts were documented. 

## 3. Comparison of Regex and AI-Assisted Outputs

### Agreement

The two approaches agree on the cleaned clinical sample IDs, patient-name casing, sex categories, site categories, glucose values/units, glucose flags, notes, and QC flags for all 60 records. They also agree on all eight FASTA records after the target schema and "do not invent missing fields" rule are made explicit.

The agreement is strongest for fields where the allowed variants can be stated as a finite set. Sex and site cleaning are examples, where making the acceptable aliases known makes regex rules transparent.

### Disagreement

The reference AI output is more conservative than the regex script for seven samples with dot-formatted dates:

- `S0011` — `07.09.61`
- `S0012` — `06.07.96`
- `S0014` — `09.12.58`
- `S0015` — `02.11.98`
- `S0031` — `11.11.95`
- `S0033` — `06.07.12`
- `S0039` — `04.12.80`

The regex parser uses a rule that all dot dates are formatted, `MM.DD.YY`, and therefore returns an ISO date for each record. The AI model was asked not to guess when both the first and second components are `<= 12`, so it records those rows as ambiguous.

The regex method is more reproducible if a format convention can be confirmed, while the AI method better communicates uncertainty when the convention has not been established.

### Edge Cases and Effort

The AI approach was faster for obtaining an initial semantic interpretation of irregular FASTA headers because it could recognize that `target=BRCA1` and an unlabeled `EGFR` gene represented the same conceptual field. The regex approach required explicit key rules and fallback patterns, but once those rules were tested it was easier to rerun consistently and audit.

For a real production dataset, I would use deterministic code as the primary cleaning method and use AI for schema discovery, debugging, or review of abnormal records. I would stay away from allowing AI to overwrite source values, but instead flag ambiguous or clinically implausible records for review.

## 4. Specific Failure Modes

### Failure Mode 1 — Ambiguous Two-Digit Dot Date

`S0012` contains DOB `06.07.96`. A regex that assumes `MM.DD.YY` converts this to `1996-06-07`, but the characters alone also permit `1996-07-06`. The regex result is therefore only as trustworthy as the dataset-wide format assumption. The AI output maintains the ambiguity rather than treating the assumption as certain.

### Failure Mode 2 — Another Ambiguous Date that Looks Valid Either Way

`S0015` contains `02.11.98`. Both February 11 and November 2 are valid calendar dates. A parser can successfully produce a date while still being semantically wrong. This is an important failure mode because no parsing exception is raised.

### Failure Mode 3 — FASTA Header Metadata Disagrees with the Sequence

`sample-003` declares `length=150bp`, but the observed sequence has 157 bases. A parser that trusts the header alone would return a clean-looking but incorrect length. Computing observed length separately reveals the conflict.

### Failure Mode 4 — Positional FASTA Tokens

`seq6|Hsapiens|EGFR` contains no `organism=` or `gene=` labels. A strict key-value regex misses both fields. The implemented parser therefore uses fallbacks for the known organism aliases and gene symbols while retaining the raw header so the inference can still be audited.

## Graduate Addendum: samples × features × metadata

`outputs/samples_features_metadata.csv` is a one-row-per-sample analytic table. Because this clinical file contains one measured feature rather than a long gene-expression matrix, no long-to-wide pivot is necessary. The roles are:

- **sample identifier:** `sample_id`
- **feature:** `glucose_mg_dl`
- **metadata:** `patient_name`, `dob`, `sex`, `enrollment_site`, `notes`
- **quality/provenance metadata:** `glucose_flag`, `glucose_qc`

This follows thr principle of one sample per row, feature columns for measurements, and sample-level metadata alongside those features.

### Analytic Readiness

The table is structurally ready for downstream analysis since sample IDs, categories, date strings, and the feature column use consistent formatting, and blank/ambiguous values are documented rather than being dropped. However, it is not yet clinically modeling-ready since the 13 records originally labeled `mmol/L` produce implausibly high values after literal conversion. The source unit/value relationship should be verified before those observations are used. Ambiguous conventions for DOB formatting should also be confirmed from source documentation rather than resolved by appearance alone.

