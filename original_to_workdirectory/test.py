import os
from git import Repo
import numpy as np
import filecmp
import datetime
import shutil
from pathlib import Path

FORCED_CHECK = True # op True zetten als we toch de laatste periode willen doorlopen, ondanks dat er geen extra commit geweest is
WEEKS_TO_REVIEW = 3 # Hoeveel weken willen we teruggaan in de commits


seconds_in_week = 7*24*60*60 
review_from = datetime.datetime.now() - datetime.timedelta(seconds=seconds_in_week*WEEKS_TO_REVIEW)

folder_original_parent= './original'
folder_original = './original/2024_DS1_Mechelen' # todo, ik wil deze eruit

folder_workdir_parent= './workdir'
folder_workdir= './workdir/2024_DS1_Mechelen' # todo, ik wil deze eruit

main_folder_name = '2024_DS1_Mechelen'

repo_original = Repo(os.path.join(folder_original_parent, main_folder_name))
repo_workdir = Repo(os.path.join(folder_workdir_parent, main_folder_name))


origin_original = repo_original.remotes.origin
origin_workdir = repo_workdir.remotes.origin

different_files = []

def git_pull_repo_changed(repo):
    current = repo.head.commit

    repo.remotes.origin.pull()

    if current == repo.head.commit:
        print(f'Repo {repo.working_dir} not changed')
        return False
    else:
        print(f'Repo {repo.working_dir} changed!')
        return True
    
def git_push_untracked_or_changed(repo, commit_message):

    if (repo_workdir.untracked_files or repo_workdir.is_dirty()):

        untracked_files = repo.untracked_files
        changed_files = [item.a_path for item in repo.index.diff(None)] # None: not been staged

        print(f'Untracked files: {len(repo_workdir.untracked_files)} -> {untracked_files}')
        print(f'Dirty repo: {repo_workdir.is_dirty()}, changed files: {changed_files}')

        try:
            repo.index.add(untracked_files)
            repo.index.add(changed_files)
            repo.index.commit(commit_message)
            origin = repo.remote(name='origin')
            origin.push()
            print(f'Repo {repo.working_dir} is pushed.')

        except:
            print('Some error occured while pushing the code')    
    else:
        print(f'Nothing to push in repo {repo.working_dir}')

def copy_file_with_folders(src_file, dst_file):
    # Get the destination directory (i.e., the folder part of dst_file)
    dst_dir = os.path.dirname(dst_file)
    # Create the destination directory if it doesn't exist
    os.makedirs(dst_dir, exist_ok=True)  # exist_ok=True will not raise an error if the directory already exists
    # Copy the file to the destination directory
    shutil.copy2(src_file, dst_file) # copy 2 preserves metadata (timestamps)

    print(f"File {src_file} copied to {dst_file}")



def compare_folders(original, workdir):
    # Create a file comparison object
    comparison = filecmp.dircmp(original, workdir)

    # Check for differences
    if comparison.left_only:
        print(f"Files only in {original}: {comparison.left_only}")

    # Check for files that are different
    if comparison.diff_files:
        print(f"Different files: {comparison.diff_files}")
        # different_files.append(os.fi)


# Checken of er nieuwe wijzigingen zijn in de original repo, als die er niet zijn moeten we niets doen
original_repo_changed = git_pull_repo_changed(repo_original)

if (FORCED_CHECK or original_repo_changed ):

    # remote workdir pullen en dan committen en pushen indien nodig
    git_pull_repo_changed(repo_workdir)
    git_push_untracked_or_changed(repo_workdir, 'automatische commit in het script "original_to_workdirectory"')

    # herstellen van de modification times van de files, sync met git - TODO enkel doen als we een repo opnieuw hebben ingeladen, ook in aparte functie zetten
    # print(f'cd {folder_original} && git restore-mtime')
    # os.system(f'cd {folder_original} && git restore-mtime')
    # print(f'cd {folder_workdir} && git restore-mtime')
    # os.system(f'cd {folder_workdir} && git restore-mtime')

    # Get all files changed in commit since
    commits = repo_original.iter_commits(since=review_from)
    files_changed = set()
 
    for commit in commits:
        
        # Get files changed in commit 
        commit_files = repo_original.git.show(commit, name_only=True, format="%n").strip().splitlines()
        print(f"Commit: {commit.hexsha}, Author: {commit.author.name}, # Files: {len(commit_files)}")
        files_changed.update(commit_files)
    print(f'{len(files_changed)} files_changed: {files_changed}')

    # de gewijzigde files copieren naar onze workdir

    for filename in files_changed:
        filename_cleaned = bytes(filename.strip('"'), 'utf-8').decode('unicode_escape').replace('Ã«','ë') # vieze dingen omdat hij ë verkeerd escaped/decoded
        full_path_origin = os.path.join(folder_original, filename_cleaned) 
        full_path_workdir = os.path.join(folder_workdir_parent, filename_cleaned)

        if (os.path.exists(full_path_origin) and not os.path.exists(full_path_workdir)): # file exists in origin but not in workdir
            copy_file_with_folders(full_path_origin, full_path_workdir)

        # todo, ik denk dat we feitelijk best enkel de size vergelijken omdat de datums wel eens kunnen afwijken afh van commits enzo
        elif (os.path.exists(full_path_origin) and os.path.exists(full_path_workdir) and not filecmp.cmp(full_path_origin, full_path_workdir, shallow=True)): # file exists in both but not the same, Shallow true (enkel metadata (timestamps) en filesize vergelijken)
            # copy file to workdir with suffix _original (tenzij modiftime van origin voor de creation time van workdir file)
            dst_filename_transformed = Path(full_path_workdir).stem + '_original' + Path(full_path_workdir).suffix
            dst_path_with_extension = os.path.join(Path(full_path_workdir).parent, dst_filename_transformed)
            copy_file_with_folders(full_path_origin, dst_path_with_extension)

    # als file bestaat in origin en niet in workdir -> check of de gewenste folder bestaat, zoniet maak hem aan -> copy file
    # als file bestaat in origin en workdir en file is niet identiek -> indien de laatste wijziging aan de origin file nadat de workdir file is ontstaan -> copy met extensie _original