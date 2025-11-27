"""
This is v2 of the script that creates the IW groups.

This is the approach:
- Randomly create group distributions for a specified amount of time
while using multiprocessing => therefore making use of the av. performance as much as possible
- Track the randomly created group w the best diversity score
- After the specified amount of time has passed, use a greedy algorithm to make some
random swaps in the group w the best diversity to see if the score can be improved upon until
no better scores are achieved => this will be the result

Background:
- The problem of creating the most diverse groups is a problem that is most similar to
the problem of set packing (https://en.wikipedia.org/wiki/Set_packing) which is a NP-complete problem,
so therefore it is safe to assume that there is no efficient algorithm that achieves the best
solution for creating the most diverse groups
- The best approach therefore is to create randomly assigned groups for as long as feasible and then
try to improve iteratively on the best found group
- Note that the longer the script is allowed the better the diversity score MAY get. Since we are working
with randomness here, this means only the probability of getting more diverse groups increases.
The script is therefore all about trying to increase this probability while staying within a still 
feasible time frame (i.e. we cannot wait 100 years 10 days and 12 to the power of 50 DTU introweeks for the script to finish
even though this would most likely come pretty close to finding the ideal distribution that has the max diversity)
"""

import os
import sys
import time

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

# do a safe import
# the reason for doing this is that for example openpyxl will otherwise
# only be checked for once it is needed, which is at the end of the script
# we however want to check if it is existent at the start to save time
try:
    import openpyxl  # not directly needed but needed by pandas so check if installed at start
    import pandas as pd
    import numpy as np
except ImportError as exc:
    print("ERROR: Please install the packages pandas, openpyxl, numpy")
    print("Most likely this is done with 'pip install pandas openpyxl numpy'")
    raise exc

###########################################
# ADJUST THESE PARAMETERS
# INPUT FILE PATH (absolute or relative path!)
FILE = "students_list_no_duplicates.xlsx"

# Target size of a group (number of students)
TARGET_GROUP_SIZE = 20

# Output directory (output files will be saved in this dir)
# absolute or relative path (dir MUST EXIST!)
# Program also automatically creates a 'master' and 'exchange' subdirectory
# for the masters and exchange groups inside this 'groups' dir 
OUTPUT_P = "groups/"

# Stop the script if required fields are missing (student number or email)
# Recommended: keep True, fix issues, then rerun.
MISSING_QUIT = False

# Setting on how to handle duplicates
# the best is to run this w true for the first time and then fix everything
# and only set this to false if you know that the flagged duplicates are no duplicates
DUPLICATE_QUIT = True

# Config that tells the script how the columns are named
# change this to match the excel file column names
# e.g. "name_col" : "name" tells the script to find the name value
# in the column called "name". If you have a different name for this
# column then change "name" to the respective name
CONFIG = {
    "fname_col": "First name",
    "lname_col": "Last name",
    "sn_col": "DTU Student Number (with 's' in front)",
    "email_col": "E-mail",
    "studyline": "Study programme",
    "gender": "To which Gender do you identify the most?",
    "country": "Home Country",
}

# Mapping from prefix to which participant categories should be included
# change this to match the excel file information
PREFIX_FILTERS = {
    "M": ["MSc Student - Full Week Option (for students enrolled in a full Master's Programme at DTU)"],
    "E": ["Exchange Student - Full Week (for students enrolled as guests at DTU for one or two semesters)"],
}

# How long the script should try to create random groups (in minutes)
RUNTIME = 0.1  # Minutes

# END OF ADJUSTING
###########################################


class Student:
    """
    Class representing a student
    Taken from the original script
    """

    def __init__(self, row_id, study, gender, nat):
        self.row_id, self.study, self.gender, self.nationality = (
            row_id,
            study,
            gender,
            nat,
        )

    def __str__(self):
        return f"{self.row_id}, {self.study}, {self.gender}, {self.nationality}"

    def get_orig_data(self, df):
        """
        Helper function to get the original data
        from the dataset based upon the index
        Handy if there is more data than what is saved here in this class
        """
        # Positional access by stable key -> no label/ordering ambiguity
        return df.iloc[self.row_id]

