
"""Compare regex and AI-assisted Lab 3 outputs."""

from pathlib import Path
import argparse
import pandas as pd


def differing_rows(left, right, key):
    common = [c for c in left.columns if c in right.columns and c != key]
    merged = left.merge(right, on=key, suffixes=("_regex", "_ai"), how="outer")
    diffs = []
    for col in common:
        a = merged[f"{col}_regex"].fillna("").astype(str)
        b = merged[f"{col}_ai"].fillna("").astype(str)
        mask = a != b
        if mask.any():
            for _, row in merged.loc[mask, [key, f"{col}_regex", f"{col}_ai"]].iterrows():
                diffs.append(
                    {
                        key: row[key],
                        "field": col,
                        "regex_value": row[f"{col}_regex"],
                        "ai_value": row[f"{col}_ai"],
                    }
                )
    return pd.DataFrame(diffs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--regex-samples", default="outputs/regex/cleaned_samples_regex.csv")
    p.add_argument("--ai-samples", default="outputs/ai/cleaned_samples_ai.csv")
    p.add_argument("--regex-fasta", default="outputs/regex/cleaned_sequences_regex.csv")
    p.add_argument("--ai-fasta", default="outputs/ai/cleaned_sequences_ai.csv")
    args = p.parse_args()

    rs = pd.read_csv(args.regex_samples, dtype=str, keep_default_na=False)
    ais = pd.read_csv(args.ai_samples, dtype=str, keep_default_na=False)
    rf = pd.read_csv(args.regex_fasta, dtype=str, keep_default_na=False)
    aif = pd.read_csv(args.ai_fasta, dtype=str, keep_default_na=False)

    sample_diffs = differing_rows(rs, ais, "sample_id")
    fasta_diffs = differing_rows(rf, aif, "record_id")

    print("Sample differences:")
    print(sample_diffs.to_string(index=False) if len(sample_diffs) else "None")
    print("\nFASTA differences:")
    print(fasta_diffs.to_string(index=False) if len(fasta_diffs) else "None")


if __name__ == "__main__":
    main()
