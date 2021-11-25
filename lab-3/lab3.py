from __future__ import print_function
import argparse
import fontforge
import sys
import tkinter as tk

_argNameFontAttrMap = {
    'name': 'fontname',
    'family': 'familyname',
    'display_name': 'fullname',
    'weight': 'weight',
    'copyright': 'copyright',
    'font_version': 'version',
}

_weightToStyleMap = {
    'normal': (0x40, 0),
    'medium': (0x40, 0),
    'italic': (0x201, 0x2),
    'bold': (0x20, 0x1),
    'bolditalic': (0x221, 0x3),
}


def initArgumentParser():
    argParser = argparse.ArgumentParser(
            description='Convert a set of BDF files into a TrueType font (TTF). '
                        'The BDF files have to be sorted by font size in ascending order.'
    )
    argParser.add_argument(
            'bdf_file',
            nargs='+',
            help='BDF file to process.'
    )
    argParser.add_argument(
            '-n',
            '--name',
            help='Font name to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-f',
            '--family',
            help='Font family to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-N',
            '--display-name',
            help='Full font name (for display) to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-w',
            '--weight',
            help='Weight to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-c',
            '--copyright',
            help='Copyright notice to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-C',
            '--append-copyright',
            help='Copyright notice to use for generated font (appends to notice taken from first BDF file).'
    )
    argParser.add_argument(
            '-V',
            '--font-version',
            help='Font version to use for generated font (default: taken from first BDF file).'
    )
    argParser.add_argument(
            '-a',
            '--prefer-autotrace',
            action='store_true',
            help='Prefer AutoTrace over Potrace, if possible (default: %(default)s).'
    )
    argParser.add_argument(
            '-A',
            '--tracer-args',
            default='',
            help='Additional arguments for AutoTrace/Potrace (default: none).'
    )
    argParser.add_argument(
            '-s',
            '--visual-studio-fixes',
            action='store_true',
            help='Make generated font compatible with Visual Studio (default: %(default)s).'
    )
    argParser.add_argument(
            '-O',
            '--os2-table-tweaks',
            action='store_true',
            help='Tweak OS/2 table according to the font weight. This may be needed for some '
                 'buggy FontForge versions which do not do this by themselves.'
    )
    argParser.add_argument(
            '--no-background',
            action='store_true',
            help='Do not import the largest font into the glyph background. This is useful only '
                 'when the font already has a suitable glyph background, and you do not want to '
                 'overwrite it. Only for special use cases.'
    )

    return argParser


def setFontAttrsFromArgs(font, args):
    for argName in _argNameFontAttrMap:
        argValue = getattr(args, argName)
        if argValue is not None:
            setattr(
                    font,
                    _argNameFontAttrMap[argName],
                    argValue
            )

args = initArgumentParser().parse_args()
fontforge.setPrefs("PreferPotrace", not args.prefer_autotrace)
fontforge.setPrefs("AutotraceArgs", args.tracer_args)
try:
    baseFont = fontforge.open(args.bdf_file[0])
except EnvironmentError as e:
    sys.exit("Could not open base font `%s'!" % args.bdf_file[0])
print('Importing bitmaps from %d additional fonts...' % (len(args.bdf_file) - 1))
for fontFile in args.bdf_file[1:]:
    try:
        baseFont.importBitmaps(fontFile)
    except EnvironmentError as e:
        sys.exit("Could not import additional font `%s'!" % fontFile)
if not args.no_background:
    try:
        print("Importing font `%s' into glyph background..." % args.bdf_file[-1])
        baseFont.importBitmaps(args.bdf_file[-1], True)
    except EnvironmentError as e:
        sys.exit("Could not import font `%s' into glyph background: %s" % (args.bdf_file[-1], e))
else:
    print("Skipping import of font `%s' into glyph background, as requested." % args.bdf_file[-1])
setFontAttrsFromArgs(baseFont, args)
if args.append_copyright is not None:
    baseFont.copyright += args.append_copyright
baseFont.os2_vendor = 'PfEd'
if args.os2_table_tweaks:
    if not hasattr(baseFont, "os2_stylemap"):
        sys.exit("You requested OS/2 table tweaks, but your FontForge version is too old for these "
                 "tweaks to work.")

    os2_weight = baseFont.weight.lower()
    if os2_weight == "medium" and baseFont.fontname.lower().endswith("italic"):
        os2_weight = "italic"
    elif os2_weight == "bold" and baseFont.fontname.lower().endswith("italic"):
        os2_weight = "bolditalic"

    try:
        styleMap, macStyle = _weightToStyleMap[os2_weight]
    except KeyError:
        sys.exit("Cannot tweak OS/2 table: No tweaks defined for guessed font weight `%s'!" % os2_weight)

    print(
            "OS/2 table tweaks: Guessed weight is `%s' -> Adding %#x to StyleMap and %#x to macStyle." % (
                os2_weight,
                styleMap,
                macStyle
        )
    )
    baseFont.os2_stylemap |= styleMap
    baseFont.macstyle |= macStyle
print('Processing glyphs...')
baseFont.selection.all()
baseFont.autoTrace()
baseFont.addExtrema()
baseFont.simplify()
basename = baseFont.fontname
if baseFont.version != '':
    basename += '-' + baseFont.version

print('Saving TTF file...')
baseFont.generate(basename + '.ttf', 'ttf')
print('Done!')

root = tk.Tk()
root.title('Program')
root.geometry("500x500")
textExample = tk.Text(root, heigh=10)
textExample.pack()
textExample.configure(font=(basename, 16, "italic"))
root.mainloop()