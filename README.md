# The Simple OBJ Exporter for Maya
![Screenshot of the Simple OBJ Exporter tool user interface in Maya](https://i.imgur.com/eqXTn9T.png)

A very simple tool for one-click exporting OBJs.

## Compatibility
Tested with Maya:	
- 2022
- 2020
- 2019.2
- 2018.6

## Installation
1. Download the latest **Source code zip** from [Releases](https://github.com/furlerer/simple-obj-exporter/releases)

2. Ensure Maya is **closed**.

3. Head to your Maya versions config folder, which on Windows is typically `"C:/Users/<username>/Documents/maya/<version>"`. We will copy the included files to sub-folders of this folder.

4. From the included `scripts` folder, copy both .py files to your `scripts` folder (in the above location).

5. From the included `prefs/shelves` folder, copy the .mel file to your `prefs/shelves` folder.

6. From the included `prefs/icons` folder, copy the two .png files to your `prefs/icons` folder.

7. Launch Maya. You should now have a new shelf labeled **'ObjExportImport'**.


8. _(Optional)_ Use middle-mouse click-and-drag on the shelf icon to move the shelf buttons to your preferred custom shelf, if you use one. After, you can safely delete the now empty shelf with the Shelf Editor.

## Usage

### Exporting
> **WARNING:** Remember that the exporter will overwrite files without prompting for permission, because it is designed for moving data quickly between programs, and **not** for final exports of completed work.

- The exporter has two modes: _single_ and _batch_, and how many objects you have selected dictates which one is used.

- Simply select the objects you wish to export and click on the Export shelf button.

- On the first export of your Maya session, you will be prompted to set the export paths for single and multi, plus any other options you wish to use.

- On subsequent clicks of the Export shelf button, objects will be immediately exported, potentially overwriting previous exports if they have the same name, allowing for very fast iteration and exporting to other DCC apps.

- You can bring up the options panel anytime by double-clicking on the Export shelf button.

- Currently, a set of custom attributes are saved onto the node in the scene so the options will persist between work sessions on the same scene, but options can be updated at any time via double-clicking the Export shelf button.  

### Importing
- The importer is quite a bit less featured at the moment (maybe _forever_), but allows you to set an OBJ file (or set of OBJ files) that can be immediately imported into the scene, allowing for fast imports and iteration from other DCC apps.

- Simply click the Import shelf button to use. On first click, you will be prompted to select the OBJ file(s) to import, but subsequent clicks will just pull in that same file (which has been presumably overwritten by the other DCC apps being used).
- You can bring up the import path dialog at any time by double-clicking on the Import shelf button (it will then immediately import the new selected file(s)).


## History
I first released this tool via my [Gumroad](https://jamesfurler.gumroad.com/l/Zvdg) in 2020, but have since moved away from using Maya as my main DCC. As I will find it very difficult to continue supporting the tool, I've moved it to the MIT License and hosting it here on Github for anyone to update, improve, or do as they wish with :)

## License
[MIT](https://github.com/furlerer/simple-obj-exporter/blob/main/LICENSE)