import sys, os
import datetime
from datetime import datetime
sys.path.append("./exportVRML")
import exportPartToVRML as expVRML
import shaderColors

dstDir = "exports/"
srcDir = "feeds/"

tmplName = 'molexTemplate'

from collections import namedtuple
import FreeCAD, FreeCADGui
import random
import ImportGui
import importDXF

bodyName = 'SOLID'
fpName = 'COMPOUND'

def export(variant, overwrite=False, saveFCStd=False, exportDXF=False):
    partPrefix = variant[:-4]
    partPostfix = variant[5:]
    pinCount = int(variant[5:7])

    srcName = srcDir+variant+'.stp'
    if not os.path.isfile(srcName):
        FreeCAD.Console.PrintMessage('missing ' + variant + '.stp\n')
        return

    if not os.path.exists(dstDir):
        os.makedirs(dstDir)

    bodyCutName = 'body-' + partPrefix + '#'

    bodyCut = None
    try:
        tmpl = App.getDocument(tmplName)
    except:
        tmpl = App.openDocument(tmplName+'.FCStd')
    for obj in tmpl.Objects:
        if obj.Label.startswith(bodyCutName):
            bodyCut = obj
            break

    if bodyCut == None:
        FreeCAD.Console.PrintMessage('missing template for ' + partPrefix + '\n')
        return

    FreeCAD.Console.PrintMessage('cehcking  ' + variant + '\n')

    names = [x for x in obj.Label.split('#')]
    pitch = float(names[2])
    dstName = dstDir+names[3]\
            .replace('%e',partPrefix)\
            .replace('%o',partPostfix)\
            .replace('%c','%02d'%pinCount)\
            .replace('%p','%.2fmm'%pitch)


    if os.path.isfile(dstName+'.stp'):
        if not overwrite:
            FreeCAD.Console.PrintMessage(dstName + ' already exists, skip!\n')
            return

    FreeCAD.Console.PrintMessage('exporting ' + dstName + '\n')

    newDoc = App.newDocument(variant+'_'+str(random.randrange(10000,99999)))
    guiDoc = Gui.getDocument(newDoc.Name)

    bodyCut = newDoc.copyObject(bodyCut,True)
    guiDoc.getObject(bodyCut.Name).Visibility = False;

    ImportGui.insert(srcName,newDoc.Name)

    objs = newDoc.getObjectsByLabel(bodyName)
    if not objs:
        FreeCAD.Console.PrintMessage('missing body for ' + partPrefix + '\n')
        return
    part = objs[0]
    guiDoc.getObject(part.Name).Visibility = False;

    objs = newDoc.getObjectsByLabel(fpName)
    if not objs:
        FreeCAD.Console.PrintMessage('missing footprint for ' + partPrefix + '\n')
        return
    footprint = objs[0]

    placement = bodyCut.Placement
    bodyCut.Placement = App.Placement()

    for obj in bodyCut.Shapes:
        # any better way to id array object?
        if 'ArrayType' in obj.PropertiesList:
            # TODO, we assum interval x sets the pitch, add more check later
            obj.IntervalX.x = pitch
            obj.NumberX = pinCount
            obj.Placement.Base.x -= (pinCount-2)*pitch/2
        else:
            for sobj in obj.Shapes:
                if sobj.TypeId == 'Part::Mirroring':
                    sobj.Source.Placement.Base.x -= (pinCount-2)*pitch/2

    newDoc.recompute()

    colors = []
    objs = []
    shapes = []

    def make_part(obj,isCut):
        names = [x for x in obj.Label.split('#')]
        newObj = newDoc.addObject("Part::Feature", names[0])
        if isCut:
            newObj.Shape = part.Shape.cut(obj.Shape).removeSplitter()
        else:
            newObj.Shape = part.Shape.common(obj.Shape).removeSplitter()
        color = names[1]
        if not color in shaderColors.named_colors:
            FreeCAD.Console.PrintWarning('unknown color : ' + color + '\n')
            color = None
        else:
            newObj.ViewObject.ShapeColor = shaderColors.named_colors[color].getDiffuseFloat()
            if not color in colors:
                colors.append(color)
        newObj.Placement = placement
        shapes.append(newObj)
        objs.append(expVRML.exportObject(freecad_object = newObj, shape_color=color, face_colors=None))

    make_part(bodyCut,True)

    for obj in bodyCut.Shapes:
        make_part(obj,False)

    newDoc.recompute()

    ImportGui.export(shapes,dstName+'.stp')

    if exportDXF:
        shapes = []
        shapes.append(footprint)
        importDXF.export(shapes,dstName+'.dxf')

    scale=1/2.54
    colored_meshes = expVRML.getColoredMesh(Gui, objs , scale)
    expVRML.writeVRMLFile(colored_meshes, dstName+'.wrl', colors)

    if saveFCStd:
        newDoc.saveAs(dstName+'.FCStd')
    App.closeDocument(newDoc.Name)

if __name__ == "__main__":

    if len(sys.argv) < 3:
        for subdirs,dirs,files in os.walk(srcDir):
            for f in files:
                fname = os.path.splitext(f)
                if fname[1] == '.stp':
                    export(fname[0])
    else:
        export(sys.argv[2])
