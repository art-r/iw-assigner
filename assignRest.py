"""
This script is made to make it easier to assign
people that sign up to the introweek after the deadline/via mail
and not with the form.
It assign group numbers for a specified amount of students
"""

import os
import sys

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
FILE = "testing/testdata.xlsx"

# Highest buddy group number
MAX_NUM = 30

# PREFIX (Masters = "M", Exchange = "E")
GROUP_PREFIX = "M"

# Config that tells the script how the columns are named
# change this to match the excel file column names
# e.g. "name_col" : "name" tells the script to find the name value
# in the column called "name". If you have a different name for this
# column then change "name" to the respective name
CONFIG = {
    "sn_col": "Student number",
    "email_col": "email",
}
###########################################


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


def get_rand_group(rng, max_val, prefix):
    """
    Helper function to get a random buddy group
    """
    return_val = f"{prefix}{rng.integers(1,max_val+1)}"
    return return_val


def main(filepath, max_n, config, prefix):
    """
    The main function of this script
    """
    # validate the file path
    if not os.path.isfile(filepath):
        print(f"FATAL ERROR: Could not find input file. Provided path is: '{filepath}'")
        sys.exit(1)

    # read the file
    df = pd.read_excel(filepath, header=0)

    # check for duplicates and quit if any are found
    check_duplicates(df, "All student info (exact duplicates)", True)
    check_duplicates(df[config["sn_col"]], "Student number", True)
    # check_duplicates(df[config["email_col"]], "Email", True)

    # assign a random group number
    # init the random number generator
    # there is no need to init it for each iteration, once is enough
    rng = np.random.default_rng()
    df["Buddy Group"] = ""
    df["Buddy Group"] = df["Buddy Group"].apply(
        lambda row: get_rand_group(rng, max_n, prefix)
    )

    df.to_excel(f"restStudents_{prefix}.xlsx")
    print(f"Results can be seen in 'restStudents_{prefix}.xlsx'")


if __name__ == "__main__":
    main(FILE, MAX_NUM, CONFIG, GROUP_PREFIX)
