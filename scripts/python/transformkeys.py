"""
Transform keyframes

scale then translate keyframes with adjustable pivots
"""

import hou
from PySide2 import QtWidgets, QtCore
from functools import partial


def transformKeyframes(keyframes, scalex=1.0, scaley=1.0,
                       translatex=0.0, translatey=0.0,
                       pivotx=None, pivoty=None,
                       autopivot='mm',
                       ripple=True,
                       snapframe=True
                       ):
    xmin = 99999999999999
    xmax = -99999999999999
    
    ymin = 99999999999999
    ymax = -99999999999999
    
    for parm in keyframes.keys():
        for key in keyframes[parm]:
            xmin = min(xmin, key.frame())
            xmax = max(xmax, key.frame())
            
            ymin = min(ymin, key.value())
            ymax = max(ymax, key.value())
    
    print 'time range:', xmin, xmax
    
    print 'value range:', ymin, ymax
    
    pivotx_mid = (xmax - xmin) / 2 + xmin
    pivoty_mid = (ymax - ymin) / 2 + ymin
    
    if autopivot == 'tl':
        # top left
        pivotx = xmin
        pivoty = ymax
    
    elif autopivot == 'tm':
        # top middle
        pivotx = pivotx_mid
        pivoty = ymax
    
    elif autopivot == 'tr':
        # top right
        pivotx = xmax
        pivoty = ymax
    
    elif autopivot == 'ml':
        # middle left
        pivotx = xmin
        pivoty = pivoty_mid
    
    elif autopivot == 'mm':
        # middle middle
        pivotx = pivotx_mid
        pivoty = pivoty_mid
    
    elif autopivot == 'mr':
        # middle right
        pivotx = xmax
        pivoty = pivoty_mid
    
    elif autopivot == 'bl':
        # bottom left
        pivotx = xmin
        pivoty = ymin
    
    elif autopivot == 'bm':
        # bottom middle
        pivotx = pivotx_mid
        pivoty = ymin
    
    elif autopivot == 'br':
        # bottom right
        pivotx = xmax
        pivoty = ymin
    else:
        pivotx = pivotx or 0
        pivoty = pivoty or 0
    
    print 'pivots:'
    print pivotx, pivoty
    
    if xmin == xmax:
        raise RuntimeError("gotta select a bigger time range")
    
    xmin_pvt = xmin - pivotx
    xmax_pvt = xmax - pivotx
    
    xmin_scaled = xmin_pvt * scalex + translatex
    xmax_scaled = xmax_pvt * scalex + translatex
    xmin_diff = xmin_scaled - xmin_pvt
    xmax_diff = xmax_scaled - xmax_pvt
    print 'xdiffs', xmin_diff, xmax_diff
    
    ymin_pvt = ymin - pivoty
    ymax_pvt = ymax - pivoty
    
    ymin_scaled = ymin_pvt * scaley + translatey
    ymax_scaled = ymax_pvt * scaley + translatey
    
    for parm in keyframes.keys():
        if ripple:
            # you dont want to ripple if you're scaling negative. bad times
            if scalex > 0:
                
                before = parm.keyframesBefore(xmin - 1)
                for key in before:
                    parm.deleteKeyframeAtFrame(key.frame())
                    
                    newframe = key.frame() + xmin_diff
                    if snapframe:
                        newframe = round(newframe)
                    
                    key.setFrame(newframe)
                    parm.setKeyframe(key)
                
                after = parm.keyframesAfter(xmax + 1)
                
                for key in after:
                    parm.deleteKeyframeAtFrame(key.frame())
                    
                    newframe = key.frame() + xmax_diff
                    if snapframe:
                        newframe = round(newframe)
                    
                    key.setFrame(newframe)
                    parm.setKeyframe(key)
        
        for key in keyframes[parm]:
            # first run - delete the target keys from the parm
            parm.deleteKeyframeAtFrame(key.frame())
        
        for key in keyframes[parm]:
            # second run - apply the key at a modified time
            xvalue = key.frame()
            
            xvalue_pvt = xvalue - pivotx
            yvalue_pvt = key.value() - pivoty
            
            # https://stackoverflow.com/a/929107
            # NewValue = (((OldValue - OldMin) * (NewMax - NewMin)) / (OldMax - OldMin)) + NewMin
            new_xvalue = ((xvalue_pvt - xmin_pvt) * (xmax_scaled - xmin_scaled)) / (xmax_pvt - xmin_pvt) + xmin_scaled
            new_xvalue += pivotx
            
            print 'xvalue', xvalue
            print 'newxvalue', new_xvalue
            
            # new_xvalue = ((xvalue - xmin) / (xmax - xmin) ) * (xmin - xmax) + xmax
            # print frame, key.isSlopeAuto(), key.slope(), key.isSlopeTied()
            
            new_yvalue = ((yvalue_pvt - ymin_pvt) * (ymax_scaled - ymin_scaled)) / (ymax_pvt - ymin_pvt) + ymin_scaled
            new_yvalue += pivoty
            key.setValue(new_yvalue + translatey)
            
            if snapframe:
                new_xvalue = round(new_xvalue)
            key.setFrame(new_xvalue)
            
            if key.isSlopeAuto() is False:
                print 'old', key.inAccel(), key.accel()
                key.setAccel(key.accel() * scalex)
                # key.setInAccel(key.inAccel() * scalex)
                
                print 'new', key.inAccel(), key.accel()
                
                key.setSlope(key.slope() * scaley)
            
            else:
                # re-auto the keys
                key.setSlope(0)
                key.setSlopeAuto(True)
                key.setInSlopeAuto(True)
            parm.setKeyframe(key)


