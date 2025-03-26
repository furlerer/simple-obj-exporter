"""
-------------------------------------------------------------------
A (very very) Simple OBJ Importer for Maya

Version 1.02 - Fixed bug where Canceling options caused mesh to reimport
        1.01 - Added ability to select multiple files to Import
        1.0 - First release 2019_10_30

Tested with Maya 2020, 2019.2, 2018.6

By James Furler, 2020
Contact: furlerjames@gmail.com

Free to use for Personal or Commercial usage, but please do not
redistribute or share as your own work.
-------------------------------------------------------------------
"""
import maya.OpenMaya as om
import maya.cmds as cmds


class SimpleObjImporter:
    # Use a class method to create only one instance of this class for persistence
    class_instance = None

    @classmethod
    def shelf_button_clicked(cls):
        if not cls.class_instance:
            cls.class_instance = SimpleObjImporter()

        cls.class_instance.import_objs()

    @classmethod
    def shelf_button_alt_clicked(cls):
        if not cls.class_instance:
            cls.class_instance = SimpleObjImporter()

        cls.class_instance.show_path_dialog()

    def __init__(self):
        # import path option variables
        self.import_path = None

    def import_objs(self):
        # Has the file been set?
        if self.import_path is None:
            self.show_path_dialog()

        # what if the path still hasn't been set (ie user cancelled)?
        if self.import_path is None:
            return

        # Do the actual import
        for i in range(0, len(self.import_path)):
            try:
                cmds.file(self.import_path[i], i=True, type='OBJ', renameAll=True, mergeNamespacesOnClash=True,
                          namespace=':', options='mo=1', importTimeRange='keep')
            except RuntimeError as e:
                om.MGlobal.displayError(('Unable to import OBJ file: {0}'.format(self.import_path[i])))

    def show_path_dialog(self):
        workspace_root = cmds.workspace(query=True, directory=True)
        obj_filter = 'OBJ Files (*.obj);;All Files (*.*)'
        path = cmds.fileDialog2(fileFilter=obj_filter, fileMode=4, dialogStyle=2, startingDirectory=workspace_root,
                                caption='Set OBJ file import path...')

        if path is not None:
            self.import_path = path
