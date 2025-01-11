"""
Script to read in the merged output of the legacy
group assigner script and calculate the diversity score according
to the new method
"""
import pandas as pd
import numpy as np
from createGroups import diversity_score
from createGroups import Student
df = pd.read_excel("output1.xlsx")
df = df.drop("Unnamed: 0", axis=1)

groups = []
for i in df.columns:
    g = []
    for x in df[i].values:
        if x is np.nan:
            continue
        infos = x.replace(" ", "").split(",")
        g.append(Student(infos[0], infos[1], infos[2], infos[3]))
    groups.append(g)

print(np.mean([diversity_score(g) for g in groups]))