def check_missing_required(df, config, quit_):
    """
    Flag missing/blank values in critical columns: student number and email.
    Treats NaN, empty strings, and 'n/a'/'na'/'none'/'nan' (any case) as missing.
    """
    sn_col = config["sn_col"]
    em_col = config["email_col"]

    # Normalize locally for robust detection (does not modify df)
    sn = df[sn_col].astype(str).str.strip()
    em = df[em_col].astype(str).str.strip().str.lower()

    missing_tokens = {"", "n/a", "na", "none", "nan"}

    sn_missing = sn.isna() | sn.str.lower().isin(missing_tokens)
    em_missing = em.isna() | em.str.lower().isin(missing_tokens)
    missing_any = sn_missing | em_missing

    if missing_any.any():
        if quit_:
            print("\n")
            print("#" * 20)
            print("😬 Well, this is awkward...")
            print("Some brave souls managed to enroll *without* a student number or email.")
            print("Truly inspiring. Unfortunately, Excel and I are not that chill.")
            print("The ")
            cols_to_show = [
                config.get("fname_col", None),
                config.get("lname_col", None),
                sn_col,
                em_col,
            ]
            cols_to_show = [c for c in cols_to_show if c and c in df.columns]
            print(df.loc[missing_any, cols_to_show])
            print("#" * 10)
            print("\n")
            print("🛑 I'm stopping here before things get worse.")
            print("Go fix the missing info, then come back when everyone remembers who they are.")
            print("Or go and set MISSING_QUIT = FALSE if you are feeling adventurous, but be ready to deal with the consenquences.")
            print("\n")
            sys.exit(1)
        else:
            print("\n")
            print("Oh, I see you set MISSING_QUIT = False... someone clearly trusts their Excel more than I do.")
            print("Fine, I'll keep going. But don't say I didn't warn you.")
            print("\n")


def check_duplicates(series, duplicate_type, quit_):
    """
    Checks for duplicates within a single column (Series).
    - Ignores missing-like values such as empty strings, 'N/A', 'None', 'nan'
    """
    # Normalize to strings and lowercase
    s = series.astype(str).str.strip().str.lower()

    # Define what counts as "missing" so we don’t treat those as duplicates
    missing_tokens = {"", "n/a", "na", "none", "nan"}
    mask = ~s.isin(missing_tokens)
    s_clean = s[mask]

    # Find duplicates (ignoring missing-like ones)
    dup_mask = s_clean.duplicated(keep=False)

    if dup_mask.any():
        print("\n")
        print("#" * 10)
        print("👯 Ah, duplicates. My favorite kind of identity crisis.")
        print(f"Found duplicates based on: {duplicate_type}")
        print("Behold the clones (values shown, missing-like entries ignored):")
        print(s_clean[dup_mask].sort_values().unique())
        print("#" * 10)
        if quit_:
            print("\n")
            print("🚫 Nope. Not doing this. Go sort your twins out before I continue.")
            print("Set DUPLICATE_QUIT = False if you enjoy living dangerously.")
            print("\n")
            sys.exit(0)
        else:
            print("\n")
            print("Oh, I see you set DUPLICATE_QUIT = False... finally, a risk-taker in data cleaning.")
            print("🤷 Fine, I'll keep going — but don't blame me if one student gets assigned to two groups.")
            print("\n")



def calc_num_groups(n_students: int, target_size: int) -> int:
    """
    Compute number of groups from target group size.
    If fractional part > 0.5 -> round up
    If fractional part < 0.5 -> round down
    If exactly 0.5 -> round up
    """
    if target_size <= 0:
        raise ValueError("TARGET_GROUP_SIZE must be positive")
    ratio = n_students / target_size
    base = int(ratio)  # floor
    frac = ratio - base
    if frac > 0.5:
        groups = base + 1
    elif frac < 0.5:
        groups = base
    else:  # exactly 0.5
        groups = base + 1
    return max(groups, 1)


