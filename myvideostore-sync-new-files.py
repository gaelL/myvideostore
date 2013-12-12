#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from myvideostore.tools import Print
from myvideostore.db import Db
from myvideostore.tools import create_dir, copy_file, remove_empty_dir, check_file_consistency
import argparse
from os.path import join
import os
import re


# TODO ./myvideostore-sync-new-files.py -s Videos/ -t dst
#X  * Prendre en arg un dossier src et un dst
#X  * Faire un fichier db à la racine de ce dossier dst
#X  * La db va contenir le path et un hash du fihier et status (copied)
#  * Possible d'ajouter des excludes pour les dossiers.
#     * Idee mettre ca dans un db_name exclude. Ajouter des arg au script pour exclude-add -list -del
#     * Del attendra un ID donné par liste. DB : excludename -> id
#     * Copy se fait uniquement si le relative_file ne match pas un exclude
#     * Si c'est une opération sur un exclude ne pas copier les fichiers
#X  * copier les nouveaux fichiers et reconstruire l'arbo
#X  * Apres passage du sync clean des dossiers vides
#  * + Ajouter la liste des nouvelles videos dans la db du videostore


# Init logging level with debug stream handler
LOG = logging.getLogger()
LOG.setLevel(logging.CRITICAL)
LOG.setLevel(logging.INFO)

# Get args
PARSER = argparse.ArgumentParser()
PARSER.add_argument("-d", "--dry-run",
            help="Launch script in dry run mode",
            action='store_true',
            default=False)
PARSER.add_argument("-l", "--list-exclude",
            help="List all excludes with ID. (Don't copy any file)",
            action='store_true',
            default=False)
PARSER.add_argument("-a", "--add-exclude",
            help="Add exclude in exclude list (Don't copy any file)",
            metavar='exclude',
            type=str,
            nargs='+')
PARSER.add_argument("-x", "--del-exclude",
            help="Delete all exclude specified (Don't copy any file)",
            metavar='exclude_id',
            type=int,
            nargs='+')
PARSER.add_argument("-L", "--list-include",
            help="List all includes with ID. (Don't copy any file)",
            action='store_true',
            default=False)
PARSER.add_argument("-A", "--add-include",
            help=("Add include in include list. "
                  "Is take before an exclude (Don't copy any file)"),
            metavar='include',
            type=str,
            nargs='+')
PARSER.add_argument("-X", "--del-include",
            help="Delete all include specified (Don't copy any file)",
            metavar='include_id',
            type=int,
            nargs='+')
PARSER.add_argument("-s", "--source",
            help="Source directory to get videos",
            type=str,
            required=True)
PARSER.add_argument("-t", "--target",
            help="Target directory where you want copy your videos",
            type=str,
            required=True)
ARGS = PARSER.parse_args()

DRY_RUN = ARGS.dry_run

if DRY_RUN: logformat = '%(asctime)s %(levelname)s / DRY_RUN! -: %(message)s'
else: logformat =  '%(asctime)s %(levelname)s -: %(message)s'
# Set logger formater
formatter = logging.Formatter(logformat)
hdl = logging.StreamHandler(); hdl.setFormatter(formatter); LOG.addHandler(hdl)



def sync_dir():
    "Sync source dir with dest dir"
    # Launch database connection
    with Db(db_name='sync', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        # For each files
        for dir_path, dirs, files in os.walk(ARGS.source):
            if not files: continue
            # For each files in dir
            for file_name in files:
                # Exemple : -s Video/foo -t dest
                # Give : src = Video/foo : relative = foo : dst = dest/foo
                dir_source      = dir_path
                dir_relative    = re.sub(r'%s/?' % ARGS.source,'', dir_source)
                dir_dest        = join(ARGS.target, dir_relative)
                file_source     = join(dir_source, file_name)
                file_relative   = join(dir_relative, file_name)
                file_dest       = join(dir_dest, file_name)
    
                if db.get(file_relative) is None:
                    if is_include(file_relative) \
                    or not is_exclude(file_relative):
                        create_dir(dir_dest, dry_run=DRY_RUN)
                        copy_file(file_source, file_dest, dry_run=DRY_RUN)
                        if check_file_consistency(file_source, file_dest, dry_run=DRY_RUN):
                            db.save(file_relative, 'unused')
                        else:
                            LOG.critical("Error file is not consistent "
                                         "the sum don't match")
    
        # Clean empty dir after sync
        remove_empty_dir(ARGS.target, dry_run=DRY_RUN)
    #print db.get_all()
    #db.flush_all()

def add_exclude():
    "Add an exclude dir filter"
    # Launch database connection
    with Db(db_name='exclude', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for exclude in ARGS.add_exclude:
            db.save(exclude)

def del_exclude():
    "Del an exclude"
    # Launch database connection
    with Db(db_name='exclude', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for exclude_id in ARGS.del_exclude:
            db.remove(exclude_id)

def list_exclude():
    "List all excludes"
    # Launch database connection
    with Db(db_name='exclude', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        print 'Excludes :'
        for key, exclude in enumerate(db.get_all()):
            print '  - %s : "%s"' % (key, exclude)

def is_exclude(line):
    "Check if file match exclude"
    with Db(db_name='exclude', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for exclude in db.get_all():
            if re.search(exclude, line):
                return True
        return False

def add_include():
    "Add an include dir filter"
    # Launch database connection
    with Db(db_name='include', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for include in ARGS.add_include:
            db.save(include)

def del_include():
    "Del an include"
    # Launch database connection
    with Db(db_name='include', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for include_id in ARGS.del_include:
            db.remove(include_id)

def is_include(line):
    "Check if file match include"
    with Db(db_name='include', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        for include in db.get_all():
            if re.search(include, line):
                return True
        return False

def list_include():
    "List all includes"
    # Launch database connection
    with Db(db_name='include', db_type='list', db_file='%s/db.json' % ARGS.target, dry_run=DRY_RUN) as db:
        print 'Includes :'
        for key, include in enumerate(db.get_all()):
            print '  - %s : "%s"' % (key, include)

if __name__ == "__main__":

    # Create target dir
    create_dir(ARGS.target, dry_run=DRY_RUN)
    # List exclude
    if ARGS.list_exclude:
        list_exclude()
    # List include
    elif ARGS.list_include:
        list_include()
    # Add exclude
    elif ARGS.add_exclude:
        add_exclude()
    # Del exclude
    elif ARGS.del_exclude:
        del_exclude()
    # Add include
    elif ARGS.add_include:
        add_include()
    # Del include
    elif ARGS.del_include:
        del_include()
    # Sync
    else:
        sync_dir()


# WALK
    #import hashlib
    #for dirnpath, dirnames, filenames in os.walk('Videos'):
        #print dirnpath, filenames
        #if not filenames: continue
        #print [(fname, hashlib.md5(open('%s/%s' % (dirnpath, fname), 'rb').read()).digest()) for fname in filenames]
# Copy with progress http://stackoverflow.com/questions/274493/how-to-copy-a-file-in-python-with-a-progress-bar

# DATABASE
#    with Db(db_file='/tmp/db.json') as db:
#        db.save('key', 'value')
#        print db.get('key')
#        print db.get_all()
