#!/usr/bin/python3

'''
This script helps remap a Project directory to a Packaging directory under the user/group, prior to copy to CephFS.
This script uses a JSON file to determine ownership with user/group, especially for EPU DoseFractions or TemScripting folders.
author: Matt Larson
date: 2024-02-13
changelog: Updated to check for old projects and skip/notify.
'''

from __future__ import print_function
import sys
import os
import json
from subprocess import Popen, PIPE
import time
import argparse
import metadata

mock = 0
sep = '/'
version = 2.0

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def callRsync(src, dest):
    ''' Wrap rsync unidirectional copy and return number of updated files '''
    # Construct rsync command with arguments for uni-directional sync
    args = ["rsync", "-aui", "--inplace", src + sep, dest + sep]
    if mock:
        print(' '.join(args))
        return 0
    else:
        p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        rc = p.returncode
        return len(output.splitlines())

def getAllowedUserGroups(filename):
    ''' Parse the json values '''
    with open(filename) as f:	
       data = json.load(f)
       return data

def isValidGroup(groupname, mapping):
    ''' This could do an active directory or LDAP check '''
    if groupname not in mapping:
        return 0
    return 1

def isValidUser(groupname, user, mapping):
    ''' This could do an active directory or LDAP check '''
    if not isValidGroup(groupname, mapping):
        return 0
    if user not in mapping[groupname]:
        return 0
    return 1

def is_old(folder_path, weeks=3):
    ''' Method that can be used to avoid rsync on old project folders '''
    # Get the modification time of the folder
    modification_time = os.path.getmtime(folder_path)
    # Calculate the current time
    current_time = time.time()
    
    # Calculate the time difference in seconds
    time_difference_seconds = current_time - modification_time
    # Convert weeks to seconds
    weeks_in_seconds = weeks * 7 * 24 * 60 * 60
    # Check if the modification time is more than 3 weeks ago
    return time_difference_seconds > weeks_in_seconds


def syncProject(projectDir, packagingDir, permitted):
    ''' Given a project directory with a metadata file, process '''
    metadataPath = os.path.join(projectDir, 'dataset.json')
    if os.path.exists(metadataPath):
        info = metadata.DatasetMetadata(metadataPath)
        username = info.User.lower()
        group = info.Group.lower()
        if isValidGroup(group, permitted) and isValidUser(group, username, permitted):
            ''' setup the rsync '''
            projectDirBaseName = os.path.basename(projectDir)
            relativePath = os.path.join(group, username, projectDirBaseName)
            userPath = os.path.join(packagingDir, relativePath)

            # check folder modification date.
            if is_old(projectDir):
                print("[old project - skipping]: ", projectDir)
            else:
                if (not os.path.exists(userPath)):
                    os.makedirs(userPath)
                updated_count = callRsync(projectDir, userPath)
                if (updated_count > 0):
                    print(relativePath)
        else: 
            eprint("[Invalid user/group]: " + username + "/" + group + " " + projectDir)
    else:
        eprint("[Invalid project, no dataset.json present]: " + projectDir)

def syncProjectWithoutMetadata(projectDir, packagingDir, username, group, permitted):
    ''' Given a project directory, username, and groupname '''

    if isValidGroup(group, permitted) and isValidUser(group, username, permitted):
        ''' setup the rsync '''
        projectDirBaseName = os.path.basename(projectDir)
        relativePath = os.path.join(group, username, projectDirBaseName)
        userPath = os.path.join(packagingDir, group, username, projectDirBaseName)

        # check folder modification date.
        if is_old(projectDir):
            print("[old project - skipping]: ", projectDir)
        else:
            if (not os.path.exists(userPath)):
                os.makedirs(userPath)
            updated_count = callRsync(projectDir, userPath)
            if (updated_count > 0):
                print(relativePath)
    else: 
        eprint("[Invalid user/group]: " + username + "/" + group)

def syncEachUserDirectory(sourcepath, packagingDir, permitted):
    ''' List all the user directories '''
    dir_list = next(os.walk(sourcepath))[1]
    for d1 in dir_list:
        groupname = d1.lower()
        if isValidGroup(groupname, permitted):
            dir_list2 = next(os.walk(sep.join([sourcepath, d1])))[1]
            for d2 in dir_list2:
                username = d2.lower()
                if isValidUser(groupname, username, permitted):
                    # Get the list of directories under source:
                    projects = next(os.walk(sep.join([sourcepath, d1, d2])))[1]
                    for project in projects:
                        source = sep.join([sourcepath, d1, d2, project])
                        if (os.path.isdir(source)):
                            syncProjectWithoutMetadata(source, packagingDir, username, groupname, permitted)

                else:
                    eprint("[Invalid user, skipping]: " + sep.join([sourcepath, d1, d2]))
        else:
            eprint("[Invalid group, skipping]: " + sep.join([sourcepath, d1]))

def main(argv):

    # 1. Provide a command-line arguments
    parser = argparse.ArgumentParser(description='Start sync for Project Directories')
    parser.add_argument('--source', help='provide source location for project directories', required=False)
    parser.add_argument('--nestedSource', help='provide source location by group/user/project', required=False)
    parser.add_argument('--dest', help='provide destination location for packaging directory of mirrored data', required=True)
    parser.add_argument('--permissions', help='permissions file location', required=True)
    args = parser.parse_args()

    # This list could eventually be replaced by a service. 
    #permissionFile = '/mnt/cryofs_cemrc/users.json'
    permissionFile = args.permissions

    if not os.path.exists(permissionFile):
        eprint("Unable to read users file: " + permissionFile, file=sys.stderr)
        exit(1)

    permitted = getAllowedUserGroups(permissionFile)

    # Two paths to support either 'dataset.json', or group/user/project to know how to move data.
    if (args.source):
        d = args.source
        projects = [f.path for f in os.scandir(d) if f.is_dir()]

        for project in projects:
            syncProject(project, args.dest, permitted)
    elif (args.nestedSource):
        syncEachUserDirectory(args.nestedSource, args.dest, permitted)
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv)