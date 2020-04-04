from PySide2 import QtWidgets, QtCore
from functools import partial
from fractions import Fraction


def tween(parm, frame, blend):
    # print "BEFORE", frame
    before = list(parm.keyframesBefore(frame))
    for k in before:
        if k.frame() == frame:
            before.remove(k)
    # print before
    
    # print "AFTER", frame
    after = list(parm.keyframesAfter(frame))
    for k in after:
        if k.frame() == frame:
            after.remove(k)
    # print after
    # print "AFTER",  hou.frameToTime(frame)
    # print parm.keyframesAfter(frame)
    
    if len(before) > 0 and len(after) > 0:
        previous = before[-1]
        next = after[0]
        
        prev_val = previous.value()
        next_val = next.value()
        
        # print previous.frame(), prev_val, next.frame(), next_val
        
        # straight up lerp
        new_value = prev_val * (1 - blend) + next_val * blend
        
        # or eval curve at a blended time
        # eval_frame = previous.frame() * (1 - blend) + next.frame() * blend
        # new_value = parm.evalAtFrame(eval_frame)
        
        hou.hscript('chkey -f %f -v %f -T "amvAMV" -o "amvAMV" %s' % (frame, new_value, parm.path()))


class TweenMachineUi(QtWidgets.QDialog):
    def __init__(self):
        super(TweenMachineUi, self).__init__(hou.ui.mainQtWindow())
        
        self.setWindowTitle('Tween Machine')
        self.setWindowFlags(QtCore.Qt.Tool)
        # self.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)
        
        self.blendSlider = QtWidgets.QSlider()
        self.blendSlider.setOrientation(QtCore.Qt.Horizontal)
        self.blendSlider.setMinimum(0)
        self.blendSlider.setMaximum(100)
        self.blendSlider.setValue(50)
        self.blendSlider.setTickInterval(10)
        self.blendSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        main_layout.addWidget(self.blendSlider)
        
        quick_layout = QtWidgets.QHBoxLayout()
        self.quick_buttons = []
        for i in range(7):
            # change range from -1 to 1
            val = ((float(i) / 6) * 2 - 1)
            # fancy fraction label
            # https://stackoverflow.com/questions/23344185/how-to-convert-a-decimal-number-into-fraction
            label = str(Fraction.from_float(val).limit_denominator())
            btn = QtWidgets.QPushButton(label)
            self.quick_buttons.append(btn)
            quick_layout.addWidget(btn)
            
            btn.clicked.connect(partial(self.quick_blend, (float(i) / 6)))
        
        main_layout.addLayout(quick_layout)
        
        self.blendButton = QtWidgets.QPushButton("Blend")
        self.blendButton.clicked.connect(self.slider_blend)
        main_layout.addWidget(self.blendButton)
    
    
    def quick_blend(self, blend):
        self.blendSlider.setValue(int(blend * 100))
        self.blend(blend)
    
    
    def slider_blend(self):
        blend = float(self.blendSlider.value()) / 100.0
        self.blend(blend)
    
    
    def blend(self, blend):
        animEdit = None
        for pane in hou.ui.currentPaneTabs():
            if pane.type() == hou.paneTabType.ChannelEditor:
                animEdit = pane
        
        if animEdit:
            graph = animEdit.graph()
            keyframes = graph.selectedKeyframes()
            # if there are keyframes selected
            # tween those
            if keyframes:
                for parm in keyframes.keys():
                    for key in keyframes[parm]:
                        tween(parm, key.frame(), blend)
                return
        
        # otherwise, just use the scoped / visible channels at the current time
        scope = hou.hscript("chscope")[0]
        for x in scope.split():
            chan = hou.parm(x)
            # only operate on channels that are visible in the graph editor
            if chan.isSelected():
                tween(chan, hou.frame(), blend)


x = TweenMachineUi()
x.show()
