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

from concurrent.futures import ProcessPoolExecutor

# safe import
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
FILE = "testing/testdata.xlsx"

# How many groups to generate
N_GROUPS = 24

# Output directory (output files will be saved in this dir)
# absolute or relative path (dir MUST EXIST!)
OUTPUT_P = "groups/"

# Prefix of output file.
# Example: OUT_PREFIX = "M" will result in group files called M01.xlsx, M02.xlsx...
OUT_PREFIX = "M"

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
    "name_col": "Name",
    "email_col": "email",
    "studyline": "Study programme",
    "gender": "To which Gender do you identify the most?",
    "country": "Home Country",
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

    def __init__(self, index, study, gender, nat):
        self.index, self.study, self.gender, self.nationality = (
            index,
            study,
            gender,
            nat,
        )

    def __str__(self):
        return (
            str(self.index)
            + ", "
            + self.study
            + ", "
            + self.gender
            + ", "
            + self.nationality
        )

    def get_orig_data(self, df):
        """
        Helper function to get the original data
        from the dataset based upon the index
        Handy if there is more data than what is saved here in this class
        """
        return df.loc[self.index]


def check_duplicates(data, duplicate_type, quit):
    """
    Helper function to check for duplicates
    """
    if data.duplicated().sum() > 0:
        print("#" * 10)
        print(f"Found duplicates based upon: {duplicate_type}")
        print("The following rows are flagged as duplicates:\n")
        print(data[data.duplicated()])
        print("#" * 10)
        if quit:
            print("Stopping the script")
            print("Change this behavior by setting DUPLICATE_QUIT to False")
            sys.exit(0)


def print_stats(category, df, config, n_groups):
    """
    Helper function to print statistics about a category
    """
    print(
        f"\n{category} information (type, amount (% of all), ideal avg. amount per group)"
    )
    count = df[config[category]].value_counts()
    amount = df.shape[0]
    n_count = df[config[category]].value_counts(normalize=True)
    for c in df[config[category]].unique():
        ideal_avg = round(count[c] / n_groups, 1)
        # round the ideal avg to 1 if it is below 1
        ideal_avg = 1 if ideal_avg < 1 else ideal_avg
        print(f"{c} - {count[c]} ({round(count[c]/amount*100,0)}%) - {ideal_avg}")


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


def main(
    input_file: str,
    output_dir: str,
    o_prefix: str,
    n_groups: int,
    dp_quit: bool,
    config: dict,
    runtime: int,
):
    """
    The main function
    """
    # validate filepaths and output dir
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Provided path is: '{FILE}'")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # read data
    df = pd.read_excel(input_file, header=0)

    # validate N_GROUPS < amount of students
    if n_groups > df.shape[0]:
        raise ValueError(
            f"Group amount ({n_groups}) is larger student amount ({df.shape[0]})"
        )

    # fill NA values to be consistent
    df = df.fillna("N/A")

    # flag potential duplicates
    # checking for:
    # 1. exact duplicates
    # 2. name duplicates
    # 3. email duplicates
    check_duplicates(df, "All student info (exact duplicates)", dp_quit)
    check_duplicates(df[config["name_col"]], "Student name", dp_quit)
    check_duplicates(df[config["email_col"]], "Email", dp_quit)

    # print some stats
    print("#" * 20)
    print("STATS:")
    print_stats("gender", df, config, n_groups)
    print_stats("country", df, config, n_groups)
    print_stats("studyline", df, config, n_groups)
    print("#" * 20)

    # convert each row to a student and save all in a list
    students = [
        Student(i, study, gender, nat)
        for i, (study, gender, nat) in enumerate(
            zip(df[config["studyline"]], df[config["gender"]], df[config["country"]])
        )
    ]

    # do random group assignments for a specified amount of time
    # while tracking the group w the best diversity score
    # set the end time
    t_end = time.time() + 60 * runtime

    best_score = -10000000
    best_group_split = None
    amount_execs = 0

    print(f"Starting the search (running {runtime} min)...")
    while time.time() < t_end:
        # For the specified amount of time create random groups in
        # batches of 50 processes at a time and then evaluate
        # the number 50 is chosen arbitrarily but shouldnt be too high
        # to avoid performance issues (especially on slower devices)
        with ProcessPoolExecutor() as ex:
            processes = [ex.submit(mp_wrapper, students, n_groups) for i in range(50)]
        # track the amount of executions for more insights
        amount_execs += 50

        for p in processes:
            result = p.result()
            # check if the result was better than the best score
            # if so then save the score and the group split
            if result[0] > best_score:
                best_score = result[0]
                best_group_split = result[1]

    tried = round(amount_execs / stirling_second_kind(df.shape[0], n_groups), 10)
    print(f"Finished. Tried {amount_execs} combinations")
    print(f"(This is equal to around {tried}% of all possible combinations)")
    print("#" * 20)
    print(f"==> Best diversity score is: {best_score} (the closer to 0 the better)")
    print("#" * 20)
    print("Running greedy swapping search to try to improve")
    # now take the group w the best diversity score and apply greedy algorithm
    # to try to swap around students until the diversity score
    # try 10.000 different swaps
    groups = best_group_split
    for _ in progressbar(range(10000)):
        groups = greedy_assign(groups)
        score = np.mean([diversity_score(g) for g in groups])
        if score > best_score:
            best_group_split = groups
            best_score = score
    print("Finished")
    print("#" * 20)
    print(f"==> Best diversity score is now: {best_score} (the closer to 0 the better)")
    print("#" * 20)
    # write the result
    out_path = os.path.join(output_dir, f"{o_prefix}_all_groups.xlsx")
    # the overview
    pd.DataFrame(
        best_group_split, index=[f"{o_prefix}{i}" for i in range(1, n_groups + 1)]
    ).to_excel(out_path)

    # save also per group (one folder per group)
    # folder (should contain all info)
    for i, g in enumerate(best_group_split):
        dir_path = os.path.join(output_dir, f"{o_prefix}{i+1}")
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        values = []
        for student in g:
            values.append(student.get_orig_data(df).values)
        groupdf = pd.DataFrame(values, columns=df.columns)
        # drop the original index
        groupdf = groupdf.drop("Unnamed: 0", axis=1)
        groupdf.reset_index(drop=True, inplace=True)
        out_path = os.path.join(dir_path, f"{o_prefix}{i+1}.xlsx")
        groupdf.to_excel(out_path)


if __name__ == "__main__":
    main(FILE, OUTPUT_P, OUT_PREFIX, N_GROUPS, DUPLICATE_QUIT, CONFIG, RUNTIME)
