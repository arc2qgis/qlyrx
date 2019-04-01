import json
from qgis.core import *
import qgis.utils
from PyQt5.QtGui import * 

layer = iface.activeLayer()
geometry_type_str = QgsWkbTypes.displayString(int(layer.wkbType()))
geometry_type = layer.wkbType()


geometry_general_type_str = geometry_type_str.replace('Multi', '').lower()  
print(geometry_general_type_str)
point2mm =  0.352778
def read_lyrx(file=None):    
    with open(file, mode="r", encoding="utf-8") as json_file:  
        data = json.load(json_file)
        #print(data)    
    return data
        
#%% 

def readValueDef(obj):
    return obj['symbol']['symbol']['symbolLayers']
    
def checkSymbolType(obj):    
    obj_arr = {}
    for o in obj:       
        if not 'desc' in obj_arr  :
            obj_arr['desc'] = []
        type = o['type']    
        if  not type in obj_arr  :
            obj_arr[type] = 0
        obj_arr[type] = obj_arr[type] + 1
        obj_arr['desc'].append(o)
    
    if 'CIMHatchFill' in obj_arr:
        obj_arr['template'] = 'hatch'
        obj_arr['template_hatch_num'] = obj_arr['CIMHatchFill']        
    else:
        obj_arr['template'] = 'simple'
        
    if 'CIMLineSymbol' in obj_arr:
        obj_arr['template_line_num'] = obj_arr['CIMLineSymbol']        
    if 'CIMSolidFill' in obj_arr:
        obj_arr['template_solid_num'] = obj_arr['CIMSolidFill']
    if 'CIMSolidStroke' in obj_arr:
        obj_arr['template_stroke_num'] = obj_arr['CIMSolidStroke']
    
    return obj_arr

def parseSolidFill(obj):    
    symbol = ""
    i = 0
    for ls in obj['desc']:
        if ls['type'] == 'CIMSolidFill':
            temp_color = ls['color']['values']
            new_color = colorToRgbArray(temp_color, ls['color']['type'])            
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(new_color)            
            i = i + 1

    # Add default shape fill.
    if symbol == '':
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            new_color = colorToRgbArray([255,255,255,0], 'CIMRGBColor')
            symbol.setColor(new_color)

    return symbol

def parseStroke(obj, symb):                
    layers = []
    i = 0
    for ls in obj['desc']:
        #print(ls)
        if ls['type'] == 'CIMSolidStroke':
            temp_color = ls['color']['values']
            new_color = colorToRgbArray(temp_color, ls['color']['type'])
            #stroke_width = ls['width'] if ls['width'] < 2 else ls['width']*point2mm             
            stroke_width = ls['width']*point2mm             
            if  i == 0:
                symb.symbolLayer(0).setStrokeColor(new_color)
                symb.symbolLayer(0).setStrokeWidth(stroke_width)                
            else :
                # Add simple line symbol layer (stroke)
                symbol_layer = QgsSimpleLineSymbolLayer()
                symbol_layer.setColor(new_color)
                symbol_layer.setWidth(stroke_width)
                # TODO: Check offset def (in poly etc)
                symbol_layer.setOffset(stroke_width/2)
                # TODO: Read join and shape
                symbol_layer.setPenJoinStyle(0)
                symb.appendSymbolLayer(symbol_layer)            
            i = i + 1            
    
    return symb   

def parseLineFill(obj):
    isDoubleHatch = False
    isOffsetEqFirstWidth = True 
    symbol = ""
    layers = []
    i = 0
    first_width = 0
    prev_hatch = 0
    for ls in obj['desc']:        
        if ls['type'] == 'CIMHatchFill':            
            symb_def = ls['lineSymbol']['symbolLayers'][0]
            # New definitions
            angle = ls['rotation'] if 'rotation' in ls else 0            
            temp_color = symb_def['color']['values']
            new_color = colorToRgbArray(temp_color, symb_def['color']['type'])
            # Hatch definitions
            fill_width = symb_def['width'] if 'width' in symb_def else 1
            fill_width = fill_width*point2mm
            fill_distance = ls['separation'] if 'separation' in ls else 0
            fill_distance = fill_distance*point2mm
            fill_offset = ls['offsetX'] if 'offsetX' in ls else 0
            fill_offset = fill_offset*point2mm
            # Create symbol
            symbol_layer = QgsLinePatternFillSymbolLayer()
            symbol_layer.setColor(new_color)
            symbol_layer.setLineAngle(angle)
            symbol_layer.setLineWidth(fill_width)
            symbol_layer.setDistance(fill_distance)            
            # Tweak save the first hatch width and use as offset
            # TODO: Real fix, mark problematic files and unusual offsets
            if prev_hatch > 0 :
                symbol_layer.setLineWidth(fill_width)
                symbol_layer.setOffset(fill_width)
                isOffsetEqFirstWidth = fill_width == prev_hatch
                isDoubleHatch = True

            layers.append(symbol_layer)
            if i == 0:
                prev_hatch = fill_width
            i = i + 1
                
    if len(layers) > 0:
        return layers
    else:
        return symbol
    