def print_stats(category, df, config, n_groups):
    """
    Helper function to print statistics about a category
    Shows percentages with adaptive precision:
      - >= 1% -> one decimal (e.g., 3.4%)
      - <  1% -> two decimals (e.g., 0.44%)
    """

    def fmt_pct(frac):
        pct = frac * 100.0
        return f"{pct:.1f}%" if pct >= 1 else f"{pct:.2f}%"
    
    print(
        f"\n{category} information (type, amount (% of all), ideal avg. amount per group)"
    )
    col = df[config[category]]
    counts = col.value_counts()
    amount = len(col)

    for value in counts.index:
        cnt = counts[value]
        frac = cnt / amount if amount else 0.0
        pct_str = fmt_pct(frac)
        ideal_avg = cnt / n_groups if n_groups else 0.0
        ideal_avg = round(ideal_avg, 1)
        if ideal_avg < 1: # round the ideal avg to 1 if it is below 1
            ideal_avg = 1  
        print(f"{value} - {cnt} ({pct_str}) - {ideal_avg}")


def create_rand_group(students, n_groups):
    """
    Helper function to create randomized groups according to the
    specified amount of groups
    """
    # randomly shuffle (numpy is faster than the built-in random module)
    np.random.shuffle(students)
    groups = [[] for _ in range(n_groups)]

    # distribute the students
    # this approach is safer than the initial slicing approach
    # as it prevents assigning students to multiple groups
    for index, s in enumerate(students):
        groups[index % n_groups].append(s)
    return groups


def diversity_score(group):
    """
    Helper function to calculate the diversity score of a given group
    Taken and adapted from https://stackoverflow.com/a/73738016
    If 2 students in a group share the same trait (i.e. same studyline and/or
    same gender and/org same country) the diversity score is reduced, i.e.
    a "penalty" is introduced.
    That means that a group that is perfectly diverse would get a score of 0
    and all other groups a score of < 0
    """
    # initial score (and potential best score)
    score = 0
    for i, student_1 in enumerate(group):
        for student_2 in group[i + 1 :]:
            # remember that True = 1 and False = 0
            # the 3 diversity factors (these are set in the Student class)
            score -= student_1.study == student_2.study
            score -= student_1.gender == student_2.gender
            score -= student_1.nationality == student_2.nationality
    return score


def mp_wrapper(students, n_groups):
    """
    Helper function that is used for the multiprocessing
    It creates a random group and then returns the diversity score
    together with the group distribution itself

    The diversity score of a group split is the mean of the diversity
    scores of all groups in it
    """
    groups = create_rand_group(students, n_groups)
    mean_scores = [diversity_score(g) for g in groups]
    return [np.mean(mean_scores), groups, mean_scores]


def stirling_second_kind(n, k):
    """
    Helper function for calculating all possible combinations
    to give an idea how hard this problem is
    Generated by Chat
    """
    # Create a 2D array to store the values of S(n, k)
    S = [[0] * (k + 1) for _ in range(n + 1)]

    # Base cases
    S[0][0] = 1  # S(0, 0) = 1

    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            S[i][j] = j * S[i - 1][j] + S[i - 1][j - 1]

    return S[n][k]


def maybe_swap(group_1, group_2):
    """
    Helper function to see if a swap would increase diversity of the groups
    Taken and adapted from https://stackoverflow.com/a/73738016
    """
    diversity_1, diversity_2 = map(diversity_score, [group_1, group_2])
    old_sum = diversity_1 + diversity_2
    for _ in range(len(group_1)):  # do this for every student in group_1
        student_1 = group_1.pop(0)  # provisionally remove from group_1
        for _ in range(len(group_2)):
            student_2 = group_2.pop(0)  # provisionally remove from g_2
            group_1.append(student_2)  # provisionally swap students
            group_2.append(student_1)
            diversity_1, diversity_2 = map(diversity_score, [group_1, group_2])
            new_sum = diversity_1 + diversity_2
            if new_sum > old_sum:  # see what the new score is
                return True  # leave the swap intact and return if higher
            group_2.pop()  # else, remove student_1 from group_2 ...
            group_2.append(group_1.pop())  # and return student_2 to group_2
        group_1.append(student_1)  # return student_1 to group_1
    # no increase so leave w False
    return False


