"""
This script checks an Excel file for duplicate student entries (based on student number and/or email)
and optionally removes them.

Workflow:
1. Reads the Excel file containing all student data.
2. Detects duplicates by either student number or email (case-insensitive for emails, because of 's').
   - Ignores missing values such as NaN, N/A, empty strings, or None.
3. Shows you which entries are duplicates.
4. Asks if you want to delete duplicates (keeps the first occurrence).
5. If you say yes ('y'), it creates:
   - a cleaned version of the file with "_no_duplicates.xlsx"
   - a file listing removed duplicates with "_removed_duplicates.xlsx"
"""

import os
import pandas as pd

###########################################
# ADJUST THESE PARAMETERS

# Path to your Excel file (original student list)
FILE = "students_list.xlsx"

# Column name of the student number (exactly as in Excel)
SN_COL = "DTU Student Number (with 's' in front)"

# Column name of the email (exactly as in Excel)
EMAIL_COL = "E-mail"

# END OF ADJUSTING
###########################################


def normalize_cols(df, sn_col, em_col):
    """Standardize student number and email for reliable duplicate detection."""
    df = df.copy()
    df[sn_col] = df[sn_col].astype(str).str.strip().str.lower()
    df[em_col] = df[em_col].astype(str).str.strip().str.lower()

    # Replace "nan", "none", "n/a", "" with actual NaN
    df[sn_col].replace(["nan", "none", "n/a", "na", ""], pd.NA, inplace=True)
    df[em_col].replace(["nan", "none", "n/a", "na", ""], pd.NA, inplace=True)
    return df


def find_duplicates(df, sn_col, em_col):
    """Find duplicate rows by student number or email, ignoring missing values."""
    # Only mark duplicates where the field is not null
    dup_sn = df[sn_col].notna() & df.duplicated(subset=[sn_col], keep="first")
    dup_em = df[em_col].notna() & df.duplicated(subset=[em_col], keep="first")
    dup_any = dup_sn | dup_em
    return df[dup_any], dup_sn, dup_em


def main():
    # Check if file exists
    if not os.path.isfile(FILE):
        print(f"ERROR: File not found: {FILE}")
        return

    try:
        df = pd.read_excel(FILE, header=0)
    except Exception as e:
        print(f"ERROR reading Excel: {e}")
        return

    # Ensure required columns exist
    for col in [SN_COL, EMAIL_COL]:
        if col not in df.columns:
            print(f"ERROR: Column '{col}' not found in the Excel file.")
            print("Available columns:", list(df.columns))
            return

    # Normalize
    df_norm = normalize_cols(df, SN_COL, EMAIL_COL)

    # Find duplicates (ignoring blanks)
    dup_df, dup_sn_mask, dup_em_mask = find_duplicates(df_norm, SN_COL, EMAIL_COL)
    total_dupes = len(dup_df)

    print("=" * 60)
    print(f"🔍 Found {total_dupes} duplicate entries (by student number and/or email).")
    print("=" * 60)

    if total_dupes == 0:
        print("✅ No duplicates found. Nothing to clean.")
        return

    print("\nPreview of duplicates (first 20 shown):")
    print(dup_df.head(20)[[SN_COL, EMAIL_COL]])

    # Show top repeated keys (non-null only)
    sn_counts = df_norm[SN_COL].dropna().value_counts()
    em_counts = df_norm[EMAIL_COL].dropna().value_counts()

    print("\nMost common duplicated student numbers:")
    print(sn_counts[sn_counts > 1].head(10))

    print("\nMost common duplicated emails:")
    print(em_counts[em_counts > 1].head(10))

    # Ask user
    choice = input("\n🗑️ Remove duplicates (keep first occurrence) and save cleaned file? [y/n]: ").strip().lower()

    if choice != "y":
        print("No changes made. Exiting.")
        return

    # Drop duplicates — only among rows that have a real (non-missing) key
    cleaned = df_norm.copy()

    # 1) Deduplicate by EMAIL (ignore missing emails)
    em_mask = cleaned[EMAIL_COL].notna()
    kept_em = cleaned.loc[em_mask].drop_duplicates(subset=[EMAIL_COL], keep="first")
    rest_em = cleaned.loc[~em_mask]  # rows with missing email -> keep all
    cleaned = pd.concat([kept_em, rest_em]).sort_index()

    # 2) Deduplicate by STUDENT NUMBER (ignore missing SN)
    sn_mask = cleaned[SN_COL].notna()
    kept_sn = cleaned.loc[sn_mask].drop_duplicates(subset=[SN_COL], keep="first")
    rest_sn = cleaned.loc[~sn_mask]  # rows with missing SN -> keep all
    cleaned = pd.concat([kept_sn, rest_sn]).sort_index()

    # Determine which rows were removed
    removed = pd.concat([df_norm, cleaned]).drop_duplicates(keep=False)

    # Output filenames
    base, ext = os.path.splitext(FILE)
    out_clean = f"{base}_no_duplicates.xlsx"
    out_removed = f"{base}_removed_duplicates.xlsx"

    # Save using original values (not normalized display)
    cleaned_final = df.loc[cleaned.index]
    removed_final = df.loc[removed.index]

    cleaned_final.to_excel(out_clean, index=False)
    removed_final.to_excel(out_removed, index=False)

    print("\nYayy! Duplicates removed successfully! 🥳")
    print(f"📁 Cleaned file saved as: {out_clean}")
    print(f"🗑️ Removed duplicates saved as: {out_removed}")
    print("=" * 60)

if __name__ == "__main__":
    main()
