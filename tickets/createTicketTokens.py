"""
This script generates personalized ticket tokens / event tokens for every student
These can then be used to limit the purchase of tickets for an event to only students
that have such a token (not implemented here; needs to be implemented in the respective
system that handles the ticket purchases)

All that this script does is:
- create secure and non-guessable and unique token for every student

Students are identified by student number
For ease of use the output will also contain their first and last name
"""

import os
import secrets
import sys

# do a safe import
# the reason for doing this is that for example openpyxl will otherwise
# only be checked for once it is needed, which is at the end of the script
# we however want to check if it is existent at the start to save time
try:
    import openpyxl  # not directly needed but needed by pandas so check if installed at start
    import pandas as pd
except ImportError as exc:
    print("ERROR: Please install the packages pandas, openpyxl, numpy")
    print("Most likely this is done with 'pip install pandas openpyxl numpy'")
    raise exc

###########################################
# ADJUST THESE PARAMETERS
# INPUT FILE PATH (absolute or relative path!)
FILE = "testing/testdata.xlsx"

# PATH TO THE FILE THAT WILL HOLD THE TOKEN INFO
TOKEN_FILE = "tokens.xlsx"

# Config that tells the script how the columns are named
# change this to match the excel file column names
# e.g. "name_col" : "name" tells the script to find the name value
# in the column called "name". If you have a different name for this
# column then change "name" to the respective name
CONFIG = {
    "sn_col": "Student number",
    "fname_col": "First Name",
    "lname_col": "Last Name",
    "token_col": "Token",
}

# TOKEN LENGTH - only relevant to modify if you know what you are doing
# basically the longer this is the longer and more secure the tokens will be
# a setting of 16 bits might not be the most secure, but depending on the context
# this is sufficient enough will ensuring the token is still not too long
TOKEN_LEN = 16
###########################################


def gen_token(student_num: str, e_students: list, e_tokens: list, token_len: int):
    """
    Helper function that generates a new token for a student, that is identified
    by their student number

    If the student already has a token then None is returned

    It is ensured that a new token is not yet present in the existing
    list of tokens!
    """
    # check if the student already has a token
    # if so just return the existing token
    if student_num in e_students:
        return None

    # generate a new secure random token
    tk = secrets.token_urlsafe(token_len)

    # if the token already exists then generate a new one
    # until a new unique one has been generated
    while tk in e_tokens:
        tk = secrets.token_urlsafe(token_len)

    # append the student to existing ones
    e_students.append(student_num)

    # append the token to the existing ones
    e_tokens.append(tk)
    return tk, e_students, e_tokens


def main(file: str, tk_file: str, config: dict, tk_len: int):
    """
    The main function of this script

    - file: path to the file that holds the student information
    (student first name, last name, student number)
    - tk_file: path where the output will be saved (must not exist yet!)
    - config: configuration that tells how the columns in 'file' are named
    - tk_len: the length of the tokens in bits
    """
    if not os.path.isfile(file):
        print("FATAL ERROR: Could not find the file holding the student info")
        print(f"Provided path is: {file}")
        sys.exit(1)

    # stop processing if tk file already exists
    # this is done to not accidentally overwrite
    if os.path.isfile(tk_file):
        print("ERROR: Token file already exists")
        print(f"Provided path is: {tk_file}")
        sys.exit(1)

    token_df = pd.DataFrame(
        columns=[
            config["fname_col"],
            config["lname_col"],
            config["sn_col"],
            config["token_col"],
        ]
    )

    student_df = pd.read_excel(file, header=0)

    # all the students that need a token
    students = student_df[config["sn_col"]].values

    # lists that will hold already created students and tokens
    # this is done to prevent duplicates
    e_students = []
    e_tokens = []

    # generate a new token for each student
    for s in students:
        # duplicate student
        if s in e_students:
            print(f"Skipping duplicate student with number: {s}")
            continue
        token, e_students, e_tokens = gen_token(s, e_students, e_tokens, tk_len)
        s_info = student_df[student_df[config["sn_col"]] == s]
        token_df.loc[-1] = [
            s_info[config["fname_col"]].values[0],
            s_info[config["lname_col"]].values[0],
            s,
            token,
        ]
        token_df.index += 1
        token_df.sort_index(ascending=True, inplace=True)

    # save the new token file
    token_df.to_excel(tk_file)


if __name__ == "__main__":
    main(FILE, TOKEN_FILE, CONFIG, TOKEN_LEN)
