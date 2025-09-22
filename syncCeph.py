#!/usr/bin/python3

'''
Rsync & Remapping script to move projects to CephFS
author: Matt Larson
date: 2024-02-13
changelog: Updated to check for old projects and skip/notify.
'''

from __future__ import print_function
import sys
import os
import json
import subprocess
import grp
import time
from subprocess import Popen, PIPE

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

mock = 0
sep = '/'
version = 2.0

def callRsync(src, dest):
    ''' Wrap rsync unidirectional copy and return number of updated files '''
    # Construct rsync command with arguments for uni-directional sync
    # 12/17/2024 - adding arguments to define permissions and avoid access issues.
    args = ["rsync", "-aui", "--chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r", src + sep, dest + sep]
    if mock:
        print(' '.join(args))
        return 0
    else:
        p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        rc = p.returncode
        return len(output.splitlines())

def createStaffDirectory(destProject):
    ''' create a processing folder for staff '''
    staff_folder = 'staff_proc'
    staff_group = 'CEMRC-facility@ad.wisc.edu'
    path_to_proc = os.path.join(destProject, staff_folder)

    if not os.path.isdir(path_to_proc):
        os.makedirs(path_to_proc)

    gid = grp.getgrnam(staff_group).gr_gid
    os.chown(path_to_proc, 0, gid)
    os.chmod(path_to_proc, 0o775)

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

### CephFS copy and permission functions.
def syncEachUserToCephFS(sourcepath, cryofs, source, permitted):
    ''' List all the user directories '''
    dir_list = next(os.walk(sourcepath))[1]
    for d1 in dir_list:
        groupname = d1.lower()
        if isValidGroup(groupname, permitted):
            dir_list2 = next(os.walk(sep.join([sourcepath, d1])))[1]
            for d2 in dir_list2:
                username = d2.lower()
                ad_user = username + '@ad.wisc.edu'
                ts = time.time()
                if isValidUser(groupname, username, permitted):
                    # Get the list of directories under source:
                    projects = next(os.walk(sep.join([sourcepath, d1, d2])))[1]
                    for project in projects:
                        orig = sep.join([sourcepath, d1, d2, project])
                        dest = sep.join([cryofs, groupname, ad_user, source, project])
                        if (os.path.isdir(orig)):
                            # check folder modification date.
                            if is_old(orig):
                                print("[old project - skipping]: ", orig)
                            else:
                                # copies now at project level, requires creating parent folder.
                                parent_folder = sep.join([cryofs, groupname, ad_user, source])
                                if (not os.path.exists(parent_folder)):
                                    os.makedirs(parent_folder)
                                updated_count = callRsync(orig, dest)
                                if (updated_count > 0):
                                    print(orig)
                        # iterate through the project directories and create `staff_proc`
                        if os.path.isdir(dest) and os.path.getctime(dest) > ts:
                            print("Create a staff_proc in " + dest)
                            createStaffDirectory(dest)
                else:
                    eprint("[Invalid user, skipping]: " + sep.join([sourcepath, d1, d2]))
        else:
            eprint("[Invalid group, skipping]: " + sep.join([sourcepath, d1]))

def getAllowedUserGroups(filename):
    ''' Parse the json values '''
    with open(filename) as f:	
       data = json.load(f)
       return data

def main(argv):

    # This list could eventually be replaced by a service. 
    permissionFile = '/mnt/cryofs_cemrc/users.json'

    if not os.path.exists(permissionFile):
        print("Unable to read users file: " + permissionFile, file=sys.stderr)
        exit(1)

    permitted = getAllowedUserGroups(permissionFile)

    # Data sources directory
    data_sources = [ "krios-k3", "krios-f3", "krios-f4", "arctica-k3", "arctica-f3", "aquilos", "aquilos2", "l120c", "l120c-cetaf"]

    # Expect mirror shares to exist in this prefix location
    mirror_prefix = "/mnt/buffer/mirror-"

    # CephFS upload directory
    cryofs_path = "/mnt/cryofs_cemrc/incoming/"

    # Perform the unidirectional sync and remapping to CephFS
    for source in data_sources:
        sourcepath = mirror_prefix + source
        if (os.path.isdir(sourcepath)):
            syncEachUserToCephFS(sourcepath, cryofs_path, source, permitted)

if __name__ == "__main__":
    main(sys.argv)
