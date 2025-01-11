import os
import random
import pandas as pd  # Also install openpyxl

# import getopt #TODO: Command-line arguments for easier use

"""
Credit goes to: My favorite neighbor <3

HOW TO USE:

Set working directory to the folder where your files are located (if running from e.g. Spyder)    

Set FILENAME below to the name of the Excel file containing all student data.

Set OUT_PREFIX to "M" or "E" for MSc or Exchange students.

Set N_GROUPS to the number of groups you need generated.

Check that the column names for study program, gender, and nationality in the Excel
sheet are "Study programme", "To which Gender do you identify the most?", and "Home Country", respectively. 
Otherwise change it.

Play with MAX_SCORE, NO_INVALID_GROUP, MAX_ONLY_VALID_TRIES, MAX_PROBLEM_GROUP_RESHUFFLE and RAISE_TOLERANCE at your own risk.
Worst case is the script will run for a while and generate worse groups.

Install required packages:
'pip install pandas openpyxl'
There was another package requirement but I kinda forgot to write it down lol

Make sure the script is in the same directory as the Excel files (type "cd DIRECTORY PATH" in the command prompt). 
Output files will also be placed here.

Start the script in the command prompt with
'python MSCGrouper.py'
"""

# Validation at the end is missing
# Flag potential duplicate students!

# Set working directory (i.e. where the files are located)
# this is not a good way of doing it
# os.chdir(r"")


# How many groups to generate
N_GROUPS = 24

# Maximum similarity score in the group. Higher -> Allow for more similarity. Around 7 seems possible, but often lands at 8.5
MAX_SCORE = 7

# Allow no groups above the maximum similarity score
NO_INVALID_GROUP = True

# How many attempts should be made to generate groupings at a given similarity score
MAX_ONLY_VALID_TRIES = 100

# Automatically raise tolerance for similarity if no valid groups are found after MAX_ONLY_VALID_TRIES attempts
RAISE_TOLERANCE = True

# How many times should a set of problem-groups be reshuffled together before starting over
MAX_PROBLEM_GROUP_RESHUFFLE = 10000

# Input file name
# FILENAME = "Participants-MSC-Autumn-22.xls"
# FILENAME = "Masters_Fullweek_Jan24.xlsx"
FILENAME="testdata.xlsx"
# Prefix of output file. Example: OUT_PREFIX = "M" will result in group files called M01.xlsx, M02.xlsx...
# OUT_PREFIX = "M"
OUT_PREFIX = "M"


