
"""Lab 3 regex-based cleaning for messy clinical CSV and FASTA data."""

from pathlib import Path
from datetime import datetime
import argparse
import re
import pandas as pd
import numpy as np


def norm_sample_id(x):
    s = x.strip()
    m = re.search(r"(\d+)$", s)
    return f"S{int(m.group(1)):04d}" if m else s.upper()


def parse_dob(x):
    s = x.strip()
    formats = [
        (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),
        (r"^\d{2}/\d{2}/\d{4}$", "%m/%d/%Y"),
        (r"^\d{2}-[A-Za-z]{3}-\d{4}$", "%d-%b-%Y"),
        (r"^\d{2}\.\d{2}\.\d{2}$", "%m.%d.%y"),
    ]
    for pattern, fmt in formats:
        if re.match(pattern, s):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d"), "parsed_by_rule"
            except ValueError:
                return "", "invalid_date"
    return "", "unparsed"


def norm_sex(s):
    x = s.strip().lower()
    if x in {"m", "male"}:
        return "Male"
    if x in {"f", "female"}:
        return "Female"
    return "Unknown"


def norm_site(s):
    x = re.sub(r"[\s_-]+", "", s.strip().lower())
    return {"sitea": "Site A", "siteb": "Site B", "sitec": "Site C"}.get(x, s.strip())


def clean_glucose(value, unit):
    raw_value = value.strip()
    flag = "*" if raw_value.endswith("*") else ""
    numeric_text = raw_value.rstrip("*").strip()

    if numeric_text.upper() in {"", "NA", "N/A"}:
        return np.nan, flag, "missing"

    try:
        numeric = float(numeric_text)
    except ValueError:
        return np.nan, flag, "unparsed_value"

    unit_norm = unit.strip().lower()
    if unit_norm == "mmol/l":
        mg_dl = numeric * 18.0182
    elif unit_norm == "mg/dl":
        mg_dl = numeric
    else:
        return np.nan, flag, "unknown_unit"

    qc = "review_unit_or_value" if mg_dl < 20 or mg_dl > 600 else "ok"
    return round(mg_dl, 1), flag, qc


def clean_samples(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = []
    for _, r in df.iterrows():
        dob, dob_status = parse_dob(r["dob"])
        glucose, glucose_flag, glucose_qc = clean_glucose(
            r["glucose_value"], r["glucose_unit"]
        )
        rows.append(
            {
                "sample_id_raw": r["sample_id"],
                "sample_id": norm_sample_id(r["sample_id"]),
                "patient_name": r["patient_name"].title(),
                "dob_raw": r["dob"],
                "dob": dob,
                "dob_parse_status": dob_status,
                "sex_raw": r["sex"],
                "sex": norm_sex(r["sex"]),
                "enrollment_site_raw": r["enrollment_site"],
                "enrollment_site": norm_site(r["enrollment_site"]),
                "glucose_value_raw": r["glucose_value"],
                "glucose_unit_raw": r["glucose_unit"],
                "glucose_mg_dl": glucose,
                "glucose_flag": glucose_flag,
                "glucose_qc": glucose_qc,
                "notes": r["notes"],
            }
        )
    return pd.DataFrame(rows)


def read_fasta(path):
    records = []
    header = None
    sequence_parts = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(sequence_parts)))
                header = line[1:].strip()
                sequence_parts = []
            else:
                sequence_parts.append(re.sub(r"\s+", "", line).upper())
    if header is not None:
        records.append((header, "".join(sequence_parts)))
    return records


def normalize_fasta_id(raw_id):
    match = re.match(r"(?i)^sample[_-]?(\d+)$", raw_id.strip())
    if match:
        return f"sample_{int(match.group(1)):03d}"
    return raw_id.strip().lower()


def parse_fasta_record(header, sequence):
    raw_id = re.split(r"[|;\s]+", header.strip(), maxsplit=1)[0]
    record_id = normalize_fasta_id(raw_id)

    organism = ""
    match = re.search(
        r"(?i)(?:organism|species)\s*[:=]\s*([^|;]+?)"
        r"(?=(?:\s+(?:gene|target|len|length|note)\s*[:=])|[|;]|$)",
        header,
    )
    if match:
        organism = match.group(1).strip()
    else:
        for alias in ["Homo_sapiens", "Homo sapiens", "H.sapiens", "Hsapiens"]:
            if re.search(re.escape(alias), header, flags=re.I):
                organism = alias
                break

    compact_org = re.sub(r"[\s._]", "", organism.lower())
    organism_clean = (
        "Homo sapiens"
        if compact_org in {"homosapiens", "hsapiens"}
        else organism
    )

    gene = ""
    match = re.search(r"(?i)(?:gene|target)\s*[:=]\s*([A-Za-z0-9_-]+)", header)
    if match:
        gene = match.group(1).upper()
    else:
        match = re.search(r"\b(BRCA1|TP53|EGFR)\b", header, flags=re.I)
        if match:
            gene = match.group(1).upper()

    declared_length = None
    match = re.search(r"(?i)(?:len|length)\s*[:=]\s*(\d+)\s*(?:bp)?", header)
    if match:
        declared_length = int(match.group(1))
    else:
        match = re.search(r"(?<![:=])\b(\d+)\s*bp\b", header, flags=re.I)
        if match:
            declared_length = int(match.group(1))

    note = ""
    match = re.search(r"(?i)note\s*[:=]\s*([^|;]+)", header)
    if match:
        note = match.group(1).strip()

    observed_length = len(sequence)
    if declared_length is None:
        length_check = "not_reported"
    elif declared_length == observed_length:
        length_check = "match"
    else:
        length_check = "mismatch"

    return {
        "record_id_raw": raw_id,
        "record_id": record_id,
        "organism": organism_clean,
        "gene": gene,
        "declared_length_bp": declared_length,
        "observed_length_bp": observed_length,
        "length_check": length_check,
        "note": note,
        "sequence": sequence,
        "header_raw": header,
    }


def clean_fasta(path):
    return pd.DataFrame(
        [parse_fasta_record(header, sequence) for header, sequence in read_fasta(path)]
    )


def build_feature_table(cleaned_samples):
    # With one measured feature (glucose), the cleaned clinical table is already
    # one-row-per-sample. This function makes the feature/metadata roles explicit.
    return cleaned_samples[
        [
            "sample_id",
            "glucose_mg_dl",
            "patient_name",
            "dob",
            "sex",
            "enrollment_site",
            "notes",
            "glucose_flag",
            "glucose_qc",
        ]
    ].copy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True, help="C:/data/messy_samples.csv")
    parser.add_argument("--fasta", required=True, help="/data/messy_sequences.fasta")
    parser.add_argument("--outdir", default="outputs/regex", help="/outputs/regex")
    parser.add_argument(
        "--feature-output",
        default="outputs/samples_features_metadata.csv",
        help="Graduate samples x features x metadata output",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    Path(args.feature_output).parent.mkdir(parents=True, exist_ok=True)

    samples = clean_samples(args.samples)
    fasta = clean_fasta(args.fasta)
    feature_table = build_feature_table(samples)

    samples.to_csv(outdir / "cleaned_samples_regex.csv", index=False)
    fasta.to_csv(outdir / "cleaned_sequences_regex.csv", index=False)
    feature_table.to_csv(args.feature_output, index=False)

    print(f"Wrote {len(samples)} cleaned sample rows.")
    print(f"Wrote {len(fasta)} cleaned FASTA records.")
    print(f"Wrote graduate feature table with {len(feature_table)} rows.")


if __name__ == "__main__":
    main()
