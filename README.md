Import OpenCTM (.ctm)
====================

This Blender plugin allows you to import files in OpenCTM format.

## Usage

- To import: File > Import > OpenCTM (.ctm)

**Note** Model might be scaled in weird way when imported, make sure to scale it to viewport size after importing it


## Dev notes

Blender 4.2.0 uses python 3.11 specifically, so use that to install bpy and create a virtualenv for if you want to have IDE autocompletions and such:
```
python3.11 -m venv venv
venv/bin/pip install bpy blender-stubs
```

Build the addon .zip file:
```
blender --command extension build
```

Install dev build:
* Blender > Edit > Preferences > Add-Ons > Install from disk > .zip file