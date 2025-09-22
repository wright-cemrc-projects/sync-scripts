# sync-scripts
Utilities for rsync and transfers

## Example for how to configure the transfers

Crontab as a root user to transfer to the network storage:

```
# Periodic copy of staging location on Linux server to CephFS
2-59/5 * * * * /usr/bin/flock -w 0 /run/lock/cephfs.transfer.lock /opt/cemrc/cryo-pipeliner/python/util/syncCeph.py 2>&1 | tee -a /var/log/sync.ceph
```

Crontab as a local user to copy from SMB file share from instrument PC:

```
# Periodic copy from instrument to a staging location on Linux server
*/5 * * * * /usr/bin/flock -w 0 /home/cryojob/dosefraction.rsync.lock /opt/cemrc/cryo-pipeliner/python/jobs/syncProject.py --source /mnt/krios-k3/DoseFractions/ --dest /mnt/buffer/mirror-krios-k3/ --permissions /mnt/cryofs_cemrc/users.json 2>&1 | /opt/cemrc/cryo-pipeliner/python/jobs/enqueueJobs.py --base=/mnt/buffer/mirror-krios-k3/ 2>&1 | tee -a /var/log/sync.cryojob
```

## Notes

The syncCeph.py will copy from <group>/<user> folders locally to a network storage where things are similarly organized. In addition, it will deposit under a folder describing the instrument source. This can avoid collisions where the same user on different instruments had a similarly named folder.

The syncProject.py will copy from a folder created by EPU under X:\DoseFractions on a RAID array associated with an instrument. Here it will read in a dataset.json in the folder that describes who owns the data. This metadata.json is created by a GUI application that users fill in details of their data collection and saves as a json and README.txt to document their data collection.

Rsync copies are setup to override permissions and set ownerships.

syncProject.py will emit the paths of folders with changed contents in the `rsync` copies, and these can be passed to scripts by a | for further downstream preprocessing setup or general logging.