class TransformKeysUi(QtWidgets.QDialog):
    def __init__(self):
        super(TransformKeysUi, self).__init__(hou.ui.mainQtWindow())
        
        self.setWindowTitle('Transform Keys')
        self.setWindowFlags(QtCore.Qt.Tool)
        # self.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        
        self.draw_ui()
    
    
    def draw_ui(self):
        
        main_lay = QtWidgets.QHBoxLayout()
        self.setLayout(main_lay)
        xform_lay = QtWidgets.QVBoxLayout()
        main_lay.addLayout(xform_lay)
        
        sx_lay = QtWidgets.QHBoxLayout()
        xform_lay.addLayout(sx_lay)
        
        scalex_label = QtWidgets.QLabel("Scale X")
        sx_lay.addWidget(scalex_label)
        
        self.scalex_spin = QtWidgets.QDoubleSpinBox()
        self.scalex_spin.setRange(-9999999, 9999999)
        self.scalex_spin.setSingleStep(0.1)
        self.scalex_spin.setValue(1.0)
        sx_lay.addWidget(self.scalex_spin)
        
        tx_label = QtWidgets.QLabel("Translate X")
        sx_lay.addWidget(tx_label)
        
        self.tx_spin = QtWidgets.QDoubleSpinBox()
        self.tx_spin.setRange(-9999999, 9999999)
        self.tx_spin.setSingleStep(0.1)
        self.tx_spin.setValue(0)
        sx_lay.addWidget(self.tx_spin)
        
        sy_lay = QtWidgets.QHBoxLayout()
        xform_lay.addLayout(sy_lay)
        
        scaley_label = QtWidgets.QLabel("Scale Y")
        sy_lay.addWidget(scaley_label)
        
        self.scaley_spin = QtWidgets.QDoubleSpinBox()
        self.scaley_spin.setRange(-9999999, 9999999)
        self.scaley_spin.setSingleStep(0.1)
        self.scaley_spin.setValue(1.0)
        sy_lay.addWidget(self.scaley_spin)
        
        ty_label = QtWidgets.QLabel("Translate Y")
        sy_lay.addWidget(ty_label)
        
        self.ty_spin = QtWidgets.QDoubleSpinBox()
        self.ty_spin.setRange(-9999999, 9999999)
        self.ty_spin.setSingleStep(0.1)
        self.ty_spin.setValue(0)
        sy_lay.addWidget(self.ty_spin)
        
        # PIVOT OPTIONS
        groupBox = QtWidgets.QGroupBox("Pivot")
        xform_lay.addWidget(groupBox)
        pv_lay = QtWidgets.QVBoxLayout()
        pv_grid = QtWidgets.QGridLayout()
        groupBox.setLayout(pv_lay)
        pv_lay.addLayout(pv_grid)
        
        pv0 = QtWidgets.QRadioButton('⌜')
        pv0.setProperty('align', 'tl')
        pv0.setToolTip('Top Left')
        pv_grid.addWidget(pv0, 0, 0)
        
        pv1 = QtWidgets.QRadioButton()
        pv1.setProperty('align', 'tm')
        pv1.setToolTip('Top Middle')
        pv_grid.addWidget(pv1, 0, 1)
        
        pv2 = QtWidgets.QRadioButton('⌝')
        pv2.setProperty('align', 'tr')
        pv2.setToolTip('Top Right')
        pv_grid.addWidget(pv2, 0, 2)
        
        pv3 = QtWidgets.QRadioButton()
        pv3.setProperty('align', 'ml')
        pv3.setToolTip('Middle Left')
        pv_grid.addWidget(pv3, 1, 0)
        
        pv4 = QtWidgets.QRadioButton()
        pv4.setProperty('align', 'mm')
        pv4.setToolTip('Middle Middle')
        pv4.setChecked(True)
        pv_grid.addWidget(pv4, 1, 1)
        
        pv5 = QtWidgets.QRadioButton()
        pv5.setProperty('align', 'mr')
        pv5.setToolTip('Middle Right')
        pv_grid.addWidget(pv5, 1, 2)
        
        pv6 = QtWidgets.QRadioButton('⌞')
        pv6.setProperty('align', 'bl')
        pv6.setToolTip('Bottom Left')
        pv_grid.addWidget(pv6, 2, 0)
        
        pv7 = QtWidgets.QRadioButton()
        pv7.setProperty('align', 'bm')
        pv7.setToolTip('Bottom Middle')
        pv_grid.addWidget(pv7, 2, 1)
        
        pv8 = QtWidgets.QRadioButton('⌟')
        pv8.setProperty('align', 'br')
        pv8.setToolTip('Bottom Right')
        pv_grid.addWidget(pv8, 2, 2)
        
        self.align_checks = [pv0, pv1, pv2, pv3, pv4, pv5, pv6, pv7, pv8]
        
        # BUTTONS AND OPTIONS
        btn_lay = QtWidgets.QVBoxLayout()
        xform_lay.addLayout(btn_lay)
        
        self.snap_chk = QtWidgets.QCheckBox("Snap Frames")
        self.snap_chk.setCheckState(QtCore.Qt.Checked)
        self.snap_chk.setToolTip("Snap frame times to whole frames")
        btn_lay.addWidget(self.snap_chk)
        
        self.ripple_chk = QtWidgets.QCheckBox("Ripple")
        self.ripple_chk.setCheckState(QtCore.Qt.Checked)
        self.ripple_chk.setToolTip("Move keys outside of the selection range")
        btn_lay.addWidget(self.ripple_chk)
        
        reset_btn = QtWidgets.QPushButton("Reset")
        reset_btn.clicked.connect(self.reset)
        btn_lay.addWidget(reset_btn)
        
        self.applyButton = QtWidgets.QPushButton("Apply")
        self.applyButton.clicked.connect(self.transform)
        btn_lay.addWidget(self.applyButton)
        
        # QUICK TOOLS
        tools_lay = QtWidgets.QVBoxLayout()
        main_lay.addLayout(tools_lay)
        flipx_btn = QtWidgets.QPushButton("Flip X")
        flipx_btn.clicked.connect(partial(self.flip, vertical=False))
        tools_lay.addWidget(flipx_btn)
        
        flipx_btn = QtWidgets.QPushButton("Flip Y")
        flipx_btn.clicked.connect(partial(self.flip, vertical=True))
        tools_lay.addWidget(flipx_btn)
        
        verticalSpacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        tools_lay.addItem(verticalSpacer)
    
    
    def reset(self):
        self.scalex_spin.setValue(1.0)
        self.scaley_spin.setValue(1.0)
        self.tx_spin.setValue(0.0)
        self.ty_spin.setValue(0.0)
    
    
    def get_channels(self):
        keyframes = {}
        animEdit = None
        for pane in hou.ui.currentPaneTabs():
            if pane.type() == hou.paneTabType.ChannelEditor:
                animEdit = pane
        
        if animEdit:
            graph = animEdit.graph()
            keyframes = graph.selectedKeyframes()
            if not keyframes:
                # otherwise, just use the scoped / visible channel
                scope = hou.hscript("chscope")[0]
                
                for x in scope.split():
                    chan = hou.parm(x)
                    # only operate on channels that are visible in the graph editor
                    if chan.isSelected():
                        keyframes[chan] = chan.keyframes()
        return keyframes
    
    
    def flip(self, vertical=True):
        
        pivot = 'mm'
        for check in self.align_checks:
            if check.isChecked():
                pivot = check.property("align")
                break
        
        keyframes = self.get_channels()
        if keyframes:
            with hou.undos.group('TransformKeys'):
                if vertical:
                    transformKeyframes(keyframes, scaley=-1, autopivot=pivot, ripple=False)
                else:
                    transformKeyframes(keyframes, scalex=-1, autopivot=pivot, ripple=False)
    
    
    def transform(self):
        
        sx = self.scalex_spin.value()
        sy = self.scaley_spin.value()
        
        tx = self.tx_spin.value()
        ty = self.ty_spin.value()
        
        snap = self.snap_chk.checkState() == QtCore.Qt.Checked
        print snap
        ripple = self.ripple_chk.checkState() == QtCore.Qt.Checked
        print ripple
        pivot = 'mm'
        for check in self.align_checks:
            if check.isChecked():
                pivot = check.property("align")
                break
        
        keyframes = self.get_channels()
        if keyframes:
            with hou.undos.group('TransformKeys'):
                transformKeyframes(keyframes, scalex=sx, scaley=sy,
                                   translatex=tx, translatey=ty,
                                   snapframe=snap,
                                   ripple=ripple,
                                   autopivot=pivot)


x = TransformKeysUi()
x.show()
