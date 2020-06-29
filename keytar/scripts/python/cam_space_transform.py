"""
nudge objects in camera depth
"""

import hou
from PySide2 import QtWidgets, QtCore
from functools import partial


def cam_space_nudge(pos, cam, x=0, y=0, z=0):
    """
    Transforms a position vector in camera view space
    
    @param pos: World space position vector. List, tuple or Vector3
    @param cam: Camera path or object
    @param x: Amount in camera x to move
    @param y: Amount in camera y to move
    @param z: Amount in camera z to move
    @return: Mofified positon vector
    """
    
    if isinstance(pos, list):
        pos = hou.Vector3(pos)
    elif isinstance(pos, tuple):
        pos = hou.Vector3(pos)
    
    assert isinstance(pos, hou.Vector3)
    
    if isinstance(cam, basestring):
        cam = hou.node(cam)
    
    assert isinstance(cam, hou.ObjNode)
    
    focal = cam.parm("focal").eval()
    aperture = cam.parm("aperture").eval()
    zoom = focal / aperture
    xres = float(cam.parm("resx").eval())
    yres = float(cam.parm("resy").eval())
    pix_aspect = cam.parm("aspect").eval()
    
    aspect = xres / yres
    near_clip = cam.parm("near").eval()
    far_clip = cam.parm("far").eval()
    
    # camera view matrix
    view_matrix = hou.Matrix4()
    # we are ignoring the camera window, using the full aperture
    # camera window can vary with 2d pan/zoom, etc
    view_matrix.setToPerspective(zoom, aspect, pix_aspect, near_clip, far_clip, 0, 1, 0, 1)
    
    # camera transform matrix
    cam_xform = cam.worldTransform()
    
    # position in the camera transform space
    pos_in_cam = pos * cam_xform.inverted()
    # print 'pos in cam xform space:', pos_in_cam
    
    # this is the depth in cam xform space
    depth = pos_in_cam.z() * -1
    # normalize the depth before converting into matrix space
    squish = hou.hmath.buildScale(1 / depth, 1 / depth, 1 / depth)
    
    ndc_pos = pos_in_cam * squish * view_matrix
    # print 'NDC cam_pos:', ndc_pos
    
    # adjust the depth here
    depth += z
    ndc_pos[0] = ndc_pos[0] + x
    ndc_pos[1] = ndc_pos[1] + y
    # print 'NDC post adjust:', ndc_pos
    
    # scale the depth back out to the proper
    stretch = hou.hmath.buildScale(depth, depth, depth)
    new_pos = ndc_pos * view_matrix.inverted() * stretch * cam_xform
    # print 'new world pos', new_pos
    return new_pos


"""
cam = hou.node("/obj/cam1")

# simple example - objNode
target = hou.node("/obj/sphere1/")
pos = hou.Vector3(target.parmTuple("t").eval())
new_pos = cam_space_nudge(pos, cam, x=0, z=0.1)
target.parmTuple("t").set(new_pos)


# here's one on a SOP node, taking into account the parent's
# world transform matrix

target = hou.node("/obj/geo1/add1")
print type(target)
print target.parent()
par_xform = target.parent().worldTransform()
print par_xform

pos = hou.Vector3(target.parmTuple("pt0").eval())
print 'local pos:', pos
world_pos = pos * par_xform
print 'world_pos', world_pos

new_pos = cam_space_nudge(world_pos, cam, x=0, z=-0.1)
local_pos = new_pos * par_xform.inverted()
target.parmTuple("pt0").set(local_pos)
"""


class CameraChooserEdit(QtWidgets.QLineEdit):
    def __init__(self):
        super(CameraChooserEdit, self).__init__()
        self.setAcceptDrops(True)
    
    
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
    
    
    def dropEvent(self, event):
        mime_data = event.mimeData()
        
        # Check if a node path was dropped.
        data = mime_data.data(hou.qt.mimeType.nodePath)
        if not data.isEmpty():
            node_path = str(data)
            print node_path
            node = hou.node(node_path)
            print node
            print node.type().name()
            if node.type().name() == 'cam':
                self.setText(node_path)
            else:
                print 'rejecting node:'
        event.accept()


