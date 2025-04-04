"""
MIT License
Copyright (c) 2020-2025 James Furler

-------------------------------------------------------------------
A Simple OBJ Batch Exporter for Maya

Version 1.10 - Updated for Python 3, added Dialog style switch, object attrs
Version 1.03 - Fix for filenames with | symbols
Version 1.0 - First release 2019_10_30

Tested with Maya 2022, 2020, 2019.2, 2018.6
-------------------------------------------------------------------
"""
import os
import json

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets
from shiboken2 import wrapInstance

import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.cmds as cmds

def maya_main_window():
    # Return the Maya main window as a python object
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def clean_filename(filename):
    """
    Does a basic strip and replace so a Maya node can easily become a filename.
    Maya does a decent job for us already by only allowing alphanum and ':' and "_"
    :param str filename: The string to be cleaned
    :return str: The cleaned string
    """
    # Check for leading or trailing symbols
    filename = filename.strip(' :|')

    # Check for symbols in the string
    filename = filename.replace(':', '_')
    filename = filename.replace('|', '_')
    return filename


def set_attr(mesh, short_name, long_name, attr_type, value):
    """
    Static helper method for setting a Maya attribute. Checks if attribute exists, adds it if not,
    and goes on to set the value.
    :param mesh: The Maya node to add the attribute to
    :param short_name: Attribute's Maya short name
    :param long_name: Attribute's Maya Long name
    :param attr_type: The attribute's type (string, bool, etc)
    :param value: The value to set the attribute to
    :return:
    """
    # Add attribute to mesh (and catch if already added error)
    cmds.select(mesh, replace=True)
    try:
        if cmds.listAttr(userDefined=True, visible=True) is None or \
                long_name not in cmds.listAttr(userDefined=True, visible=True):
            # Maya needs slightly different arguments depending on type
            if attr_type == 'string':
                cmds.addAttr(shortName=short_name, longName=long_name, dataType=attr_type)
            elif attr_type == 'bool':
                cmds.addAttr(shortName=short_name, longName=long_name, attributeType=attr_type)
    except RuntimeError as e:
        pass

    # set the attribute
    if attr_type == 'string' and value is not None:
        cmds.setAttr('{0}.{1}'.format(mesh, short_name), value, type='string')

    elif attr_type == 'bool':
        cmds.setAttr('{0}.{1}'.format(mesh, short_name), value)


def get_attr(mesh, short_name):
    """
    Static helper method for attempting to get a attributes value from a Maya node
    :param mesh: The Maya node that contains attribute
    :param short_name: The attribute's short name
    :return: The attribute's value if exists, None if does not exist
    """
    try:
        return cmds.getAttr('{0}.{1}'.format(mesh, short_name))
    except ValueError as e:
        return None


def show_file_dialog(dialog_mode, dialog_style):
    """
    Static helper function to display the Maya file dialog based on users styler selection
    :param dialog_style: 1 Native OS style, 2 Maya style
    :param dialog_mode: 0 Any file, existing or not, 3 Name of a directory
    :return: The string list output by maya's cmd.fileDialog2 command
    """
    workspace_root = cmds.workspace(query=True, directory=True)
    if dialog_mode == 0:
        obj_filter = 'OBJ Files (*.obj);;All Files (*.*)'
        return cmds.fileDialog2(fileFilter=obj_filter, fileMode=0, dialogStyle=dialog_style,
                                startingDirectory=workspace_root, caption='Set OBJ export path...')
    # else
    return cmds.fileDialog2(fileMode=3, dialogStyle=dialog_style, startingDirectory=workspace_root,
                            okCaption='Select', caption='Set batch OBJ export path...')


