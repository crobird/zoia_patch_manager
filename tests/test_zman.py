#!/usr/bin/env python

import os
import sys
import json
import glob
import pytest
import tempfile

import zman

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PATCHES_DIR = os.path.join(SCRIPT_DIR, "patches")
RESOURCE_DIR = os.path.join(SCRIPT_DIR, "resources")


@pytest.fixture
def patches_from_dir():
    return zman.get_patch_files(PATCHES_DIR)


@pytest.fixture
def old_config_patches():
    patches = zman.get_patch_files(PATCHES_DIR)
    for p in patches:
        if p.name == 'barfoo.bin':
            p.active = False
        elif p.name == 'barbar.bin':
            p.preferred_index = 60
    return patches


def test_get_patch_files(patches_from_dir):
    """
    Verifies that all ZOIA bin files are parsed, even with conflicting index numbers.
    """
    all_files = glob.glob(os.path.join(PATCHES_DIR, '*.bin'))
    assert len(all_files) == len(patches_from_dir)


def test_get_patch_files_from_config():
    """
    Verifies reading patches from a config file.
    """
    patches = zman.get_patch_files_from_config(os.path.join(RESOURCE_DIR, "read_from_config.json"))

    assert len(patches) == 3
    assert sum(p.active == False for p in patches) == 1
    assert sum(p.preferred_index == 60 for p in patches) == 1


def test_merge_patch_files(patches_from_dir, old_config_patches):
    """
    Verifies that merging of patch objects works correctly.
    """
    merged = zman.merge_patch_files(patches_from_dir, old_config_patches)

    assert sum(p.active == False for p in merged) == 1
    assert sum(p.preferred_index == 60 for p in merged) == 1


def test_create_config(patches_from_dir):
    """
    Verifies writing patches to a JSON file.
    """
    tmp_config_path = os.path.join(RESOURCE_DIR, 'tmp_config.json')

    if os.path.isfile(tmp_config_path):
        os.remove(tmp_config_path)

    zman.create_config(patches_from_dir, tmp_config_path)

    with open(tmp_config_path, "r") as fh:
        raw = fh.read()
        stuff = json.loads(raw)

    assert len(stuff)
    assert len(stuff) == len(patches_from_dir)
    os.remove(tmp_config_path)


def test_copy_and_delete(old_config_patches):
    """
    Verifies patch files can get copied to a dir with proper rules enforced. Also verifies deletion works.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        zman.copy_files(old_config_patches, tmpdir)
        dir_list = glob.glob(os.path.join(tmpdir, '*.bin'))
        assert len(dir_list) == sum(p.active == True for p in old_config_patches)
        assert sum('/060_zoia_' in f for f in dir_list) == 1

        zman.delete_files_in_dir(tmpdir)
        dir_list = glob.glob(os.path.join(tmpdir, '*.bin'))
        assert not len(dir_list)

