# pyslapi
Python bindings for the official Sketchup API and an importer for blender based on them


## Installing the Addon in Blender

### Method 1: Direct Installation (Recommended)
1) Download the latest release from [the releases page](https://github.com/martijnberger/pyslapi/releases)
2) Start Blender
3) From the top menu, choose: **Edit > Preferences...**
4) Click on the **Add-ons** tab
5) Click on the **Install...** button
6) Browse to and select the downloaded zip file (e.g., `sketchup_importer_X.XX.zip`)
7) Click **Install Add-on**
8) In the add-ons list, search for "Sketchup"
9) Enable the add-on by clicking the checkbox next to **Import-Export: Sketchup importer**
10) Click **Save Preferences** to keep the add-on enabled for future Blender sessions

### Method 2: Manual Installation
1) Download the latest release zip file
2) Unpack the zip file into Blender's addons folder:
   - Windows: `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons`
   - macOS: `~/Library/Application Support/Blender/[version]/scripts/addons`
   - Linux: `~/.config/blender/[version]/scripts/addons`
3) Restart Blender and enable the add-on as described in steps 3-10 above

## Using the Addon
Once installed and enabled, you can import Sketchup files (.skp) by:
1) From Blender's top menu, choose: **File > Import > Import Sketchup Scene (.skp)**
2) Navigate to and select your .skp file
3) Adjust import settings if needed and click **Import Sketchup Scene**

## Compatibility
The latest version of the importer is compatible with:
- Blender 4.x
- Python 3.11
- Various versions of SketchUp files up to and including version 2025.1

For older versions of Blender, check the specific release notes on the [releases page](https://github.com/martijnberger/pyslapi/releases).

## Version 0.25 Improvements

This version incorporates significant improvements by [Peter Kirkham](https://pkirkham.github.io/blog/importing-from-sketchup-into-blender/) that address several critical issues with the SketchUp importer:

- **Preserved Hierarchy Structure**: Maintains the original SketchUp model hierarchy in Blender's outliner
- **Improved Nested Components**: Fixed issues with nesting of groups and components
- **Name Recognition Fix**: Solved problems with objects sharing the same name not being recognized as separate entities
- **Transformation Corrections**: Fixed transformations not being correctly applied to groups containing both nested loose mesh data and groups

As noted by Peter Kirkham in his August 2022 update:
> "I've continued to work on the import script and have solved the issues with nesting of groups and components. The issue turned out to be related to a mix of objects with the same name not being recognised as separate entities, and with transformations not being correctly applied to groups containing both nested loose mesh data and groups. These problems have been fixed and the importer is now a lot more robust."

**Note about complex transformations**: There may still be occasional import issues with groups that have multiple transformations applied. If you encounter problems, try exploding and re-grouping the geometry in SketchUp to reset the transformations before importing.

## Features Not Yet Implemented

### Platform Support
- **Linux Support**: Not available due to limitations in the SketchUp SDK which doesn't provide Linux libraries.

### Import Options
- **Line-Only Import**: Future feature to import only line geometry without faces.



## Build Info

### OSX Build
1) Install Python3 from Python website (python.org)
2) Install Cython from shell:
   ```
   pip3 install Cython --install-option="--no-cython-compile"
   ```
   (replace by pip if needed)

3) Download Sketchup SDK https://extensions.sketchup.com/sketchup-sdk

#### BUILD
1) Copy LayOutAPI.framework and SketchUpAPI.framework from SDK directory to pyslapi

2) Build OSX version
   ```
   uv venv 
   python3 setup.py build_ext --inplace
   ```

3) Run the two last lines of setup script manually:
   ```
   install_name_tool -change @rpath/SketchUpAPI.framework/Versions/Current/SketchUpAPI @loader_path/SketchUpAPI.framework/Versions/Current/SketchUpAPI sketchup.cpython-311-darwin.so
   install_name_tool -change @rpath/SketchUpAPI.framework/Versions/A/SketchUpAPI @loader_path/SketchUpAPI.framework/Versions/A/SketchUpAPI sketchup.cpython-311-darwin.so
   sudo xattr -r -d com.apple.quarantine SketchUpAPI.framework
   ```

#### INSTALL
1) Copy the following files from pyslapi to SketchUp_Importer
  - LayOutAPI.framework
  - SketchUpAPI.framework
  - sketchup.cpython-311-darwin

2) Rename sketchup.cpython-311-darwin.so to sketchup.so

3) Look the addon in Blender and enable it

