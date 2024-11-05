import os
from git import Repo
import numpy as np
import filecmp
import datetime
import shutil
from pathlib import Path

FORCED_CHECK = True # op True zetten als we toch de laatste periode willen doorlopen, ondanks dat er geen extra commit geweest is
WEEKS_TO_REVIEW = 3 # Hoeveel weken willen we teruggaan in de commits
SYNC_GIT_MODIFICATION_TIME = True # vooral nodig indien we de repo opnieuw hebben gecloned

seconds_in_week = 7*24*60*60 
review_from = datetime.datetime.now() - datetime.timedelta(seconds=seconds_in_week*WEEKS_TO_REVIEW)

main_folder_name = '2024_DS1_Mechelen'
folder_original_parent= './original'
folder_original = os.path.join(folder_original_parent, main_folder_name)
folder_workdir_parent= './workdir'
folder_workdir= os.path.join(folder_workdir_parent, main_folder_name)

repo_original = Repo(folder_original)
repo_workdir = Repo(folder_workdir)

origin_original = repo_original.remotes.origin
origin_workdir = repo_workdir.remotes.origin

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

        untracked_files = repo.untracked_files # new files
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

def restore_modification_time_of_git_files(folder):
    os.system(f'cd {folder} && git restore-mtime')
    print(f'modification time of {folder} is synced with git and restored')

def copy_file_with_folders(src_file, dst_file):
    # Get the destination directory (i.e., the folder part of dst_file)
    dst_dir = os.path.dirname(dst_file)
    # Create the destination directory if it doesn't exist
    os.makedirs(dst_dir, exist_ok=True)  # exist_ok=True will not raise an error if the directory already exists
    # Copy the file to the destination directory
    shutil.copy2(src_file, dst_file) # copy 2 preserves metadata (timestamps)
    print(f'{src_file}->{dst_file}')

# Checken of er nieuwe wijzigingen zijn in de original repo, als die er niet zijn moeten we niets doen
original_repo_changed = git_pull_repo_changed(repo_original)

if (FORCED_CHECK or original_repo_changed):

    # pull remote workdir and commit and push ongoing changes
    git_pull_repo_changed(repo_workdir)
    git_push_untracked_or_changed(repo_workdir, 'automatische commit in het script "original_to_workdirectory"')

    if (SYNC_GIT_MODIFICATION_TIME):
        restore_modification_time_of_git_files(folder_original)
        restore_modification_time_of_git_files(folder_workdir)
        
    # Get all files changed in commit since
    commits = repo_original.iter_commits(since=review_from)
    files_changed = set()
 
    for commit in commits:
        # Get files changed in commit 
        commit_files = repo_original.git.show(commit, name_only=True, format="%n").strip().splitlines()
        print(f"Commit: {commit.hexsha}, Author: {commit.author.name}, # Files: {len(commit_files)}")
        files_changed.update(commit_files)
    print(f'{len(files_changed)} files_changed in the origin folder')

    # de gewijzigde files copieren naar onze workdir
    for filename in files_changed:
        print(f'for filename {filename}')
        filename_cleaned = bytes(filename.strip('"'), 'utf-8').decode('unicode_escape').replace('Ã«','ë') # vieze dingen omdat hij ë verkeerd escaped/decoded
        full_path_origin = os.path.join(folder_original_parent, main_folder_name, filename_cleaned) 
        full_path_workdir = os.path.join(folder_workdir_parent, main_folder_name, filename_cleaned)
        print(f'for full_path_workdir {full_path_workdir} - {os.path.exists(full_path_workdir)}')

        if (os.path.exists(full_path_origin) and not os.path.exists(full_path_workdir)): # file exists in origin but not in workdir
            copy_file_with_folders(full_path_origin, full_path_workdir)

        elif (os.path.exists(full_path_origin) and os.path.exists(full_path_workdir) and not filecmp.cmp(full_path_origin, full_path_workdir, shallow=False)): # file exists in both but are not the same, Shallow False (files vergelijken zonder metadata =timestamps)
            # nu kopieren we altijd de originele versie, in principe is dit niet nodig als de laatste modification time voor de creatie van de original file is. Maar moeilijk om de birth time te pakken te krijgen
            dst_filename_transformed = Path(full_path_workdir).stem + '_original' + Path(full_path_workdir).suffix
            dst_path_with_extension = os.path.join(Path(full_path_workdir).parent, dst_filename_transformed)
            copy_file_with_folders(full_path_origin, dst_path_with_extension)

    print(f'Copies zijn gemaakt, nu nog te verifieren en manueel de workdir committen en pushen (dit kan ook door dit script nog eens te laten lopen :-))')

else:
    print(f'No action because the original repo change: {original_repo_changed} and FORCED_CHECK: {FORCED_CHECK}')