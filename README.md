# IW Assigner

This repository holds the code for assigning people to groups for IntroWeek.

The goal is to create groups that are as diverse as possible, accounting for gender, studyline, and home country.

Depending on what you want to do this is the code file that you need:

| Goal | Needed file |
|---|---|
| Pre-processing the student list to remove duplicate entries | `dedupe_students.py` |
| Initial assignment of all students to diverse groups | `createGroups.py` |
| Assignment of students that signed up after deadline | `assignRest.py` |
| Generate unique ticket tokens for all students | `tickets/createTicketTokens.py` |

> note that `assignRest.py` will only assign random buddy group numbers but not add them to any existing files that were generaterd by `createGroups.py`, since it is assumed that these files might already have been distributed or sent away etc.

## Step 1: Pre-processing: Clean Your Student List (Recommended Before Running Anything)

Before creating the IntroWeek groups, it is recommended to clean the student list to remove duplicate entries (email or student number). Students occasionally sign up twice, mistype their email, or write S123456 instead of s123456, which can lead to mismatches later in the group creation process.

To handle this, you can use the script dedupe_students.py.
It identifies duplicate entries and (if you choose) removes them.

| Task                                                | Done by `dedupe_students.py` |
| --------------------------------------------------- | ---------------------------- |
| Detect duplicate student numbers (case-insensitive) | ✔️                           |
| Detect duplicate emails (case-insensitive)          | ✔️                           |
| Ignore missing values (N/A, empty, NaN)             | ✔️                           |
| Show which entries are duplicates                   | ✔️                           |
| Ask whether duplicates should be removed            | ✔️                           |
| Save cleaned file with no duplicates                | ✔️                           |
| Save removed duplicates separately                  | ✔️                           |

### How to use the script

- Install all dependencies (using the package manager of your choice)\
You need: `pandas`, `numpy` and `openpyxl`

> If you have no idea what this means then make sure to follow this for Windows: https://www.geeksforgeeks.org/how-to-install-pip-on-windows/

- Locate the file that contains all the information about the signed up people (**DO NOT UPLOAD IT HERE**)

- Open the file `dedupe_students.py` and adjust the parameters starting in line 20 until line 31 and save it

- Run the script with `python3 dedupe_students.py` 
> (If that doesn’t work, try: `python dedupe_students.py`)

- The results will be placed in the main directory `iw-assigner` named `students_list_removed_duplicates.xlsx` (excel containing the removed students) and `students_list_no_duplicates.xlsx` (final excel later used for the groups)

## Step 2: Creating random Buddy groups

- After this step you will have all the results in the directory `groups`, namely the per-group files in `groups/master/` and `groups/exchange/`, a file containing all groups and their number of students called `group_sizes.xlsx` (M+E), a file containing the number of students per studyline called `studyline_counts_M.xlsx` (M only), and a file containing all the groups with the student information called `all_groups_big.xlsx` (M+E)

### How to run the script
- Install all dependencies (using the package manager of your choice)\
You need: `pandas`, `numpy` and `openpyxl` (**ONLY APPLICABLE IF YOU HAVE NOT DONE THIS ALREADY IN STEP 1**)

> If you have no idea what this means then make sure to follow this for Windows: https://www.geeksforgeeks.org/how-to-install-pip-on-windows/

- Locate the file that contains all the information about the signed up people (should be called `*_no_duplicates.xlsx`)

- Adjust the parameters in the file `createGroups.py` starting in line 47 until line 94

- Run the script with `python3 createGroups.py` 
> (If that doesn’t work, try: `python createGroups.py`)

- The results will be placed in the directory `groups`

### General approach to the group assignment
- Randomly create group distributions for a specified amount of time
while using multiprocessing and therefore making use of the available device performance as much as possible
- Keep track of the randomly created group with the best diversity score
- After the specified amount of time has passed, use a greedy algorithm to make some
random swaps in the group with the best diversity to see if the score can be improved => this will then be the result


## Background for the solution
The problem of creating the most diverse groups is similar to the set packing problem, which is an NP-complete problem (https://en.wikipedia.org/wiki/Set_packing). Therefore, it is safe to assume that there is no efficient algorithm that can achieve the best solution for creating the most diverse groups.

The best approach is to create randomly assigned groups for as long as feasible and then try to improve iteratively on the best found group. Note that the longer the script is allowed to run, the better the diversity score may get. Since we are working with randomness, this means only the probability of getting more diverse groups increases. The script is therefore all about trying to increase this probability while staying within a still feasible time frame. We cannot wait an unreasonably long time for the script to finish, even though this would most likely come pretty close to finding the ideal distribution that has the maximum diversity.