def cmyk2Rgb(cmyk_array):
    c = cmyk_array[0]
    m  = cmyk_array[1]
    y  = cmyk_array[2]
    k  = cmyk_array[3]
    
    r = int((1 - ((c + k)/100)) * 255)
    g = int((1 - ((m + k)/100)) * 255)
    b = int((1 - ((y + k)/100)) * 255)
    
    return [r, g, b]

def colorToRgbArray(color_array, type):
    new_color = QColor.fromRgb(color_array[0],color_array[1], color_array[2])        
    if type == 'CIMHSVColor':
        new_color = QColor.fromHsvF(color_array[0]/360,color_array[1]/100, color_array[2]/100,1)
    elif type == 'CIMCMYKColor':
        temp_color = cmyk2Rgb(color_array)
        new_color = QColor.fromRgb(temp_color[0],temp_color[1], temp_color[2])
    
    return new_color
    
#j_data = read_lyrx("c:/xampp/htdocs/lyrxtoqml_d/lyrx samples/plan2.lyrx")
j_data = read_lyrx("c:/xampp/htdocs/lyrxtoqml_d/lyrx samples/rami plan.lyrx")


layerDef = j_data['layerDefinitions']
renderers = [];
renderers_symb_type = []

for p in layerDef :
    print(p['name'])
    temp_renderer = p['renderer'] if 'renderer' in p else ''
    renderers.append(temp_renderer)
    if not temp_renderer == '':
        rend_type = temp_renderer['symbol']['type'] if 'symbol' in temp_renderer else  temp_renderer['defaultSymbol']['symbol']['type']
        renderers_symb_type.append(rend_type.lower())

# Find a renderer with the active layer field attribute
rend_to_check = []
x = 0
for r in renderers_symb_type:
    if geometry_general_type_str in r:
        rend_to_check.append(x)
    x = x + 1

rend_idx = -1
print(rend_to_check)
for z in rend_to_check:
    field_exist = layer.fields().indexFromName(renderers[z]['fields'][0])
    if field_exist > -1:
        rend_idx = z
#rend_idx = rend_to_check[1]
if rend_idx > -1:
    class_field = renderers[rend_idx]['fields'][0] if len(renderers[rend_idx]['fields']) > 0 else 'CODE'
    print(class_field)
    classes = renderers[rend_idx]["groups"][0]["classes"]
    symbols_labels = []
    symbol_layers = []
    symbol_values = []
    for c in classes :    
        symbol_layers.append(readValueDef(c))
        symbols_labels.append(c['label'])
        symbol_values.append(c['values'][0]['fieldValues'])

    categories = []

    idx = 0
    for sl in symbol_layers:
        symbol_def = checkSymbolType(sl)
        ret = parseSolidFill(symbol_def)    
        if not symbol_def['template'] == 'hatch':
            if 'template_stroke_num' in symbol_def and not ret == '':
                ret = parseStroke(symbol_def, ret)
            category = QgsRendererCategory(symbol_values[idx][0], ret, symbols_labels[idx])
            categories.append(category)
        elif symbol_def['template'] == 'hatch':
            print ("val :" + str(symbol_values[idx][0]))
            line_ret = parseLineFill(symbol_def)        
            if not line_ret == '':
                for line in line_ret:
                    ret.appendSymbolLayer(line)
                if 'template_stroke_num' in symbol_def and not ret == '':
                    ret = parseStroke(symbol_def, ret)   
                category = QgsRendererCategory(symbol_values[idx][0], ret, symbols_labels[idx])
                categories.append(category)
        
        idx = idx + 1


    renderer = QgsCategorizedSymbolRenderer(class_field, categories)

    # assign the created renderer to the layer
    if renderer is not None:
        iface.activeLayer().setRenderer(renderer)

    iface.activeLayer().triggerRepaint()

