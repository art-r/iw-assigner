# IW Assigner

This repository holds the code for assigning people to groups for IntroWeek.

The goal is to create groups that are as diverse as possible, accounting for gender, studyline, and home country.

## How to run this
- Install all dependencies (using the package manager of your choice)\
You need: `pandas`, `numpy` and `openpyxl`

- Locate the file that contains all the information about the signed up people (**DO NOT UPLOAD IT HERE**)

- Adjust the parameters in the file `createGroups.py` starting in line 42 until line 78

- Run the script with `python3 createGroups.py`

- The results will be placed in the directory `groups`