class ParmChooserEdit(QtWidgets.QLineEdit):
    def __init__(self):
        super(ParmChooserEdit, self).__init__()
        self.setAcceptDrops(True)
    
    
    def dragEnterEvent(self, event):
        event.acceptProposedAction()
    
    
    def dropEvent(self, event):
        mime_data = event.mimeData()
        
        # Check if a parameter path was dropped.
        data = mime_data.data(hou.qt.mimeType.parmPath)
        if not data.isEmpty():
            parm_paths = str(data).split("\t")
            print parm_paths
            parm_path = parm_paths[0]
            print parm_path
            parm = hou.parm(parm_path)
            print parm
            if parm:
                parm_tuple = parm.tuple()
                if len(parm_tuple) == 3:
                    self.setText(parm.tuple().name())
                else:
                    print 'not a vector 3 typeish parm'
        event.accept()


class CameraSpaceNudgeUi(QtWidgets.QDialog):
    def __init__(self):
        super(CameraSpaceNudgeUi, self).__init__(hou.ui.mainQtWindow())
        
        self.setWindowTitle('Camera space nudge')
        self.setWindowFlags(QtCore.Qt.Tool)
        # self.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        
        root = hou.node('/')
        camera_nodes = root.recursiveGlob('*', hou.nodeTypeFilter.ObjCamera)
        if camera_nodes:
            # if there's cameras in the scene, just grab the first one as a default
            self.camera = camera_nodes[0].path()
        else:
            self.camera = None
        
        self.parm = 't'
        self.time_range = 'all'
        
        self.draw_ui()
        
        self.parm_edit.setText(self.parm)
    
    
    def camera_edit_changed(self):
        self.camera = self.camera_edit.text()
        print "camera changed", self.camera
    
    
    def parm_edit_changed(self):
        self.parm = self.parm_edit.text()
        print "self.parm changed", self.parm
    
    
    def onCameraSelected(self, node_path):
        self.camera = node_path.path()
        self.camera_edit.setText(self.camera)
    
    
    def onParmSelected(self, node_path):
        print node_path
        if node_path:
            parm_tuple = node_path[0]
            if len(parm_tuple) == 3:
                self.parm = parm_tuple.name()
                self.parm_edit.setText(self.parm)
            else:
                print 'not a vector3 type ish parmTuple'
    
    
    def time_range_changed(self):
        self.time_range = self.time_range_combo.currentData()
    
    
    def draw_ui(self):
        
        main_lay = QtWidgets.QHBoxLayout()
        self.setLayout(main_lay)
        xform_lay = QtWidgets.QVBoxLayout()
        main_lay.addLayout(xform_lay)
        
        camera_lay = QtWidgets.QHBoxLayout()
        xform_lay.addLayout(camera_lay)
        
        camera_label = QtWidgets.QLabel("Camera")
        camera_lay.addWidget(camera_label)
        
        self.camera_edit = CameraChooserEdit()
        self.camera_edit.setText(self.camera)
        self.camera_edit.textChanged.connect(self.camera_edit_changed)
        camera_lay.addWidget(self.camera_edit)
        
        node_chooser_btn = hou.qt.NodeChooserButton()
        node_chooser_btn.setNodeChooserFilter(hou.nodeTypeFilter.ObjCamera)
        node_chooser_btn.nodeSelected.connect(self.onCameraSelected)
        camera_lay.addWidget(node_chooser_btn)
        
        parm_lay = QtWidgets.QHBoxLayout()
        xform_lay.addLayout(parm_lay)
        
        parm_label = QtWidgets.QLabel("Parm Tuple")
        parm_lay.addWidget(parm_label)
        
        self.parm_edit = ParmChooserEdit()
        self.parm_edit.textChanged.connect(self.parm_edit_changed)
        parm_lay.addWidget(self.parm_edit)
        
        node_chooser_btn = hou.qt.ParmTupleChooserButton()
        node_chooser_btn.parmTupleSelected.connect(self.onParmSelected)
        parm_lay.addWidget(node_chooser_btn)
        
        time_lay = QtWidgets.QHBoxLayout()
        xform_lay.addLayout(time_lay)
        
        time_label = QtWidgets.QLabel("Time range")
        time_lay.addWidget(time_label)
        
        self.time_range_combo = QtWidgets.QComboBox()
        self.time_range_combo.addItem('All frames', 'all')
        self.time_range_combo.addItem('Playbar selection', 'sel')
        self.time_range_combo.addItem('Current Frame', 'cur')
        self.time_range_combo.currentIndexChanged.connect(self.time_range_changed)
        time_lay.addWidget(self.time_range_combo)
        
        # PIVOT OPTIONS
        groupBox = QtWidgets.QGroupBox("Nudge")
        xform_lay.addWidget(groupBox)
        pv_lay = QtWidgets.QVBoxLayout()
        pv_grid = QtWidgets.QGridLayout()
        groupBox.setLayout(pv_lay)
        pv_lay.addLayout(pv_grid)
        
        pv0 = QtWidgets.QLabel()
        pv_grid.addWidget(pv0, 0, 0)
        
        up_btn = QtWidgets.QPushButton("Up")
        up_btn.clicked.connect(partial(self.move, y=1))
        pv_grid.addWidget(up_btn, 0, 1)
        
        pv2 = QtWidgets.QLabel()
        pv_grid.addWidget(pv2, 0, 2)
        
        left_btn = QtWidgets.QPushButton("Left")
        left_btn.clicked.connect(partial(self.move, x=-1))
        pv_grid.addWidget(left_btn, 1, 0)
        
        self.nudge_amount = QtWidgets.QDoubleSpinBox()
        self.nudge_amount.setRange(0, 10)
        self.nudge_amount.setSingleStep(0.01)
        self.nudge_amount.setValue(0.1)
        pv_grid.addWidget(self.nudge_amount, 1, 1)
        
        right_btn = QtWidgets.QPushButton("Right")
        right_btn.clicked.connect(partial(self.move, x=1))
        pv_grid.addWidget(right_btn, 1, 2)
        
        back_btn = QtWidgets.QPushButton("Back")
        back_btn.clicked.connect(partial(self.move, z=1))
        pv_grid.addWidget(back_btn, 2, 0)
        
        down_btn = QtWidgets.QPushButton("Down")
        down_btn.clicked.connect(partial(self.move, y=-1))
        pv_grid.addWidget(down_btn, 2, 1)
        
        fwd_btn = QtWidgets.QPushButton("Fwd")
        fwd_btn.clicked.connect(partial(self.move, z=-1))
        
        pv_grid.addWidget(fwd_btn, 2, 2)
        
        # BUTTONS AND OPTIONS
        btn_lay = QtWidgets.QVBoxLayout()
        xform_lay.addLayout(btn_lay)
        
        down_btn = QtWidgets.QPushButton("Down")
        down_btn.clicked.connect(partial(self.move, y=1))
    
    
    def move(self, x=0, y=0, z=0):
        camera = hou.node(self.camera)
        if not camera:
            raise RuntimeError("cannot find camera")
        
        amount = self.nudge_amount.value()
        
        x_offset = x * amount
        y_offset = y * amount
        z_offset = z * amount
        
        current_frame = hou.frame()
        with hou.undos.group('Camera NudgeKeys'):
            for node in hou.selectedNodes():
                print node
                keytimes = []
                parmTuple = node.parmTuple(self.parm)
                if parmTuple:
                    if self.time_range == 'cur':
                        keytimes = [current_frame]
                    else:
                        for parm in parmTuple:
                            print parm
                            parm_keys = parm.keyframes()
                            keytimes.extend([x.frame() for x in parm_keys])
                        
                        keytimes = sorted(list(set(keytimes)))
                        if self.time_range == 'sel':
                            sel_range = hou.playbar.selectionRange()
                            keytimes = [x for x in keytimes if x >= sel_range[0] and x <= sel_range[1]]
                    
                    print keytimes
                    
                    for keytime in keytimes:
                        hou.setFrame(keytime)
                        pos = hou.Vector3(parmTuple.eval())
                        new_pos = cam_space_nudge(pos, camera, x=x_offset, y=y_offset, z=z_offset)
                        parmTuple.set(new_pos)
        hou.setFrame(current_frame)