def greedy_assign(groups):
    """
    Helper function to do the greedy swapping
    Taken and adapted from https://stackoverflow.com/a/73738016

    This function is guaranteed to return because the diversity score
    is only permitted to increase (otherwise we might run into cycles),
    and the diversity score is capped at 0.
    """
    # first shuffle the list order
    # this only shuffles the order of the groups
    # and not actually the people inside the group!
    # this is needed so that the first group is not always the same!
    np.random.shuffle(groups)
    while True:
        has_swapped = False
        for i, group_1 in enumerate(groups):
            for group_2 in groups[i + 1 :]:
                has_swapped = maybe_swap(group_1, group_2) or has_swapped
        if not has_swapped:
            return groups
        
def fun_intro():
    intros = [
        "✨ Ah, IntroWeek time again. Let's form some *totally random* but *deeply scientific* groups 🧪.",
        "🌀 Welcome back, agent of chaos. Let's pretend we're in control of this randomness.",
        "🎭 Another day, another batch of innocent students about to be grouped against their will.",
        "🦄 Initializing group generator... because nothing says 'welcome to DTU' like statistical group generation.",
    ]
    print("\n" + np.random.choice(intros) + "\n")


def progressbar(it, prefix="", size=60, out=sys.stdout):
    """
    Progress bar for nicer UI, taken from https://stackoverflow.com/a/34482761
    """
    count = len(it)
    start = time.time()  # time estimate start

    def show(j):
        x = int(size * j / count)
        # time estimate calculation and string
        remaining = ((time.time() - start) / j) * (count - j)
        mins, sec = divmod(remaining, 60)  # limited to minutes
        time_str = f"{int(mins):02}:{sec:03.1f}"
        print(
            f"{prefix}[{u'█'*x}{('.'*(size-x))}] {j}/{count} Est wait {time_str}",
            end="\r",
            file=out,
            flush=True,
        )

    show(0.1)  # avoid div/0
    for i, item in enumerate(it):
        yield item
        show(i + 1)
    print("\n", flush=True, file=out)

def assert_student_consistency(df, groups, config):
    for g in groups:
        for s in g:
            r = s.get_orig_data(df)
            assert s.study == r[config["studyline"]]
            assert s.gender == r[config["gender"]]
            assert s.nationality == r[config["country"]]


