#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
:mod:`cape.pyfun.cli`: Command-line interface to ``pyfun``
===========================================================

This module provides the :func:`main` function that is used by the
executable called ``pyfun``.

"""

# Standard library modules
import sys

# CAPE modules
import cape.argread
import cape.pyfun
import cape.pyfun.cli_doc
import cape.text


# Primary interface
def main():
    r"""Main interface to ``pyfun``

    This is basically an interface to :func:`cape.pyfun.cntl.Cntl.cli`. 

    :Call:
        >>> main()
    :Versions:
        * 2021-03-03 ``@ddalle``: Version 1.0
    """
    # Parse inputs
    a, kw = cape.argread.readflagstar(sys.argv)
    
    # Check for a help flag
    if kw.get('h') or kw.get("help"):
        # Get help message
        HELP_MSG = cape.pyfun.cli_doc.PYFUN_HELP
        # Display help
        print(cape.text.markdown(HELP_MSG))
        return
        
    # Get file name
    fname = kw.get('f', "pyFun.json")
    
    # Try to read it
    cntl = cape.pyfun.Cntl(fname)
    
    # Call the command-line interface
    cntl.cli(*a, **kw)


# Check if run as a script.
if __name__ == "__main__":
    main()
