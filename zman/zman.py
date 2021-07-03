#!/usr/bin/env python

"""
This is a small script to help manage patches for the ZOIA.

It has a few distinct actions that it supports:

    create_config - Reads a directory full of zoia patches and generates a JSON config file for them.
                    A config defines which patches are "active" meaning they'd be copied to an SD card
                    and if there's a preferred index for that patch.

    config_stats - Parses a config file and report back with some basic stats, such as number of active patches.

    copy_files - Given a config file, copies patches to a specified location (probably your SD card). After patches
                 with preferred numbers are accounted for, the rest of the patches will be assigned numbers.
                 Because of this, the default numbers from the downloaded patches can conflict and they will just
                 get resolved at copy time. 

"""
import os
import re
import json
import argparse
from collections import deque
from dataclasses import dataclass
from typing import Optional
from shutil import copyfile

DEFAULT_PATCH_DIR = "./patches"
DEFAULT_DESTINATION_PATCH_DIR = "/Volumes/ZOIA/to_zoia"
DEFAULT_CONFIG = "zoia_patches.conf"
ACTION_CREATE_CONFIG = "create_config"
ACTION_COPY_FILES = "copy_files"
ACTION_CONFIG_STATS = "config_stats"

@dataclass
class PatchFile:
    full_path: str
    file_name: str
    name: str
    active: bool = True
    preferred_index: Optional[int] = None

    def __repr__(self):
        return json.dumps(self.config())

    def config(self):
        return dict(
            name=self.name,
            full_path=self.full_path,
            file_name=self.file_name,
            active=self.active,
            preferred_index=self.preferred_index,
        )


def get_patch_files(patch_dir):
    """
    Reads all matching patch files from a directory, returning a list of PatchFile objects.

    Args:
        patch_dir (str): Path to the directory of patches.

    Returns:
        [PatchFile]: List of PatchFile objects for each file found.
    """
    files = os.listdir(patch_dir)
    patch_files = []
    for f in files:
        if not f.endswith('.bin'):
            continue
        name = re.sub(r'^\d\d\d_zoia_', '', f)
        patch_files.append(PatchFile(full_path=os.path.join(patch_dir, f), file_name=f, name=name))
    return patch_files


def merge_patch_files(patch_files, override_patch_files):
    """
    Replaces PatchFile objects in list with preferred ones, if present in override list.

    Args:
        patch_files ([PatchFiles]): List of main PatchFile objects.
        override_patch_files ([PatchFiles]): List of override PatchFile objects.

    Returns:
        [PatchFiles]): List of PatchFile objects.
    """
    override_paths = {x.full_path:x for x in override_patch_files}
    get_pf = lambda pf: override_paths[pf.full_path] if pf.full_path in override_paths else pf
    return list(map(get_pf, patch_files))


def create_config(patch_files, file_name):
    """
    Writes out a new config file, given a list of PatchFile objects.

    Args:
        patch_files ([PatchFiles]): List of PatchFile objects to use.
        file_name (str): File name for config to write out.
    """
    with open(file_name, "w") as fh:
        fh.write(json.dumps([pf.config() for pf in patch_files], indent=4, sort_keys=True))

    print(f"Wrote patch config to {file_name}.")


def get_patch_files_from_config(config_path):
    """
    Parses a config file and returns PatchFile objects.

    Args:
        config_path (str): Path to a config file to read.

    Returns:
        [PatchFile]: List of PatchFile objects.
    """
    with open(config_path, "r") as fh:
        txt = fh.read()
        try:
            patch_files = [PatchFile(**x) for x in json.loads(txt)]
        except Exception as e:
            print(f"Unable to parse config JSON: {e}")
            exit(1)
    return patch_files


def print_patch_files(patch_files):
    """
    Prints out PatchFile object info.

    Args:
        patch_files ([PatchFiles]): List of PatchFile object to print.
    """
    for pf in patch_files:
        print(pf)

def get_preferred_index_patches(patch_files):
    index_map = {}
    for patch_file in patch_files:
        if patch_file.preferred_index:
            if not patch_file.preferred_index in index_map:
                index_map[patch_file.preferred_index] = []
            index_map[patch_file.preferred_index].append(patch_file.name)
    return index_map

def config_stats(config_path, patch_dir):
    """
    Prints stats about the patches in a config.

    Args:
        config_path (str): Path to a config file.
    """
    patch_files = get_patch_files_from_config(config_path)
    total_patches = len(patch_files)
    active_patches = len([x for x in patch_files if x.active])
    preferred_index_patches = get_preferred_index_patches(patch_files)
    preferred_index_patch_count = sum([len(preferred_index_patches[i]) for i in preferred_index_patches])

    preferred_index_strs = []
    for i in sorted(preferred_index_patches.keys()):
        conflict_char = '*' if len(preferred_index_patches[i]) > 1 else ' '
        for p in preferred_index_patches[i]:
            preferred_index_strs.append(f"\t{conflict_char}[{i}] {p}")
    preferred_index_str = "\n".join(preferred_index_strs)

    print(f"""
    {config_path}

    total patches: {total_patches}
    active patches: {active_patches}

    patches with preferred index: {preferred_index_patch_count}
    {preferred_index_str}
    """)






