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

def validate_dir_path(path):
    """
    Perform a relatively simple check of the given user path.
    Puts a little more trust to the user to not type garbage into the file path line edits in the UI.
    Check if the directory exists, if not create the directory. If that fails, return False.
    :param str path: The path to test against, and potentially create.
    :return:
    """
    if path is None:
        return False
    if path == '':
        return False
    
    dir = os.path.normpath(os.path.abspath(path))

    if os.path.exists(dir):
        return True
    # if not, makedirs
    try:
        #print('SimpleObjExporter: Attempting to create output directory {}'.format(dir))
        os.makedirs(dir, 511, True)
        return True
    except Exception:
        return False

def set_attr(node, short_name, long_name, attr_type, value):
    """
    Static helper method for setting a Maya attribute. Checks if attribute exists, adds it if not,
    and goes on to set the value.
    :param node: The Maya node to add the attribute to
    :param short_name: Attribute's Maya short name
    :param long_name: Attribute's Maya Long name
    :param attr_type: The attribute's type (string, bool, etc)
    :param value: The value to set the attribute to
    :return:
    """
    try:
        if cmds.listAttr(node, userDefined=True, visible=True) is None or \
                long_name not in cmds.listAttr(node, userDefined=True, visible=True):
            # Maya needs slightly different arguments depending on type
            if attr_type == 'string':
                cmds.addAttr(node, shortName=short_name, longName=long_name, dataType=attr_type)
            elif attr_type == 'bool':
                cmds.addAttr(node, shortName=short_name, longName=long_name, attributeType=attr_type)
    except RuntimeError as e:
        pass

    # set the attribute
    if attr_type == 'string' and value:
        cmds.setAttr('{0}.{1}'.format(node, short_name), value, type='string')

    elif attr_type == 'bool':
        cmds.setAttr('{0}.{1}'.format(node, short_name), value)


def get_attr(mesh, short_name):
    """
    Static helper method for attempting to get an attributes value from a Maya node
    :param mesh: The Maya node that contains attribute
    :param short_name: The attribute's short name
    :return: The attribute's value if exists, None if does not exist
    """
    try:
        return cmds.getAttr('{0}.{1}'.format(mesh, short_name))
    except ValueError as e:
        return None
    
def delete_attr(mesh, short_name):
    """
    Static helper method for attempting to delete a attribute on a Maya node
    :param mesh: The Maya node that contains attribute
    :param short_name: The attribute's short name
    """
    try:
        cmds.deleteAttr('{0} at={1}'.format(mesh, short_name))
    except RuntimeError as e:
        return

def show_file_dialog(dialog_mode, dialog_style, starting_dir = None):
    """
    Static helper function to display the Maya file dialog based on users styler selection
    :param dialog_style: 1 Native OS style, 2 Maya style
    :param dialog_mode: 0 Any file, existing or not, 3 Name of a directory
    :param starting_dir: Path to directory to start file dialog in, defaults to Workspace
    :return: The string list output by maya's cmd.fileDialog2 command
    """
    if not validate_dir_path(starting_dir):
        starting_dir = cmds.workspace(query=True, directory=True)

    if dialog_mode == 0:
        obj_filter = 'OBJ Files (*.obj);;All Files (*.*)'
        return cmds.fileDialog2(fileFilter=obj_filter, fileMode=0, dialogStyle=dialog_style,
                                startingDirectory=starting_dir, caption='Set OBJ export path...')
    # else
    return cmds.fileDialog2(fileMode=3, dialogStyle=dialog_style, startingDirectory=starting_dir,
                            okCaption='Select', caption='Set batch OBJ export path...')


