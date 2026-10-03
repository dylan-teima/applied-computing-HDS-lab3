# Lab 3: Parsing Messy Health and Genomic Data

This repository is a draft implementation of the **PUBH 6854 graduate requirements** for Lab 3. It cleans both provided datasets with a deterministic regex-based workflow, includes comparable AI-assisted reference outputs, compares the two approaches, identifies concrete failure modes, and creates a graduate **samples × features × metadata** table.

> **Important:** `AI_USAGE.md` is deliberately a **mock/reference** document. Before submitting, replace it with an accurate record of the AI tool/model, exact prompts, responses, and changes you actually used.

## Repository Contents

``` text
.
├── README.md
├── AI_USAGE.md
├── .gitignore
├── requirements.txt
├── clean_regex.py
├── compare_outputs.py
└── outputs/
    ├── regex/
    │   ├── cleaned_samples_regex.csv
    │   └── cleaned_sequences_regex.csv
    ├── ai/
    │   ├── cleaned_samples_ai.csv
    │   └── cleaned_sequences_ai.csv
    └── samples_features_metadata.csv
```

The raw course files are **not** included in this repository draft. Keep them locally (for example, under `data/raw/`) or provide their paths on the command line. This follows the course guidance not to commit duplicate raw data.

## Setup and Reproducible Run

Python 3 with pandas/numpy is sufficient.

``` bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the regex cleaner:

``` bash
python clean_regex.py \
  --samples data/raw/messy_samples.csv \
  --fasta data/raw/messy_sequences.fasta \
  --outdir outputs/regex \
  --feature-output outputs/samples_features_metadata.csv