def run_one_cohort(
    input_file: str,
    output_dir: str,
    prefix: str,
    dp_quit: bool,
    config: dict,
    runtime: int,
    prefix_filters: dict,
    target_group_size: int,
):
    """
    Runs the full pipeline for a single cohort prefix (e.g., 'M' (master) or 'E' (exchange))
    Returns:
      - best_group_split
      - df_used (filtered/processed df WITHOUT _row_id, ready for export)
      - per_run_group_sizes: groups with the number of students [{'Cohort','Group','Size'}...]
      - per_run_big_rows: all groups with student names and IDs [{'Cohort','Buddy Group','First name','Last name','Student number'}...]
      - per_run_studyline_counts: number of students per studyline (only meaningful for 'M'; else empty)
    """
    # validate filepaths and output dir
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Provided path is: '{input_file}'")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # read data
    df = pd.read_excel(input_file, header=0)

    # Filter by prefix ('M' or 'E')
    if prefix in prefix_filters:
        allowed_categories = prefix_filters[prefix]
        df = df[df["Participant category"].isin(allowed_categories)].copy()
        print(f"Filtering for prefix '{prefix}': keeping {len(df)} participants from categories {allowed_categories}")
    else:
        print(f"Warning: No filter defined for prefix '{prefix}', using all participants.")

    # Compute number of groups from target size
    n_students = len(df)
    n_groups = calc_num_groups(n_students, target_group_size)
    print(f"[{prefix}] Students: {n_students}, target/group ≈ {target_group_size} -> n_groups = {n_groups}")

    # Validate
    if n_groups > n_students:
        # (This can only happen if target_size is 0/negative, but keep the guard)
        n_groups = n_students

    # normalize / prep
    df = df.fillna("N/A").reset_index(drop=True)
    df[config["sn_col"]] = df[config["sn_col"]].astype(str)
    df[config["email_col"]] = df[config["email_col"]].astype(str).str.strip().str.lower()
    df["_row_id"] = np.arange(len(df))

    # missing required fields (fail fast if configured)
    check_missing_required(df, config, MISSING_QUIT)
    # duplicates
    # normalize emails for robust duplicate catch
    df[config["email_col"]] = df[config["email_col"]].astype(str).str.strip().str.lower()
    check_duplicates(df[config["sn_col"]], "Student number", dp_quit)
    check_duplicates(df[config["email_col"]], "Email", dp_quit)

    # stats
    print("#" * 20)
    print("STATS:")
    print_stats("gender", df, config, n_groups)
    print_stats("country", df, config, n_groups)
    print_stats("studyline", df, config, n_groups)
    print("#" * 20)

    # students
    students = [
        Student(
            int(row["_row_id"]),
            row[config["studyline"]],
            row[config["gender"]],
            row[config["country"]],
        )
        for _, row in df.iterrows()
    ]

    # random search
    t_end = time.time() + 60 * runtime
    best_score = -10_000_000
    best_group_split = None
    amount_execs = 0

    print(f"Starting the search (running {runtime} min) for prefix '{prefix}'...")
    while time.time() < t_end:
        with ProcessPoolExecutor() as ex:
            processes = [ex.submit(mp_wrapper, students, n_groups) for _ in range(50)]
        amount_execs += 50
        for p in processes:
            result = p.result()
            if result[0] > best_score:
                best_score = result[0]
                best_group_split = result[1]

    tried_fraction = amount_execs / stirling_second_kind(df.shape[0], n_groups)
    print(f"Finished. Tried {amount_execs} combinations")
    if tried_fraction < 1e-6:
        print(f"(This is equal to around {tried_fraction*100:.6e}% of all possible combinations)")
    else:
        print(f"(This is equal to around {tried_fraction*100:.6f}% of all possible combinations)")
    print("#" * 20)
    print(f"==> Best diversity score is: {best_score} (the closer to 0 the better)")
    print("#" * 20)

    # greedy improve (you can cap this if needed)
    print("Running greedy swapping search to try to improve")
    groups = best_group_split
    for _ in progressbar(range(100)):
        groups = greedy_assign(groups)
        score = np.mean([diversity_score(g) for g in groups])
        if score > best_score:
            best_group_split = groups
            best_score = score
    print("Finished")
    print("#" * 20)
    print(f"==> Best diversity score is now: {best_score} (the closer to 0 the better)")
    print("#" * 20)

    # integrity check
    assert_student_consistency(df, best_group_split, config)

    # drop _row_id so it doesn't leak into outputs
    df = df.drop(columns=["_row_id"])

    # write per-group files into subdir (master/exchange)
    subdir = "master" if prefix == "M" else "exchange"
    per_group_root = Path(output_dir) / subdir
    per_group_root.mkdir(parents=True, exist_ok=True)

    # collect per-run summaries
    per_run_group_sizes = []
    per_run_big_rows = []

    for i, g in enumerate(best_group_split):
        group_name = f"{prefix}{i+1:02d}"
        dir_path = per_group_root / group_name
        dir_path.mkdir(parents=True, exist_ok=True)

        values = [s.get_orig_data(df).values for s in g]
        groupdf = pd.DataFrame(values, columns=df.columns)

        # Drop any residual index-like column
        groupdf = groupdf.drop("Unnamed: 0", axis=1, errors="ignore").reset_index(drop=True)

        # For Exchange groups, delete studyline column from per-group file
        if prefix == "E":
            cols_to_keep = [
                config["fname_col"], config["lname_col"], config["sn_col"],
                config["country"], config["email_col"],
            ]
            groupdf_to_save = groupdf[cols_to_keep]
        else:  # MSc
            cols_to_keep = [
                config["fname_col"], config["lname_col"], config["sn_col"],
                config["country"], config["email_col"], config["studyline"],
            ]
            groupdf_to_save = groupdf[cols_to_keep]

        out_path = dir_path / f"{group_name}.xlsx"
        groupdf_to_save.to_excel(out_path, index=False)

        # group size summary row
        per_run_group_sizes.append({"Cohort": prefix, "Group": group_name, "Size": len(groupdf)})

        # big list rows (name + student number, plus cohort & group)
        for _, row in groupdf.iterrows():
            per_run_big_rows.append({
                "Cohort": prefix,
                "Buddy Group": group_name,
                config["fname_col"]: row[config["fname_col"]],
                config["lname_col"]: row[config["lname_col"]],
                config["sn_col"]: row[config["sn_col"]],
            })

    # studyline counts (only for MSc)
    if prefix == "M":
        study_counts = df[config["studyline"]].value_counts().rename_axis("Study line").reset_index(name="Count")
    else:
        study_counts = pd.DataFrame(columns=["Study line", "Count"])

    return best_group_split, df, per_run_group_sizes, per_run_big_rows, study_counts


