"""
:mod:`cape.pyfun.tecplot`: Interface to FUN3D Tecplot scripts 
==============================================================

This is a module built off of the :mod:`cape.filecntl` module customized for
manipulating Tecplot layout files and macros.  The FUN3D version of this
module is based off of the generic version :mod:`cape.filecntl.tecplot` with minimal
modifications.

The module allows users to edit quantities of any layout command in addition to
declaring and adding layout variables. In addition, the :func:`ExportLayout`
function provides a utility to open a layout using Tecplot in batch mode to
export an image.

The class provides two classes, the first of which is the generic version
typically used for layout files.  The second class has a few extra methods for
handling Tecplot macros specifically.

    * :class:`cape.pyfun.tecplot.Tecsript`
    * :class:`cape.pyfun.tecplot.TecMacro`

:See also:
    * :mod:`cape.filecntl`
    * :mod:`cape.cfdx.report`
"""

# Import the base file control class.
import cape.filecntl.tecplot


# Stand-alone function to run a Tecplot layout file
def ExportLayout(lay="layout.lay", fname="export.png", fmt="PNG", w=None):
    """Stand-alone function to open a layout and export an image
    
    :Call:
        >>> ExportLayout(lay="layout.lay", fname="export.png", fmt="PNG", w=None)
    :Inputs:
        *lay*: {``"layout.lay"``} | :class:`str`
            Name of Tecplot layout file
        *fname*: {``"export.png"``} | :class:`str`
            Name of image file to export
        *fmt*: {``"PNG"``} | ``"JPG"`` | :class:`str`
            Valid image format for Tecplot export
        *w*: {``None``} | :class:`float`
            Image width in pixels
    :Versions:
        * 2015-03-10 ``@ddalle``: First version
    """
    cape.filecntl.tecplot.ExportLayout(lay=lay, fname=fname, fmt=fmt, w=w)
    
# Aerodynamic history class
class Tecscript(cape.filecntl.tecplot.Tecscript):
    """
    File control class for Tecplot script files
    
    :Call:
        >>> tec = pyfun.tecplot.Tecscript()
        >>> tec = pyfun.tecplot.Tecscript(fname="layout.lay")
    :Inputs:
        *fname*: :class:`str`
            Name of Tecplot script to read
    :Outputs:
        *tec*: :class:`pyfun.tecplot.Tecscript`
            Instance of Tecplot script base class
    :Versions:
        * 2015-02-26 ``@ddalle``: Started
        * 2015-03-10 ``@ddalle``: First version
    """
    pass

# class Tecscript


# Tecplot macro
class TecMacro(cape.filecntl.tecplot.TecMacro):
    """
    File control class for Tecplot macr files
    
    :Call:
        >>> tec = TecMacro()
        >>> tec = TecMacro(fname="export.mcr")
    :Inputs:
        *fname*: :class:`str`
            Name of Tecplot script to read
    :Outputs:
        *tec*: :class:`pyfun.tecplot.TecMacro`
            Instance of Tecplot macro interface
    :Versions:
        * 2015-03-10 ``@ddalle``: First version
    """
    pass

# class TecMacro

