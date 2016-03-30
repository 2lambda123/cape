"""
Utilities for pyFun Options module: :mod:`pyFun.options.util`
=============================================================

This module provides tools to read, access, modify, and write settings for
:mod:`pyFun`.  The class is based off of the built-int :class:`dict` class, so
its default behavior, such as ``opts['InputCntl']`` or 
``opts.get('InputCntl')`` are also present.  In addition, many convenience
methods, such as ``opts.set_it_fc(n)``, which sets the number of
:file:`flowCart` iterations,  are provided.

In addition, this module controls default values of each pyCart
parameter in a two-step process.  The precedence used to determine what the
value of a given parameter should be is below.

    *. Values directly specified in the input file, :file:`pyCart.json`
    
    *. Values specified in the default control file,
       :file:`$PYFUN/settings/pyFun.default.json`
    
    *. Hard-coded defaults from this module
"""

# Import CAPE options utilities
from cape.options.util import *

# Get the root directory of the module.
_fname = os.path.abspath(__file__)

# Saved folder names
PyFunFolder = os.path.split(os.path.split(_fname)[0])[0]

# Backup default settings
rc["project_rootname"]     ="pyfun"
rc["grid_format"]          = "aflr3"
rc["nodet_animation_freq"] = -1
# Solution mode settings
rc["KeepRestarts"] = False
# Mesh settings
rc["BCFile"] = "pyfun.mapbc"
# Adaptation settings
rc["Adaptive"]   = False
rc["Dual"]       = False
rc["AdaptPhase"] = True
rc["DualPhase"]  = True
    

# Function to ensure scalar from above
def rc0(p):
    """
    Return default setting from ``pyCart.options.rc``, but ensure a scalar
    
    :Call:
        >>> v = rc0(s)
    :Inputs:
        *s*: :class:`str`
            Name of parameter to extract
    :Outputs:
        *v*: any
            Either ``rc[s]`` or ``rc[s][0]``, whichever is appropriate
    :Versions:
        * 2014-08-01 ``@ddalle``: First version
    """
    # Use the `getel` function to do this.
    return getel(rc[p], 0)


# Function to get the defautl settings.
def getPyFunDefaults():
    """
    Read :file:`pyCart.default.json` default settings configuration file
    
    :Call:
        >>> defs = getPyFunDefaults()
    :Outputs:
        *defs*: :class:`dict`
            Dictionary of settings read from JSON file
    :Versions:
        * 2014-06-03 ``@ddalle``: First version
        * 2014-07-28 ``@ddalle``: Moved to new options module
    """
    # Read the fixed default file.
    lines = open(os.path.join(PyFunFolder, 
        "..", "settings", "pyFun.default.json")).readlines()
    # Strip comments and join list into a single string.
    lines = expandJSONFile(lines)
    # Process the default input file.
    return json.loads(lines)


