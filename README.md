# The Simple OBJ Exporter for Maya
![Screenshot of the Simple OBJ Exporter tool user interface in Maya](https://raw.githubusercontent.com/furlerer/simple-obj-exporter/refs/heads/main/soe_cover.png)

A very simple tool for one-click exporting (and importing) OBJs.

## Compatibility
Tested on Windows 11 with Maya:	
- 2025
- 2024

## Installation
1. Download the latest or most appropriate for your Maya version **Source code zip** from [Releases](https://github.com/furlerer/simple-obj-exporter/releases)

2. Ensure Maya is **closed**.

3. Head to your Maya config folder, which on Windows is typically `"C:/Users/<username>/Documents/maya/"`. There should be a folder per version of Maya (`2024`, `2025`, etc).

4. _Fastest_ is to select both `scripts` and `prefs` folders and drag onto the version folder, this will copy the files and merge them with existing folders if the exist.

5. Or to copy manually, 
    
    - From the included `scripts` folder, copy both .py files to your `<version>/scripts` folder.

    - From the included `prefs/shelves` folder, copy the .mel file to your `<version>/prefs/shelves` folder.

    - From the included `prefs/icons` folder, copy the two .png files to your `<version>/prefs/icons` folder.

6. Launch Maya. You should now have a new shelf labeled **'ObjExportImport'**.

7. _(Optional)_ Use middle-mouse click-and-drag on the shelf icon to move the shelf buttons to your preferred custom shelf, if you use one. After, you can safely delete the now empty shelf with the Shelf Editor.

## Usage

### Exporting
> **WARNING:** Remember that the exporter will overwrite files without prompting for permission, because it is designed for moving data quickly between programs, and **not** for final exports of completed work.

- The Export shelf button will perform slightly different functions based on what you have selected:
    - **No selection**: Opens the settings window (equal to double-clicking the shelf button)
    - **Single selection**: Exports selected mesh to the path specified by "Single OBJ export"
    - **Multiple selection**: 
        - Either export each mesh to a separate OBJ file located in the path specified by "Batch OBJ export", or 
        - Combine selected into a single mesh object and export to the path specified by "Single OBJ export", if "Combine Meshes" is enabled.


- To open the Options pane, simply double-click on the Export shelf button.

- Each subsequent click of the Export shelf button will immediately export the selection, overwriting previous exports if they have the same name, allowing for very fast iteration and exporting to other DCC apps.


### Importing
- The importer is quite a bit less featured at the moment (probably _forever_), but allows you to set an OBJ file (or set of OBJ files) that can be immediately imported into the scene, allowing for fast imports and iteration from other DCC apps.

- Simply click the Import shelf button to use. On first click, you will be prompted to select the OBJ file(s) to import, but subsequent clicks will just pull in that same file (which has been presumably overwritten by the other DCC apps being used).

- You can bring up the import path dialog at any time by double-clicking on the Import shelf button (it will then immediately import the new selected file(s)).

## Options
### Export Options
Each of the following export options are non-destructive - ie. they will leave the current mesh selected untouched.

#### Ask path before every export
If you wish for the tool to present the file dialog to choose a path each time Export is clicked. Sets .obj file path for single or combined selections, and directory paths for multiple selections (batch .obj file names will always match to the mesh name in Maya)

#### Triangulate Mesh
If the mesh(es) should be triangulated by Maya during export.

#### Move to origin
If the mesh(es) should be offset such that their pivot point is at the world origin `(0,0,0)` during export.

#### Combine Meshes
If selections of multiple meshes should be combined into one mesh for export to the standard path, or left to be exported separately to the Batch directory path.

### Tools Options

#### Native OS Browser & Maya File Browser
Choose which style of file browser dialog should be used. Handy if for example, you have set up favourite folders through your OS.

### Load/Save Defaults
The default settings of the tool are now stored in a small JSON file in the user prefs directory (alongside the .py file), to enable you to set your own defaults you wish for each time the tool is launched in a new Maya scene for the first time.

Note that the tool saves it's settings in the scene, so the defaults from the JSON are really only used when a new scene is created, or you choose to load them with the Load Defaults button.

## History
I first released this tool via my [Gumroad](https://jamesfurler.gumroad.com/l/Zvdg) in 2020, but have since moved away from using Maya as my main DCC. As I will find it very difficult to continue supporting the tool, I've moved it to the MIT License and hosting it here on Github for anyone to update, improve, or do as they wish with :)

## License
[MIT](https://github.com/furlerer/simple-obj-exporter/blob/main/LICENSE)