class Student:
    def __init__(self, index, study, gender, nationality):
        self.index, self.study, self.gender, self.nationality = (
            index,
            study,
            gender,
            nationality,
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

    def getData(self, inputFile):
        return inputFile.loc[self.index]


nStudy = {}
nGender = {}
nNationality = {}


def getExcelInput(filename):
    # https://pandas.pydata.org/pandas-docs/stable/reference/frame.html
    file = pd.read_excel(filename)
    nStudents = file.shape[0]
    students = []
    # can probably be done more efficiently
    """
	file = pd.read_excel(filename)
	file = file.fillna({"Study programme": "No data", "To which Gender do you identify the most?": "None", "Home Country": "None"})

	nStudy = file["Study programme"].value_counts()
	nGender = file["To which Gender do you identify the most?"].value_counts()
	nNationality = file["Home Country"].value_counts()

	students = [Student(i, study, gender, nationality) for i, (study, gender, nationality) in enumerate(zip(file["Study programme"], file["To which Gender do you identify the most?"], file["Home Country"]))]
	"""
    for i in range(nStudents):
        study = str(file.at[i, "Study programme"])
        gender = str(file.at[i, "To which Gender do you identify the most?"])
        nationality = str(file.at[i, "Home Country"])
        if study == "nan":
            study = "No data"
        if gender == "nan":
            gender = "None"
        if nationality == "nan":
            nationality == "None"
        if study not in nStudy:
            nStudy[study] = 0
        if gender not in nGender:
            nGender[gender] = 0
        if nationality not in nNationality:
            nNationality[nationality] = 0
        nStudy[study] = nStudy[study] + 1
        nGender[gender] = nGender[gender] + 1
        nNationality[nationality] = nNationality[nationality] + 1
        student = Student(i, study, gender, nationality)
        students.append(student)
    print(" ### Target gender distribution (Gender, total amount, avg. per group) ### ")
    for k, v in nGender.items():
        print(k, "-", v, "- Avg:", v / N_GROUPS)
    print(
        "\n\n ### Target country distribution (Gender, total amount, avg. per group) ### "
    )
    for k, v in nNationality.items():
        print(k, "-", v, "- Avg:", v / N_GROUPS)
    print(
        "\n\n ### Target studyline distribution (Gender, total amount, avg. per group) ### "
    )
    for k, v in nStudy.items():
        print(k, "-", v, "- Avg:", v / N_GROUPS)
    return students, file


def createGroupFile(group, inputFile, groupID, prefix=OUT_PREFIX):
    values = []
    for s in group:
        values.append(s.getData(inputFile).values)
    # no fail safe writing
    df = pd.DataFrame(values, columns=inputFile.columns)
    outpath = prefix + str(groupID).zfill(2) + ".xlsx"
    writer = pd.ExcelWriter(outpath)
    df.reset_index(drop=True)
    df.to_excel(writer)
    writer.save()


def evalNationality(group):
    score = 0
    """
	Want:
	- Different countries
	- Countries split up
	lower score for many identical countries
	account for countries maybe needing multiple in a group. Aim for nCountry/nGroup
	"""
    nations = {}
    # inefficient as double for loops
    for s in group:
        nations[s.nationality] = 0
    for s in group:
        nations[s.nationality] = nations[s.nationality] + 1
    for k, v in nations.items():
        intendedAvg = nNationality[k] / N_GROUPS if nNationality[k] >= N_GROUPS else 1
        if v > intendedAvg:
            score += (v - intendedAvg) / intendedAvg
    return score


def evalGender(group):
    score = 0
    """
	Split genders as evenly as possible
	Do not want a group with too many of one
	High difference from intended average = bad, low score
	"""
    genders = {}
    # inefficient as double for loops
    for s in group:
        genders[s.gender] = 0
    for s in group:
        genders[s.gender] = genders[s.gender] + 1
    for k, v in genders.items():
        intendedAvg = nGender[k] / N_GROUPS if nGender[k] >= N_GROUPS else 1
        if v > intendedAvg:
            score += (v - intendedAvg) / intendedAvg
    return score


def evalStudies(group):
    """
    Same as nationality
    """
    score = 0
    studies = {}
    # inefficient as double for loops
    for s in group:
        studies[s.study] = 0
    for s in group:
        studies[s.study] = studies[s.study] + 1
    for k, v in studies.items():
        intendedAvg = nStudy[k] / N_GROUPS if nStudy[k] >= N_GROUPS else 1
        if v > intendedAvg:
            score += (v - intendedAvg) / intendedAvg
    return score


def diversityScore(group):
    """
    Add 3 evaluation scores together, maybe weighted
    Score below threshold = Some teams not diverse enough. Retry.
    """
    studies = evalStudies(group)
    genders = evalGender(group)
    nations = evalNationality(group)
    score = studies + genders + nations
    # print("S:", studies, "G:", genders, "N:", nations, "Total:", score)
    return score


def generateGroups(sList, n=N_GROUPS):
    # numpy is faster so replace (np.random.shuffle)
    random.shuffle(sList)
    # this potentially assigns students to multiple groups
    # need to be done in a more failsafe way
    groups = [sList[i::n] for i in range(n)]
    return groups


def evalGroups(groups):
    problemGroups = []
    global finalGroups
    for g in groups:
        score = diversityScore(g)
        if score > MAX_SCORE:
            problemGroups.append(g)
        else:
            finalGroups.append(g)
    return problemGroups


def getBestGrouping(students):
    global finalGroups
    finalGroups = []

    groups = generateGroups(students)
    problemGroups = evalGroups(groups)

    tries = 0
    while len(problemGroups) > 1 and tries < MAX_PROBLEM_GROUP_RESHUFFLE:
        tries += 1
        newStudents = [s for g in problemGroups for s in g]
        newStudents = generateGroups(newStudents, n=len(problemGroups))
        problemGroups = evalGroups(newStudents)

    # In case there is one left
    if len(problemGroups) != 0:
        finalGroups += problemGroups

    return finalGroups, len(problemGroups) != 0


if __name__ == "__main__":
    students, inputFile = getExcelInput(FILENAME)
    results, hasInvalid = getBestGrouping(students)
    if NO_INVALID_GROUP:
        counter = 1
        while counter < MAX_ONLY_VALID_TRIES and hasInvalid:
            results, hasInvalid = getBestGrouping(students)
            counter += 1
            if counter >= MAX_ONLY_VALID_TRIES and RAISE_TOLERANCE and hasInvalid:
                counter = 0
                MAX_SCORE += 0.5
                print("\n\nThreshold increased to", MAX_SCORE, "\n\n")

    print(len(results), "groups generated from", len(students), "students.")
    tot = 0
    for i in range(len(results)):
        print("Group", i + 1, "-", diversityScore(results[i]))
        tot += diversityScore(results[i])
        # createGroupFile(results[i], inputFile, i + 1)
    pd.DataFrame(results).transpose().to_excel("output.xlsx")
    print("Average similarity score: ", tot / len(results))
    highestScoring = max(results, key=lambda g: diversityScore(g))
    print("Max similarity score:", diversityScore(highestScoring))
    print("Group with highest score:")
    for s in highestScoring:
        print(s)
