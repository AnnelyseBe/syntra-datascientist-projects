import os
from git import Repo
import numpy as np


# print(os.listdir())
repo_original = Repo('./original/2024_DS1_Mechelen')
repo_workdirectory = Repo('./workdirectory/2024_DS1_Mechelen')

origin_original = repo_original.remotes.origin
origin_workdirectory = repo_workdirectory.remotes.origin


# origin_workdirectory.pull()
files = repo_workdirectory.untracked_files
index = repo_workdirectory.index
print(files)
print(repo_workdirectory.is_dirty()) # er zijn nog files die untracked zijn, of wijzigingen tov de remote
print(len(list(repo_workdirectory.iter_commits())))


for commit in list(repo_workdirectory.iter_commits()):
    print(commit.stats.files)






# print(repo_workdirectory.untracked_files)