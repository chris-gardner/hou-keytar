# -*- coding: UTF-8 -*-
"""
Remove flat keyframes from the scene
"""

import hou


def remove_static(node, children=False):
    
    for parm in [x for x in node.parms() if x.isTimeDependent()]:
        deletelist = []
        keyframes = parm.keyframes()
        if len(keyframes) > 1:
            lastkey = None
            blockstart = None
            for key in keyframes:
                if lastkey:
                    if key.value() == lastkey.value():
                        if blockstart is None:
                            blockstart = True
                        if blockstart is not True:
                            deletelist.append(lastkey.frame())
                    else:
                        blockstart = None
                    
                    if blockstart is True:
                        lastkey.setExpression("linear()", hou.exprLanguage.Hscript)
                        parm.setKeyframe(lastkey)
                        blockstart = False
                
                # first frame - ignore
                lastkey = key
        
        if deletelist:
            print 'Removing keys on %s' % parm
            
            for frame in deletelist:
                parm.deleteKeyframeAtFrame(frame)
    
    if children:
        if not node.isLockedHDA():
            print 'i am unlocked!!'
            for n in node.allSubChildren():
                print n.path()
                remove_static(n)


def remove_static_ui():
    if hou.selectedNodes():
        start_nodes = hou.selectedNodes()
    else:
        start_nodes = [hou.node("/")]
    
    with hou.undos.group('Remove Flat Keys'):
        for node in start_nodes:
            remove_static(node)