class SimpleObjExporter:
    # Use a class method to create only one instance of this class for persistence
    class_instance = None

    @classmethod
    def shelf_button_clicked(cls):
        if not cls.class_instance:
            cls.class_instance = SimpleObjExporter()

        cls.class_instance.export_pressed()

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

        # non DAG node to store our settings on
        self.params_node = 'simpleObjExporterParams'

        # setup our default export params
        # unless this is the very first time this has been run, these will be overwritten
        # by the init_export_params when the options window is pulled up
        ws_path = os.path.abspath(os.path.join(cmds.workspace(q = True, directory = True), 'objExport'))
        self.params = {
            'export_path' : os.path.join(ws_path, 'DefaultExport.obj'),
            'batch_export_path' : os.path.join(ws_path, 'batch'),
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

        # dict of the params to attribute short and long names, and type
        # for cleaner setting and getting later on, can do in loop
        self.param_attr_map = {
            'export_path' : {'sn':'soep','ln':'soe_path', 'type':'string'},
            'batch_export_path' : {'sn':'soebp','ln':'soe_batch_path', 'type':'string'},
            'always_ask' : {'sn':'soeask','ln':'soe_always_ask', 'type':'bool'},
            'triangulate_mesh' : {'sn':'soetri','ln':'soe_triangulate', 'type':'bool'},
            'move_to_origin' : {'sn':'soemto','ln':'soe_move_to_origin', 'type':'bool'},
            'use_native_style' : {'sn':'soeds','ln':'soe_use_native_style', 'type':'bool'},
            'obj_groups' : {'sn':'soeg','ln':'soe_obj_groups', 'type':'bool'},
            'obj_ptgroups' : {'sn':'soepg','ln':'soe_obj_point_groups', 'type':'bool'},
            'obj_materials' : {'sn':'soem','ln':'soe_obj_materials', 'type':'bool'},
            'obj_smoothing' : {'sn':'soes','ln':'soe_obj_smoothing', 'type':'bool'},
            'obj_normals' : {'sn':'soen','ln':'soe_obj_normals', 'type':'bool'}
        }

    def init_export_params(self):
        """
        Initialize the locations where data from previous sessions may be stored.
        1) If the scene node already exists, read from this.
        2) If the scene node doesn't already exist, load from the json defaults and
        create the scene node with those settings
        3) If the defaults json doesn't already exist, this is the very first time
        the tool has been run on this Maya install, so create it
        """
        defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soe_defaults.json')

        # does the scene node exist?
        if len(cmds.ls(self.params_node)) > 0:
            # load into the param dict
            #print('SimpleObjExporter: Scene node exists, loading..')
            self.load_attributes(self.params_node)
            return

        # no scene node, does defaults json exist?
        if os.path.exists(defaults_path):
            # json exists, load this
            #print('SimpleObjExporter: Reading defaults json file...')
            with open(defaults_path, 'r') as fr:
                self.params = json.load(fr)

        else:
            # json doesn't exist yet, write one out using our defaults from the __init__
            #print('SimpleObjExporter: No existing defaults json file, creating...')
            with open(defaults_path, 'w') as fw:
                json.dump(self.params, fw, indent = 4)

        # now create the scene node to store our params on
        cmds.createNode('network', n=self.params_node)
        self.save_attributes(self.params_node)

    def export_pressed(self):
        """
        Runs checks to ensure valid selection before calling export_selection
        """
        selection = cmds.ls(sl=True, type='transform')

        if len(selection) <= 0:
            # if export clicked with nothing selected, just show options instead
            self.show_options()
            return

        else:
            for i in range(0, len(selection)):
                shape_nodes = cmds.listRelatives(selection[i], shapes=True)
                if shape_nodes is None:
                    om.MGlobal.displayError('"{}" is not a mesh. Please select only meshes to be exported'
                                            .format(selection[i]))
                    return

        # we have a selection of only meshes!
        # ensure our params are up-to-date
        self.init_export_params()
        self.export_selection(selection)
        
    def export_selection(self, selection):
        """
        Depending on length of selection array, performs standard export or a batch (loop) export
        By the time this function is reached, we are confident we have a valid selection and work
        under that assumption.
        """
        # is this a single or batch selection to export?
        if len(selection) == 1:
            # Single mesh export
            current_selection = selection[0]

            # ensure scene params loaded
            self.load_attributes(self.params_node)

            # Are we asking path each time?
            if self.params['always_ask']:
                # put dialog_style into mayas expected args
                if self.params['use_native_style']:
                    dialog_style = 1
                else:
                    dialog_style = 2

                self.params['export_path'] = show_file_dialog(0, dialog_style)[0]

            # now we have loaded from scene and checked overrides,
            # lets ensure that current export path is valid
            if validate_dir_path(os.path.dirname(self.params['export_path'])):
                self.export_mesh(current_selection)

            else:
                om.MGlobal.displayError('Invalid export path: {}'.format(self.params['export_path']))
    
        
        elif len(selection) > 1:
            # Batch export of meshes
            successful = 0
            failed = 0

            # ensure scene params loaded
            self.load_attributes(self.params_node)
            batch_dir = None
        
            # Are we asking path each time?
            if self.params['always_ask']:
                if self.params['use_native_style']:
                    dialog_style = 1
                else:
                    dialog_style = 2
                self.params['batch_export_path'] = show_file_dialog(3, dialog_style)[0]

            # bail out if not valid directory
            if not validate_dir_path(self.params['batch_export_path']):
                om.MGlobal.displayError('Batch export path not valid: {}'.format(self.params['batch_export_path']))
                return

            # iterate through mesh selection
            for i in range(0, len(selection)):
                current_selection = selection[i]

                # attempt to build path using set path and node name
                file_path = os.path.join(self.params['batch_export_path'], '{0}.obj'.format(clean_filename(current_selection)))
                # I guess maya cmds export expects these slashes?
                file_path = os.path.normpath(file_path)
                file_path = file_path.replace('\\', '/')
                self.params['export_path'] = file_path

                # attempt export
                result = self.export_mesh(current_selection)
                if result:
                    successful += 1
                else:
                    failed += 1
        
            # all meshes have attempted export
            if failed > 0:
                om.MGlobal.displayWarning('Successfully exported {0} meshes of {1}'.format(successful, successful + failed))    
            else:
                om.MGlobal.displayInfo('Successfully exported {0} meshes of {1}'.format(successful, successful + failed))

        else:
            # something has gone terribly wrong and we got passed a zero length selection
            om.MGlobal.displayError('Fatal: export_selection passed empty selection array')

        # finally, reset to scene params
        self.load_attributes(self.params_node)
        cmds.select(selection, replace=True)
        

    def export_mesh(self, mesh):
        """
        Duplicates, processes, and exports the specified mesh
        """
        file_path = self.params['export_path']
        result = False
        # Duplicate mesh for safety and processing
        dupe_mesh = cmds.duplicate(mesh, name='{0}_export'.format(mesh))
        self.preprocess_mesh(dupe_mesh)
        cmds.select(dupe_mesh, replace=True)

        try:
            out_file = cmds.file(file_path, exportSelected=True, type='OBJexport', force=True, 
                                 options=self.build_obj_options_string())

            om.MGlobal.displayInfo('Successfully exported to {0}'.format(out_file))
            result = True

        except RuntimeError as e:
            om.MGlobal.displayError('Unable to export {0}: {1}'.format(mesh, e))

        finally:
            cmds.delete(dupe_mesh)
            cmds.select(mesh, replace=True)

        return result
    
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

    def show_options(self):
        """
        Set the fields of the option dialog instance based on the current selection, and shows option dialog.
        """
        # ensure scene params source up to date and loaded        
        self.init_export_params()

        # update UI
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
        Saves the values from the options UI to our class dict and scene, if the user clicks accept.
        If the user rejects UI, we don't save these so that next time the UI is launched it still
        uses the previous values.
        """
        # ensure current scene params loaded
        self.load_attributes(self.params_node)

        # ensure the user has not fed garbage into the line edits
        # if so, simply don't update them and leave as is
        if validate_dir_path(os.path.dirname(self.options_popup.file_path_le.text())):
            self.params['export_path'] = self.options_popup.file_path_le.text()
        else:
            om.MGlobal.displayError('Export file path is not valid! Not updating...')

        if validate_dir_path(self.options_popup.batch_path_le.text()):
            self.params['batch_export_path'] = self.options_popup.batch_path_le.text()
        else:
            om.MGlobal.displayError('Batch export file path is not valid! Not updating...')

        # the other params are much safer, so just set those
        self.params['always_ask'] = self.options_popup.always_ask_cb.isChecked()
        self.params['triangulate_mesh'] = self.options_popup.triangulate_cb.isChecked()
        self.params['move_to_origin'] = self.options_popup.move_to_origin_cb.isChecked()
        self.params['use_native_style'] = self.options_popup.dialog_style_native_rb.isChecked()
        self.params['obj_groups'] = self.options_popup.obj_groups_cb.isChecked()
        self.params['obj_ptgroups'] = self.options_popup.obj_ptgroups_cb.isChecked()
        self.params['obj_materials'] = self.options_popup.obj_materials_cb.isChecked()
        self.params['obj_smoothing'] = self.options_popup.obj_smoothing_cb.isChecked()
        self.params['obj_normals'] = self.options_popup.obj_normals_cb.isChecked()

        # save to scene
        self.save_attributes(self.params_node)
    
    def load_attributes(self, node):
        """
        Attempts to load the specified attributes from the given Maya node, and if they exist, 
        sets our class dict to those attributes, importantly leaving value unchanged if not
        :param node: The Maya node to attempt to read attributes from
        """
        for param in self.param_attr_map.keys():
            short_name = self.param_attr_map[param]['sn']
            if get_attr(node, short_name):
                self.params[param] = get_attr(node, short_name)

    def save_attributes(self, node):
        """
        Adds and sets all the required attributes to the given Maya node, using the static set_attr method
        :param node: The Maya node to add and set the attributes to
        """

        for param in self.param_attr_map.keys():
            short_name = self.param_attr_map[param]['sn']
            long_name = self.param_attr_map[param]['ln']
            type = self.param_attr_map[param]['type']

            set_attr(node, short_name, long_name, type, self.params[param])

    def clear_attributes(self, node):
        """
        Deletes all the attributes added by this tool from the given Maya node. Once deleted, the node
        is no longer considered to have overrides and will use the scene params to export.
        :param node: The Maya node on which to delete attributes
        """
        for param in self.param_attr_map.keys():
            delete_attr(node, self.param_attr_map[param]['sn'])
        
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
        self.load_defaults_btn = QtWidgets.QPushButton('Load Defaults')
        self.load_defaults_btn.setToolTip('Load the previously saved default settings')
        self.save_defaults_btn = QtWidgets.QPushButton('Save Defaults')
        self.save_defaults_btn.setToolTip('Save these current options as defaults for new Maya scenes created in the future')
        self.confirm_btn = QtWidgets.QPushButton('Save Settings')
        self.confirm_btn.setToolTip('Save these settings to the scene file')

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
        buttons_layout.addWidget(self.load_defaults_btn)
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
        self.load_defaults_btn.clicked.connect(self.load_defaults)
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

        if file_path:
            self.file_path_le.setText(file_path[0])

    def set_batch_path(self):
        """ Called when the set batch file path button is clicked """
        if self.dialog_style_native_rb.isChecked():
            batch_path = show_file_dialog(3, 1)
        else:
            batch_path = show_file_dialog(3, 2)

        if batch_path:
            self.batch_path_le.setText(batch_path[0])

    def load_defaults(self):
        """ Called when the Load Defaults button is clicked. """
        #print('SimpleObjExporter: Reading defaults from json...')
        defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soe_defaults.json')
        with open(defaults_path, 'r') as fr:
            default_params = json.load(fr)

        self.file_path_le.setText(default_params['export_path'])
        self.batch_path_le.setText(default_params['batch_export_path'])
        self.always_ask_cb.setChecked(default_params['always_ask'])
        self.triangulate_cb.setChecked(default_params['triangulate_mesh'])
        self.move_to_origin_cb.setChecked(default_params['move_to_origin'])
        self.dialog_style_native_rb.setChecked(default_params['use_native_style'])
        self.obj_groups_cb.setChecked(default_params['obj_groups'])
        self.obj_ptgroups_cb.setChecked(default_params['obj_ptgroups'])
        self.obj_materials_cb.setChecked(default_params['obj_materials'])
        self.obj_smoothing_cb.setChecked(default_params['obj_smoothing'])
        self.obj_normals_cb.setChecked(default_params['obj_normals'])

        om.MGlobal.displayInfo('Read defaults from {}'.format(defaults_path))


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
        #print('SimpleObjExporter: Saving current options to defaults json...')
        defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soe_defaults.json')
        with open(defaults_path, 'w') as fw:
            json.dump(json_params, fw, indent = 4)

        om.MGlobal.displayInfo('Saved defaults to {}'.format(defaults_path))

    def toggle_path_options(self):
        """ Disable the file path line edits if the "ask before every export" checkbox is ticked """
        self.path_options_gb.setEnabled(not self.always_ask_cb.isChecked())


# Main Method (used for testing)
if __name__ == "__main__":
    simple_obj_exporter = SimpleObjExporter()
    simple_obj_exporter.export_pressed()