def delete_files_in_dir(dest_dir, verbose=False):
    """
    Deletes the files in a requested dir.

    Args:
        dest_dir (str): Directory to delete files in.
        verbose (bool): If set, prints additional information. Defaults to False.
    """
    if verbose:
        print(f"Deleting files in {dest_dir}.")
    for f in os.listdir(dest_dir):
        if f.startswith('.'):
            continue
        full_path = os.path.join(dest_dir, f)
        if verbose:
            print(f"\t{full_path}")
        os.remove(full_path)

def copy_files(patch_files, dest_dir, verbose=False):
    """
    Copies patches to a destination directory.

    Args:
        patch_files ([PatchFiles]): List of PatchFile objects copy.
        dest_dir (str): Path to the directory to copy patches.
        verbose (bool): If set, will provide more verbose output. Default is False.
    """
    patch_order = [None]*64
    unordered_patches = deque()

    page_size = 64
    count = 1
    for pf in patch_files:
        if count > page_size:
            print(f"Hit patch limit of {page_size}. Multiple pages not supported yet.")
            break
        if not pf.active:
            if verbose:
                print(f"Skipping {pf['name']}.")
            continue
        if pf.preferred_index is not None and patch_order[pf.preferred_index] is None:
            patch_order[pf.preferred_index] = pf
        else:
            unordered_patches.append(pf)
        count += 1

    for i in range(page_size):
        if not unordered_patches:
            break
        if not patch_order[i]:
            patch_order[i] = unordered_patches.popleft()

    for i in range(page_size):
        pf = patch_order[i]
        if not pf:
            continue
        copy_path = os.path.join(dest_dir, f"{i:03}_zoia_{pf.name}")
        copyfile(pf.full_path, copy_path)
        if verbose:
            print(f"Created {copy_path}")


def main(args):
    if args.action == ACTION_CREATE_CONFIG:
        patch_files = get_patch_files(args.patch_dir)
        if args.input_config and not os.path.isfile(args.input_config):
            print(f"Input config ({args.input_config}) is not a file. Bailing.")
            exit(1)
        elif args.input_config:
            baseline_patch_files = get_patch_files_from_config(args.input_config)
            patch_files = merge_patch_files(patch_files, baseline_patch_files)
        elif os.path.isfile(args.output_config) and args.output_config != args.input_config and not args.force:
            response = input(f"The file '{args.output_config}' already exists. Overwrite? y/[n] ")
            if response.strip().lower() not in ['y', 'yes']:
                print("Nothing done.")
                exit(1)
        create_config(patch_files, args.output_config)

    elif args.action == ACTION_COPY_FILES:
        if os.path.isdir(args.dest_dir):
            if not args.force:
                response = input(f"Going to deleted existing files in {args.dest_dir}. Okay? y/[n] ")
                if response.strip().lower() not in ['y', 'yes']:
                    print("Nothing done.")
                    exit(1)
            delete_files_in_dir(args.dest_dir, verbose=args.verbose)
        else:
            os.makedirs(args.dest_dir)
        patch_files = get_patch_files_from_config(args.config)
        copy_files(patch_files, args.dest_dir, verbose=args.verbose)

    elif args.action == ACTION_CONFIG_STATS:
        config_stats(args.config, args.patch_dir)

    else:
        print("Error: Invalid or missing action")
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help="More verbose output, if possible", default=False, action="store_true")
    subparsers = parser.add_subparsers(help='Action', dest="action", required=True)

    parser_create_config = subparsers.add_parser(ACTION_CREATE_CONFIG, help="Create a config from ZOIA patch files")
    parser_create_config.add_argument('-p', '--patch_dir', help=f'Patch dir (default: {DEFAULT_PATCH_DIR})', default=DEFAULT_PATCH_DIR)    
    parser_create_config.add_argument('-o', '--output_config', help=f"Output config file (default: {DEFAULT_CONFIG})", default=DEFAULT_CONFIG)
    parser_create_config.add_argument('-i', '--input_config', help=f"Input config file")
    parser_create_config.add_argument('-f', '--force', help="Force overwriting config without prompt", default=False, action="store_true")
    parser_create_config.set_defaults(func=create_config)

    parser_copy_files = subparsers.add_parser(ACTION_COPY_FILES, help="Copy patch files to a destination folder")
    parser_copy_files.add_argument('-d', '--dest_dir', help=f'Destination patch dir (default: {DEFAULT_DESTINATION_PATCH_DIR})', default=DEFAULT_DESTINATION_PATCH_DIR)    
    parser_copy_files.add_argument('-c', '--config', help=f"Config file (default: {DEFAULT_CONFIG})", default=DEFAULT_CONFIG)
    parser_copy_files.add_argument('-f', '--force', help="Force deleting of patch_dir without prompt", default=False, action="store_true")
    parser_copy_files.set_defaults(func=copy_files)

    parser_config_stats = subparsers.add_parser(ACTION_CONFIG_STATS, help="Provide some stats about a config file")
    parser_config_stats.add_argument('-c', '--config', help=f"Config file (default: {DEFAULT_CONFIG})", default=DEFAULT_CONFIG)
    parser_config_stats.add_argument('-p', '--patch_dir', help=f'Patch dir (default: {DEFAULT_PATCH_DIR})', default=DEFAULT_PATCH_DIR)    
    parser_config_stats.set_defaults(func=config_stats)

    args = parser.parse_args()
    main(args)

