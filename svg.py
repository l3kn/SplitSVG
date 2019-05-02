import xml.etree.ElementTree as ET
import copy
import sys

from named_colors import NAMED_COLORS

def plainTag(el):
    if el.tag.startswith('{'):
        return el.tag.split('}')[1]
    else:
        return el.tag

def parseStyle(style):
    """Parse style attribute into dict"""
    if style is None or style.strip() == '':
      return {}
    else:
      return dict([[part.strip() for part in prop.split(":")] for prop in style.split(";")])

def stringifyStyle(style):
    """Convert a style dict back to a string"""
    return ';'.join(['{}:{}'.format(key, value) for key, value in style.items()])

def normalizeStyle(el):
    """
    Inkscape stores fill and stroke colors in the element style.
    Store it in the element attributes instead.
    """
    style = parseStyle(el.get('style', ''))
    if 'fill' in style:
        el.set('fill', style['fill'])
        del style['fill']
    if 'stroke' in style:
        el.set('stroke', style['stroke'])
        del style['stroke']

    if len(style.items()) != 0:
        el.set('style', stringifyStyle(style))

    for child in el:
        normalizeStyle(child)

def normalizeColor(color):
    color = color.lower()
    return NAMED_COLORS.get(color, color)

def normalizeColors(el):
    if el.get('fill'):
        el.set('fill', normalizeColor(el.get('fill')))
    if el.get('stroke'):
        el.set('stroke', normalizeColor(el.get('stroke')))
    for child in el:
        normalizeColors(child)

def makeGroup(id, children):
    el = ET.Element('g', {'id': id})
    el.extend(children)
    return el

def findColors(el, res):
    """
    Recursively search the document for fill and stroke attributes
    and collect the results in a set
    """
    stroke = el.get('stroke', 'none')
    fill = el.get('fill', 'none')

    if stroke is not None and stroke != 'none':
        res.add(stroke)
    if fill is not None and fill != 'none':
        res.add(fill)

    for child in el:
        findColors(child, res)

def removeOtherColors(el, color, inherited_stroke='none', inherited_fill='none'):
    """
    Recursively remove elements with a different color than the group.
    If stroke and fill colors are different and one is correct,
    set the other to 'none' and keep the element
    """
    if plainTag(el) == 'g':
        inherited_stroke = el.get('stroke', inherited_stroke) 
        inherited_fill = el.get('fill', inherited_stroke) 

    toBeRemoved = []
    for child in el:
        removeOtherColors(child, color)

        # If a group is empty (because no element in it has the right color), remove it.
        # Don't remove layers because their fill/stroke is different
        if plainTag(child) == 'g':
            if len(child) == 0:
                toBeRemoved.append(child)
            continue

        stroke = child.get('stroke', inherited_stroke)
        fill = child.get('fill', inherited_fill)


        if stroke != 'none' and stroke != color:
            if fill == color:
                child.set('stroke', 'none')
            else:
                toBeRemoved.append(child)
                continue
            
        if fill != 'none' and fill != color:
            if stroke == color:
                child.set('fill', 'none')
            else:
                toBeRemoved.append(child)

    for tbr in toBeRemoved:
        el.remove(tbr)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: <tool> in.svg")

    in_file = sys.argv[1]

    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(in_file)
    root = tree.getroot()

    normalizeStyle(root)
    normalizeColors(root)

    colors = set()
    findColors(root, colors)

    groups = []
    for color in colors:
        r = copy.deepcopy(root)
        removeOtherColors(r, color)
        groups.append((color, r))
        # group = makeGroup(color, list(copy.deepcopy(root)))
        # removeOtherColors(group, color)
        # groups.append((color, group))

    print('Split image into %d groups' % len(groups))
    for (color, group) in groups:
        newTree = copy.deepcopy(tree)
        newTree._setroot(group)

        outFile = open('color_%s.svg' % color, 'wb')
        newTree.write(outFile)
        outFile.close()
