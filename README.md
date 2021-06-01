# zman - a ZOIA Patch Manager

## Overview
zman is a small Python command line utility that helps simplify getting properly named ZOIA patch files onto an SD card. It will read available patches from a directory and build a JSON config for them. Using a config, patches can be assigned numbers, otherwise they will be renumbered to guarantee uniqueness.

I know there's a nice librarian app, but I wanted something small and dumb that would make it easy to move downloaded files onto an SD card without having to rename files myself.

## Usage
### Creating a config from patches in ./patches
```
$ zman/zman.py create_config
The file 'zoia_patches.conf' already exists. Overwrite? y/[n] y
Wrote patch config to zoia_patches.conf.
```
### Update the config
By default, all patches are active and there's no preferred index numbers set. Just edit the file to set one for a patch
```
    {
        "active": true,
        "file_name": "020_zoia_Really_Cookin.bin",
        "full_path": "./patches/020_zoia_Really_Cookin.bin",
        "name": "Really_Cookin.bin",
        "preferred_index": 13
    },
```
### Creating a config from ./patches, but keep customizations from the existing config
```
$ zman/zman.py create_config -i zoia_patches.conf
Wrote patch config to zoia_patches.conf.
```
### Copying patches to a directory
```
$ zman/zman.py copy_files -d /Volumes/SDCard/to_zoia
```

