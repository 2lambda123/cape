#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
:mod:`cape.cfdx.cli`: Command-line interface to ``cape`` (executable)
======================================================================

This module provides the :func:`main` function that is used by the
executable called ``cape``.

"""

# Standard library modules
import sys

# CAPE modules
import cape
import cape.argread
import cape.cfdx.cfdx_doc
import cape.text


# Primary interface
def main():
    r"""Main interface to ``pyfun``

    This is basically an interface to :func:`cape.cntl.Cntl.cli`. 

    :Call:
        >>> main()
    :Versions:
        * 2021-03-04 ``@ddalle``: Version 1.0
    """
    # Parse inputs
    a, kw = cape.argread.readflagstar(sys.argv)
    
    # Check for a help flag
    if kw.get('h') or kw.get("help"):
        # Get help message
        HELP_MSG = cape.cfdx.cfdx_doc.CAPE_HELP
        # Display help
        print(cape.text.markdown(HELP_MSG))
        return
        
    # Get file name
    fname = kw.get('f', "cape.json")
    
    # Try to read it
    cntl = cape.Cntl(fname)
    
    # Call the command-line interface
    cntl.cli(*a, **kw)


# Check if run as a script.
if __name__ == "__main__":
    main()