def main(
    input_file: str,
    output_dir: str,
    dp_quit: bool,
    config: dict,
    runtime: int,
):
    """
    Orchestrates runs for BOTH cohorts: 'M' then 'E'.
    Writes:
      - per-group files in groups/master/ and groups/exchange/
      - groups/group_sizes.xlsx          (M+E)
      - groups/studyline_counts_M.xlsx   (M only)
      - groups/all_groups_big.xlsx       (M+E)
    """
    fun_intro()

    # run MSc
    m_res = run_one_cohort(
        input_file, output_dir, "M", dp_quit, config, runtime, PREFIX_FILTERS, TARGET_GROUP_SIZE
    )
    # run Exchange
    e_res = run_one_cohort(
        input_file, output_dir, "E", dp_quit, config, runtime, PREFIX_FILTERS, TARGET_GROUP_SIZE
    )

    # combine summaries
    _, _, m_group_sizes, m_big_rows, m_study_counts = m_res
    _, _, e_group_sizes, e_big_rows, e_study_counts = e_res  # e_study_counts is empty by design

    # 1) group sizes (M+E)
    group_sizes_df = pd.DataFrame(m_group_sizes + e_group_sizes)
    group_sizes_path = Path(output_dir) / "group_sizes.xlsx"
    group_sizes_df.to_excel(group_sizes_path, index=False)

    # 2) study line counts (only M)
    study_counts_path = Path(output_dir) / "studyline_counts_M.xlsx"
    m_study_counts.to_excel(study_counts_path, index=False)

    # 3) big list (M+E)
    big_df = pd.DataFrame(m_big_rows + e_big_rows)
    big_path = Path(output_dir) / "all_groups_big.xlsx"
    big_df.to_excel(big_path, index=False)

    print(f"\nSaved summaries:\n - {group_sizes_path}\n - {study_counts_path}\n - {big_path}")
    print("\n🎉 Groups created, spreadsheets saved, and chaos (mostly) contained.")
    print("Go forth and confuse a new generation of students responsibly. 💪")



if __name__ == "__main__":
    main(FILE, OUTPUT_P, DUPLICATE_QUIT, CONFIG, RUNTIME)