```

Expected outputs:

- `outputs/regex/cleaned_samples_regex.csv` — 60 cleaned clinical records
- `outputs/regex/cleaned_sequences_regex.csv` — 8 parsed FASTA records
- `outputs/samples_features_metadata.csv` — 60-row graduate analytic table

After saving the AI-assisted outputs documented in `AI_USAGE.md`, compare them:

``` bash
python compare_outputs.py
```

## 1. Regex-Based Cleaning

### Clinical Samples

The regex workflow standardizes the following fields while retaining raw values for auditability:

- sample IDs such as `s-0003` → `S0003`;
- four DOB formats → ISO `YYYY-MM-DD`;
- `M`, `m`, `Male` → `Male`;
- `F`, `f`, `Female` → `Female`;
- blank, `U`, and `unknown` → `Unknown`;
- `SITE-A`, `site_a`, `Site A` → `Site A` (similarly for Sites B/C);
- `mg/dL`, `mg/dl`, `MG/DL` → numeric mg/dL;
- `mmol/L` → mg/dL using `1 mmol/L = 18.0182 mg/dL`;
- a trailing glucose `*` is stripped from the numeric feature but preserved in `glucose_flag`.

The raw file contains 18 slash dates, 18 day-month-name dates, 15 dot dates, and 9 ISO dates. The cleaned table contains 22 `Male`, 20 `Female`, and 18 `Unknown` values after sex standardization, and 23 Site A, 20 Site B, and 17 Site C records after site normalization.

Thirteen records are labeled `mmol/L`. Conversion by the recorded unit produces very high mg/dL values, so those rows are flagged `review_unit_or_value` rather than silently relabeled. The goal is to distinguish a mathematical conversion from an unsupported correction to the source data.

### FASTA Records

The FASTA parser supports pipe-, semicolon-, and space-delimited headers, multiple key names (`organism`/`species`, `gene`/`target`, `len`/`length`), and unlabeled gene/length tokens when they are explicit in the header. It standardizes human-organism aliases to `Homo sapiens`, computes observed sequence length, and keeps declared and observed lengths separate.

Two records contain a declared/observed length disagreement:

- `sample-003`: header reports **150 bp**, observed sequence is **157 bp**.
- `sample005`: header reports **130 bp**, observed sequence is **144 bp**.

These are retained as `length_check = mismatch`; the parser does not overwrite one value with the other.

## 2. AI-Assisted Cleaning

The reference AI outputs use the same target schema so that comparison is field-for-field. The clinical prompt is intentionally conservative about ambiguous dates: if a dot-formatted date has two fields that could both be a month (for example `06.07.96`), the AI reference output leaves the standardized date blank and records `ambiguous_MM_DD_vs_DD_MM` rather than guessing.

The FASTA AI prompt explicitly says not to invent a declared length. It extracts the semantic fields, computes observed length, and flags the same two metadata mismatches as the regex workflow.

See `AI_USAGE.md` for example prompts and for examples of how debugging or correction prompts should be documented. **That file must be edited to match your actual AI use before submission.**

## 3. Comparison of Regex and AI-Assisted Outputs

### Agreement

The two approaches agree on the cleaned clinical sample IDs, patient-name casing, sex categories, site categories, glucose values/units, glucose flags, notes, and QC flags for all 60 records. They also agree on all eight FASTA records after the target schema and "do not invent missing fields" rule are made explicit.

The agreement is strongest for fields where the allowed variants can be stated as a finite set. Sex and site cleaning are good examples: once the acceptable aliases are known, regex rules are transparent and deterministic.

### Disagreement

The reference AI output is more conservative than the regex script for seven dot-formatted dates:

- `S0011` — `07.09.61`
- `S0012` — `06.07.96`
- `S0014` — `09.12.58`
- `S0015` — `02.11.98`
- `S0031` — `11.11.95`
- `S0033` — `06.07.12`
- `S0039` — `04.12.80`

The regex parser uses a dataset-level rule that all dot dates are `MM.DD.YY` and therefore returns an ISO date for each record. The AI reference policy asks the model not to guess when both the first and second components are `<= 12`, so it records those rows as ambiguous.

This disagreement is useful rather than something to hide. The regex method is more reproducible once a format convention is confirmed, while the conservative AI method better communicates uncertainty when the convention has not been verified externally.

### Edge Cases and Effort

The AI approach was faster for obtaining an initial semantic interpretation of irregular FASTA headers because it could recognize that `target=BRCA1` and an unlabeled `EGFR` token represented the same conceptual field. The regex approach required explicit key rules and fallback patterns, but once those rules were tested it was easier to rerun consistently and audit.

For a real production dataset, I would use deterministic code as the primary cleaning pipeline and use AI for schema discovery, debugging, or review of unusual records. I would not allow AI to silently overwrite source values; ambiguous or clinically implausible records should be flagged for review.

## 4. Specific Failure Modes

### Failure Mode 1 — Ambiguous Two-Digit Dot Date

`S0012` contains DOB `06.07.96`. A regex that assumes `MM.DD.YY` converts this to `1996-06-07`, but the characters alone also permit `1996-07-06`. The regex result is therefore only as trustworthy as the dataset-wide format assumption. The conservative AI output preserves the ambiguity rather than treating the assumption as certain.

### Failure Mode 2 — Another Ambiguous Date that Looks Valid Either Way

`S0015` contains `02.11.98`. Both February 11 and November 2 are valid calendar dates. A parser can successfully produce a date while still being semantically wrong. This is an important failure mode because no parsing exception is raised.

### Failure Mode 3 — FASTA Header Metadata Disagrees with the Sequence

`sample-003` declares `length=150bp`, but the observed sequence has 157 bases. A parser that trusts the header alone would return a clean-looking but incorrect length. Computing observed length separately reveals the conflict.

### Failure Mode 4 — Positional FASTA Tokens

`seq6|Hsapiens|EGFR` contains no `organism=` or `gene=` labels. A strict key-value regex misses both semantic fields. The implemented parser therefore uses narrow fallbacks for the known organism aliases and gene symbols while retaining the raw header so the inference remains auditable.

## Graduate Addendum: samples × features × metadata

`outputs/samples_features_metadata.csv` is a one-row-per-sample analytic table. Because this clinical file contains one measured feature rather than a long gene-expression matrix, no long-to-wide pivot is necessary. The roles are:

- **sample identifier:** `sample_id`
- **feature:** `glucose_mg_dl`
- **metadata:** `patient_name`, `dob`, `sex`, `enrollment_site`, `notes`
- **quality/provenance metadata:** `glucose_flag`, `glucose_qc`

This follows Week 5's principle of one sample per row, feature columns for measurements, and sample-level metadata alongside those features.