class SimpleObjExporter:
    # Use a class method to create only one instance of this class for persistence
    class_instance = None

    @classmethod
    def shelf_button_clicked(cls):
        if not cls.class_instance:
            cls.class_instance = SimpleObjExporter()

        cls.class_instance.export_selected()

    @classmethod
    def shelf_button_alt_clicked(cls):
        if not cls.class_instance:
            cls.class_instance = SimpleObjExporter()

        cls.class_instance.show_options()

    def __init__(self):
        """ Constructor Method """
        # create and connect a persistent options window
        self.options_popup = OptionsPopup()
        self.options_popup.accepted.connect(self.options_accepted)

        self.current_selection = None
        """
        # Export path option variables
        self.export_path = None
        self.batch_export_path = None

        # General export option variables
        self.always_ask = False
        self.triangulate_mesh = False
        self.move_to_origin = False

        # Tool options
        self.use_native_style = False

        # OBJ specific export options
        self.obj_groups = True
        self.obj_ptgroups = True
        self.obj_materials = True
        self.obj_smoothing = True
        self.obj_normals = True
        """

        self.params = {
            'export_path' : None,
            'batch_export_path' : None,
            'always_ask' : False,
            'triangulate_mesh' : False,
            'move_to_origin' : False,
            'use_native_style' : False,
            'obj_groups' : True,
            'obj_ptgroups' : True,
            'obj_materials' : True,
            'obj_smoothing' : True,
            'obj_normals' : True
        }

        self.load_defaults_json()

    def load_defaults_json(self):
        """
        Check the users Scripts directory for a soe_defaults.json, and init class values off this
        If it doesn't exist (ie. very first run on this comp), create it!
        """
        defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soe_defaults.json')
        if not os.path.exists(defaults_path):
            print('SimpleObjExporter: No existing defaults json file, creating...')
            with open(defaults_path, 'w') as fw:
                json.dump(self.params, fw, indent = 4)

        else:
            print('SimpleObjExporter: Reading defaults json file...')
            with open(defaults_path, 'r') as fr:
                self.params = json.load(fr)

    def export_selected(self):
        """
        Runs simple checks that correct node/s have been selected, and calls export methods based on qty selected
        """
        selection = cmds.ls(sl=True, type='transform')

        if len(selection) <= 0:
            om.MGlobal.displayError('Please select at least one mesh to be exported')
            return

        elif len(selection) == 1:
            shape_nodes = cmds.listRelatives(selection[0], shapes=True)
            if shape_nodes is not None:
                self.current_selection = selection[0]
                self.single_export()
            else:
                om.MGlobal.displayError('"{}" is not a mesh. Please select only meshes to be exported'
                                        .format(selection[0]))
                return

        elif len(selection) > 1:
            for i in range(0, len(selection)):
                shape_nodes = cmds.listRelatives(selection[i], shapes=True)
                if shape_nodes is None:
                    om.MGlobal.displayError('"{}" is not a mesh. Please select only meshes to be exported'
                                            .format(selection[i]))
                    return

            # is success
            self.current_selection = selection
            self.batch_export()

    def show_options(self):
        """
        Sets the fields of the option dialog instance based on the current class values, and shows option dialog.
        These get set manually each time the options are shown in case a user changed options then hit Cancel
        """
        self.options_popup.file_path_le.setText(self.params['export_path'])
        self.options_popup.batch_path_le.setText(self.params['batch_export_path'])

        self.options_popup.always_ask_cb.setChecked(self.params['always_ask'])
        self.options_popup.triangulate_cb.setChecked(self.params['triangulate_mesh'])
        self.options_popup.move_to_origin_cb.setChecked(self.params['move_to_origin'])

        self.options_popup.dialog_style_native_rb.setChecked(self.params['use_native_style'])
        self.options_popup.dialog_style_maya_rb.setChecked(not self.params['use_native_style'])

        self.options_popup.obj_groups_cb.setChecked(self.params['obj_groups'])
        self.options_popup.obj_ptgroups_cb.setChecked(self.params['obj_ptgroups'])
        self.options_popup.obj_materials_cb.setChecked(self.params['obj_materials'])
        self.options_popup.obj_smoothing_cb.setChecked(self.params['obj_smoothing'])
        self.options_popup.obj_normals_cb.setChecked(self.params['obj_normals'])

        self.options_popup.show()

    def options_accepted(self):
        """
        Saves the values from the options UI to our class variables, if the user clicks accept.
        If the user rejects UI, we don't save these so that next time the UI is launched it still
        uses the previous values.
        """
        if self.options_popup.file_path_le.text() == '':
            self.params['export_path'] = None
        else:
            self.params['export_path'] = self.options_popup.file_path_le.text()

        if self.options_popup.batch_path_le.text() == '':
            self.params['batch_export_path'] = None
        else:
            self.params['batch_export_path'] = self.options_popup.batch_path_le.text()

        self.params['always_ask'] = self.options_popup.always_ask_cb.isChecked()
        self.params['triangulate_mesh'] = self.options_popup.triangulate_cb.isChecked()
        self.params['move_to_origin'] = self.options_popup.move_to_origin_cb.isChecked()

        self.params['use_native_style'] = self.options_popup.dialog_style_native_rb.isChecked()

        self.params['obj_groups'] = self.options_popup.obj_groups_cb.isChecked()
        self.params['obj_ptgroups'] = self.options_popup.obj_ptgroups_cb.isChecked()
        self.params['obj_materials'] = self.options_popup.obj_materials_cb.isChecked()
        self.params['obj_smoothing'] = self.options_popup.obj_smoothing_cb.isChecked()
        self.params['obj_normals'] = self.options_popup.obj_normals_cb.isChecked()

        # self.debug_print()

    def preprocess_mesh(self, mesh):
        """
        Runs Maya commands processing the given mesh based on the options selected
        :param mesh: Name of node to be processed
        :type mesh: str
        """
        # Triangulation
        if self.params['triangulate_mesh']:
            cmds.select(mesh, replace=True)
            cmds.polyTriangulate()

        # Move to origin
        if self.params['move_to_origin']:
            # Use the point constraint method to move to origin
            origin_loc = cmds.group(empty=True, name='temp_loc')
            point_con = cmds.pointConstraint(origin_loc, mesh, maintainOffset=False)
            cmds.delete(point_con)
            cmds.delete(origin_loc)

    def single_export(self):
        """
        Performs a number of checks to make sure the user has set the required values at some point,
        either through the UI or from previous sessions through the object attributes,
        and if so, duplicates, processes, and exports the mesh.
        """
        # has the export path or ask option been set?
        # if not, might be the first run of tool
        if self.params['export_path'] is None and self.params['always_ask'] is False:
            # attempt to load saved attrs from selection
            self.load_attributes(self.current_selection)

            # did loading work? if not, force UI pop-up
            if self.params['export_path'] is None:
                # pop up the options box in modal mode, so user has to enter
                result = self.options_popup.exec_()

                if result == QtWidgets.QDialog.Rejected:
                    # the user didn't set a path, so we can't export
                    om.MGlobal.displayError('Unable to export without Export Path set...')
                    return
                elif result == QtWidgets.QDialog.Accepted:
                    self.options_accepted()

        if self.params['use_native_style']:
            dialog_style = 1
        else:
            dialog_style = 2

        # did the user just change the ask option?
        if self.params['always_ask']:
            file_path = show_file_dialog(0, dialog_style)[0]
        else:
            file_path = self.params['export_path']

        # but what if the user still hasn't set a path? Check one more time
        if file_path is None:
            om.MGlobal.displayError('Unable to export without Export Path set...')
            return

        # if we got here, we're pretty safe
        # Duplicate mesh for safety and processing
        dupe_mesh = cmds.duplicate(self.current_selection, name='{0}_export'.format(self.current_selection))
        self.preprocess_mesh(dupe_mesh)
        cmds.select(dupe_mesh, replace=True)

        try:
            result = cmds.file(file_path, exportSelected=True, type='OBJexport', force=True,
                               options=self.build_obj_options_string())

            om.MGlobal.displayInfo('Successfully exported to {0}'.format(result))

        except RuntimeError as e:
            om.MGlobal.displayError(('Unable to export selected mesh. Check file path and try again. '
                                     '(Maya error output: {0})'.format(e)))

        cmds.delete(dupe_mesh)
        cmds.select(self.current_selection, replace=True)
        # set/update attrs on selection
        self.save_attributes(self.current_selection)
        self.current_selection = None

    def batch_export(self):
        """
        Same checks as single_export(), but instead runs a loop over the selected meshes, building
        the path for each to be exported to, duplicating, processing and exporting the meshes.
        """
        # has the batch export path been set?
        if self.params['batch_export_path'] is None and self.params['always_ask'] is False:
            # attempt to load saved attrs from selection
            self.load_attributes(self.current_selection[0])

            # did loading work? if not, force UI pop-up
            if self.params['batch_export_path'] is None:
                # pop up the options box in modal mode, so user has to enter
                result = self.options_popup.exec_()

                if result == QtWidgets.QDialog.Rejected:
                    # the user didn't set a path, so we can't export
                    om.MGlobal.displayError('Unable to export without Batch Export Path set...')
                    return
                elif result == QtWidgets.QDialog.Accepted:
                    self.options_accepted()

        if self.params['use_native_style']:
            dialog_style = 1
        else:
            dialog_style = 2

        # did the user just change the ask option?
        if self.params['always_ask']:
            batch_dir = show_file_dialog(3, dialog_style)[0]
        else:
            batch_dir = self.params['batch_export_path']

        # but what if the user still hasn't set a path? Check one more time
        if batch_dir is None:
            om.MGlobal.displayError('Unable to export without Batch Export Path set...')
            return

        # we are as safe as possible for now
        obj_options = self.build_obj_options_string()

        export_count = 0
        meshes = self.current_selection
        for i in range(0, len(meshes)):
            # Duplicate mesh for safety, and create file name with no namespace colons
            dupe_mesh = cmds.duplicate(meshes[i], name='{0}_export'.format(meshes[i]))
            # normalise and then replace slashes to appease Maya
            file_path = os.path.normpath(os.path.join(batch_dir, '{0}.obj'.format(clean_filename(meshes[i]))))
            file_path = file_path.replace('\\', '/')
            self.preprocess_mesh(dupe_mesh)
            cmds.select(dupe_mesh, replace=True)

            try:
                cmds.file(file_path, exportSelected=True, type='OBJexport', force=True, options=obj_options)

            except RuntimeError as e:
                om.MGlobal.displayError(('Unable to export selected meshes. Check file path and try again. '
                                         '(Maya error output: {0})'.format(e)))
                cmds.delete(dupe_mesh)
                continue

            cmds.delete(dupe_mesh)
            export_count += 1
            # set/update attrs on mesh
            self.save_attributes(meshes[i])

        # but if we finished for all the meshes
        om.MGlobal.displayInfo('Successfully exported {0} meshes to {1}'.format(export_count, batch_dir))
        # Nice touch to select the original selection after
        cmds.select(self.current_selection, replace=True)
        self.current_selection = None

    def build_obj_options_string(self):
        """
        Helper method to build out the verbose string Maya requires when exporting OBJs via the file command
        """
        if self.params['obj_groups']:
            groups = '1'
        else:
            groups = '0'

        if self.params['obj_ptgroups']:
            ptgroups = '1'
        else:
            ptgroups = '0'

        if self.params['obj_materials']:
            materials = '1'
        else:
            materials = '0'

        if self.params['obj_smoothing']:
            smoothing = '1'
        else:
            smoothing = '0'

        if self.params['obj_normals']:
            normals = '1'
        else:
            normals = '0'

        return 'groups={0};ptgroups={1};materials={2};smoothing={3};normals={4}'.format(
            groups, ptgroups, materials, smoothing, normals)

    def load_attributes(self, node):
        """
        Attempts to load the specified attributes from the given Maya node, and if they exists, sets our
        class variables to those attributes.
        :param node: The Maya node to attempt to read attributes from
        """
        if get_attr(node, 'soep') == '':
            self.params['export_path'] = None
        else:
            self.params['export_path'] = get_attr(node, 'soep')

        if get_attr(node, 'soebp') == '':
            self.params['batch_export_path'] = None
        else:
            self.params['batch_export_path'] = get_attr(node, 'soebp')

        if get_attr(node, 'soeask') is not None:
            self.params['always_ask'] = get_attr(node, 'soeask')

        if get_attr(node, 'soetri') is not None:
            self.params['triangulate_mesh'] = get_attr(node, 'soetri')

        if get_attr(node, 'soemto') is not None:
            self.params['move_to_origin'] = get_attr(node, 'soemto')

        if get_attr(node, 'soeds') is not None:
            self.params['use_native_style'] = get_attr(node, 'soeds')

        if get_attr(node, 'soeg') is not None:
            self.params['obj_groups'] = get_attr(node, 'soeg')

        if get_attr(node, 'soepg') is not None:
            self.params['obj_ptgroups'] = get_attr(node, 'soepg')

        if get_attr(node, 'soem') is not None:
            self.params['obj_materials'] = get_attr(node, 'soem')

        if get_attr(node, 'soes') is not None:
            self.params['obj_smoothing'] = get_attr(node, 'soes')

        if get_attr(node, 'soen') is not None:
            self.params['obj_normals'] = get_attr(node, 'soen')

    def save_attributes(self, node):
        """
        Adds and sets all the required attributes to the given Maya node, using the static set_attr method
        :param node: The Maya node to add and set the attributes to
        """
        set_attr(node, 'soep', 'soe_path', 'string', self.params['export_path'])
        set_attr(node, 'soebp', 'soe_batch_path', 'string', self.params['batch_export_path'])
        set_attr(node, 'soeask', 'soe_always_ask', 'bool', self.params['always_ask'])
        set_attr(node, 'soetri', 'soe_triangulate', 'bool', self.params['triangulate_mesh'])
        set_attr(node, 'soemto', 'soe_move_to_origin', 'bool', self.params['move_to_origin'])
        set_attr(node, 'soeds', 'soe_use_native_style', 'bool', self.params['use_native_style'])
        set_attr(node, 'soeg', 'soe_obj_groups', 'bool', self.params['obj_groups'])
        set_attr(node, 'soepg', 'soe_obj_point_groups', 'bool', self.params['obj_ptgroups'])
        set_attr(node, 'soem', 'soe_obj_materials', 'bool', self.params['obj_materials'])
        set_attr(node, 'soes', 'soe_obj_smoothing', 'bool', self.params['obj_smoothing'])
        set_attr(node, 'soen', 'soe_obj_normals', 'bool', self.params['obj_normals'])

    def debug_print(self):
        """ Helper method that dumps class variables to output """
        print('---------------------------------------------------')
        print('Export path: {0}'.format(self.params['export_path']))
        print('Batch path: {0}'.format(self.params['batch_export_path']))
        print('Ask before every save: {0}'.format(self.params['always_ask']))
        print('Triangulate Mesh: {0}'.format(self.params['triangulate_mesh']))
        print('Move to origin: {0}'.format(self.params['move_to_origin']))
        print('Use Native OS Style: {0}'.format(self.params['use_native_style']))
        print('OBJ Groups: {0}'.format(self.params['obj_groups']))
        print('OBJ Point Groups: {0}'.format(self.params['obj_ptgroups']))
        print('OBJ Materials: {0}'.format(self.params['obj_materials']))
        print('OBJ Smoothing: {0}'.format(self.params['obj_smoothing']))
        print('OBJ Normals: {0}'.format(self.params['obj_normals']))
        print('---------------------------------------------------')


class OptionsPopup(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        """ Constructor Method """
        super(OptionsPopup, self).__init__(parent)

        self.setWindowTitle('Simple OBJ Exporter')
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        """ Helper method that groups together all widget creation """
        self.export_options_gb = QtWidgets.QGroupBox('Export Options')
        self.always_ask_cb = QtWidgets.QCheckBox('Ask path before every export')
        self.triangulate_cb = QtWidgets.QCheckBox('Triangulate mesh')
        self.move_to_origin_cb = QtWidgets.QCheckBox('Move to origin')

        self.tool_options_gb = QtWidgets.QGroupBox('Tool Options')
        self.dialog_style_native_rb = QtWidgets.QRadioButton('Native OS File Browser')
        self.dialog_style_maya_rb = QtWidgets.QRadioButton('Maya Style File Browser', checked=True)

        self.path_options_gb = QtWidgets.QGroupBox('File Export Paths')
        self.file_path_le = QtWidgets.QLineEdit()
        self.file_path_le.setMinimumWidth(250)
        #self.file_path_le.setReadOnly(True)
        self.file_path_le.setPlaceholderText('Browse...')

        self.file_path_btn = QtWidgets.QPushButton()
        self.file_path_btn.setIcon(QtGui.QIcon(':folder-closed.png'))
        self.file_path_btn.setToolTip('Browse')

        self.obj_options_gb = QtWidgets.QGroupBox('OBJ Export Specific Options')
        self.obj_groups_cb = QtWidgets.QCheckBox('Groups', checked=True)
        self.obj_ptgroups_cb = QtWidgets.QCheckBox('Point groups', checked=True)
        self.obj_materials_cb = QtWidgets.QCheckBox('Materials', checked=True)
        self.obj_smoothing_cb = QtWidgets.QCheckBox('Smoothing', checked=True)
        self.obj_normals_cb = QtWidgets.QCheckBox('Normals', checked=True)

        self.batch_path_le = QtWidgets.QLineEdit()
        self.batch_path_le.setMinimumWidth(250)
        #self.batch_path_le.setReadOnly(True)
        self.batch_path_le.setPlaceholderText('Browse to directory....')

        self.batch_path_btn = QtWidgets.QPushButton()
        self.batch_path_btn.setIcon(QtGui.QIcon(':folder-closed.png'))
        self.batch_path_btn.setToolTip('Browse')

        self.cancel_btn = QtWidgets.QPushButton('Cancel')
        self.save_defaults_btn = QtWidgets.QPushButton('Save Defaults')
        self.save_defaults_btn.setToolTip('Save these current options as defaults for new Maya scenes ans sessions')
        self.confirm_btn = QtWidgets.QPushButton('Confirm')

    def create_layout(self):
        """ Helper method that groups together all widget layout """
        export_options_layout = QtWidgets.QVBoxLayout()
        export_options_layout.addWidget(self.always_ask_cb)
        export_options_layout.addWidget(self.triangulate_cb)
        export_options_layout.addWidget(self.move_to_origin_cb)
        export_options_layout.addStretch()
        self.export_options_gb.setLayout(export_options_layout)

        tool_options_layout = QtWidgets.QVBoxLayout()
        dialog_style_rb_layout = QtWidgets.QHBoxLayout()
        dialog_style_rb_layout.addWidget(self.dialog_style_native_rb)
        dialog_style_rb_layout.addWidget(self.dialog_style_maya_rb)
        tool_options_layout.addLayout(dialog_style_rb_layout)
        self.tool_options_gb.setLayout(tool_options_layout)

        obj_options_layout = QtWidgets.QVBoxLayout()
        obj_options_layout.addWidget(self.obj_groups_cb)
        obj_options_layout.addWidget(self.obj_ptgroups_cb)
        obj_options_layout.addWidget(self.obj_materials_cb)
        obj_options_layout.addWidget(self.obj_smoothing_cb)
        obj_options_layout.addWidget(self.obj_normals_cb)
        obj_options_layout.addStretch()
        self.obj_options_gb.setLayout(obj_options_layout)

        path_options_layout = QtWidgets.QGridLayout()
        path_options_layout.addWidget(QtWidgets.QLabel('Single OBJ export'), 0, 0)
        path_options_layout.addWidget(self.file_path_le, 0, 1)
        path_options_layout.addWidget(self.file_path_btn, 0, 2)
        path_options_layout.addWidget(QtWidgets.QLabel('Batch OBJ export'), 1, 0)
        path_options_layout.addWidget(self.batch_path_le, 1, 1)
        path_options_layout.addWidget(self.batch_path_btn, 1, 2)
        self.path_options_gb.setLayout(path_options_layout)

        options_layout_main = QtWidgets.QHBoxLayout()
        options_layout_left = QtWidgets.QVBoxLayout()
        options_layout_left.addWidget(self.export_options_gb)
        options_layout_left.addWidget(self.tool_options_gb)
        options_layout_main.addLayout(options_layout_left)
        options_layout_main.addWidget(self.obj_options_gb)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_defaults_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.confirm_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(options_layout_main)
        main_layout.addWidget(self.path_options_gb)
        main_layout.addLayout(buttons_layout)

    def create_connections(self):
        """ Helper method that groups together all signals and slots """
        self.cancel_btn.clicked.connect(self.reject)
        self.save_defaults_btn.clicked.connect(self.save_defaults)
        self.confirm_btn.clicked.connect(self.accept)
        self.file_path_btn.clicked.connect(self.set_file_path)
        self.batch_path_btn.clicked.connect(self.set_batch_path)
        self.always_ask_cb.stateChanged.connect(self.toggle_path_options)

    def set_file_path(self):
        """ Called when the set single file path option is clicked """
        if self.dialog_style_native_rb.isChecked():
            file_path = show_file_dialog(0, 1)
        else:
            file_path = show_file_dialog(0, 2)

        if file_path is not None:
            self.file_path_le.setText(file_path[0])

    def set_batch_path(self):
        """ Called when the set batch file path button is clicked """
        if self.dialog_style_native_rb.isChecked():
            batch_path = show_file_dialog(3, 1)
        else:
            batch_path = show_file_dialog(3, 2)

        if batch_path is not None:
            self.batch_path_le.setText(batch_path[0])

    def save_defaults(self):
        """ Called when the Save Defaults button is clicked """
        json_params = {
            'export_path' : self.file_path_le.text(),
            'batch_export_path' : self.batch_path_le.text(),
            'always_ask' : self.always_ask_cb.isChecked(),
            'triangulate_mesh' : self.triangulate_cb.isChecked(),
            'move_to_origin' : self.move_to_origin_cb.isChecked(),
            'use_native_style' : self.dialog_style_native_rb.isChecked(),
            'obj_groups' : self.obj_groups_cb.isChecked(),
            'obj_ptgroups' : self.obj_ptgroups_cb.isChecked(),
            'obj_materials' : self.obj_materials_cb.isChecked(),
            'obj_smoothing' : self.obj_smoothing_cb.isChecked(),
            'obj_normals' : self.obj_normals_cb.isChecked()
        }
        print('SimpleObjExporter: Saving current options to defaults json...')
        defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soe_defaults.json')
        with open(defaults_path, 'w') as fw:
            json.dump(json_params, fw, indent = 4)

    def toggle_path_options(self):
        """ Disable the file path line edits if the "ask before every export" checkbox is ticked """
        self.path_options_gb.setEnabled(not self.always_ask_cb.isChecked())


# Main Method (used for testing)
if __name__ == "__main__":
    simple_obj_exporter = SimpleObjExporter()
    simple_obj_exporter.export_selected()
