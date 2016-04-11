#!/usr/bin/env python
"""
Create command strings for binary modules
=========================================

This module creates system commands as lists of strings for binaries or scripts
that require multiple command-line options.  It is closely tied to
:mod:`cape.bin`.
"""

# Import getel feature
from cape.options.util import getel

# Function get aflr3 commands
def aflr3(opts=None, j=0, **kw):
    """Create AFLR3 system command as a list of strings
    
    :Call:
        >>> cmdi = aflr3(opts=None, j=0, **kw)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface, either global, "RunControl", or "aflr3"
        *j*: :class:`int` | ``None``
            Phase number
        *blc*: :class:`bool`
            Whether or not to generate prism layers
        *blr*: :class:`float`
            Boundary layer stretching option
        *blds*: :class:`float`
            Initial surface stretching
        *angblisimx*: :class:`float`
            Max BL intersection angle
    :Outputs:
        *cmdi*: :class:`list` (:class:`str`)
            System command created as list of strings
    :Versions:
        * 2016-04-04 ``@ddalle``: First version
    """
    # Check the input type.
    if opts is not None:
        # Get values
        fi         = opts.get_aflr3_i(j)
        fo         = opts.get_aflr3_o(j)
        blc        = opts.get_blc(j)
        blr        = opts.get_blr(j)
        blds       = opts.get_blds(j)
        angblisimx = opts.get_angblisimx(j)
    else:
        fi         = getel(kw.get('i'), j)
        fo         = getel(kw.get('o'), j)
        blc        = getel(kw.get('blc'), j)
        blr        = getel(kw.get('blr'), j)
        blds       = getel(kw.get('blds'), j)
        angblisimx = getel(kw.get('angblisimx'), j)
    # Initialize command
    cmdi = ['aflr3']
    # Start with input and output files
    if fi is None:
        raise ValueError("Input file to aflr3 required")
    else:
        cmdi += ['-i', fi]
    # Check for output file
    if fo is None:
        raise ValueError("Output file for aflr3 required")
    else:
        cmdi += ['-o', fo]
    # Process boolean settings
    if blc:    cmdi.append('-blc')
    # Process flag/value options
    if blr:    cmdi += ['-blr',  str(blr)]
    if blds:   cmdi += ['-blds', str(blds)]
    # Process options that come with an equal sign
    if angblisimx: cmdi += ['angblisimx=%s' % angblisimx]
    # Output
    return cmdi
    
# Function to call verify
def intersect(opts=None, **kw):
    """Interface to Cart3D binary ``intersect``
    
    :Call:
        >>> cmd = cape.cmd.intesect(opts=None, **kw)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface
        *i*: :class:`str`
            Name of input ``tri`` file
        *o*: :class:`str`
            Name of output ``tri`` file
        *
    :Outputs:
        *cmd*: :class:`list` (:class:`str`)
            Command split into a list of strings
    :Versions:
        * 2015-02-13 ``@ddalle``: First version
    """
    # Check input type
    if opts is not None:
        # Check for "RunControl"
        opts = opts.get("RunControl", opts)
        opts = opts.get("itnersect",  opts)
        # Get settings
        fin    = opts.get('i', 'Components.tri')
        fout   = opts.get('o', 'Components.i.tri')
        cutout = opts.get('cutout')
        ascii  = opts.get('ascii', True)
        v      = opts.get('v', False)
        T      = opts.get('T', False)
        iout   = opts.get('intersect', False)
    else:
        # Get settings from inputs
        fin    = kw.get('i', 'Components.tri')
        fout   = kw.get('o', 'Components.i.tri')
        cutout = kw.get('cutout')
        ascii  = kw.get('ascii', True)
        v      = kw.get('v', False)
        T      = kw.get('T', False)
        iout   = kw.get('intersect', False)
    # Build the command.
    cmdi = ['intersect', '-i', fin, '-o', fout]
    # Type option
    if cutout: cmdi += ['-cutout', str(cutout)]
    if ascii:  cmdi.append('-ascii')
    if v:      cmdi.append('-v')
    if T:      cmdi.append('-T')
    if iout:   cmdi.append('-intersections')
    # Output
    return cmdi
    
# Function to call verify
def verify(opts=None, **kw):
    """Interface to Cart3D binary ``verify``
    
    :Call:
        >>> cmd = cape.cmd.verify(opts=None, i='Components.i.tri', **kw)
    :Inputs:
        *opts*: :class:`cape.options.Options`
            Options interface
        *i*: {``"Components.i.tri"`` | :class:`str`
            Name of *tri* file to test
        *ascii*: {``True``} | ``False``
            Flag to consider input file ASCII
        *binary*: ``True`` | {``False``}
            Flag to consider input file binary
    :Outputs:
        *cmd*: :class:`list` (:class:`str`)
            Command split into a list of strings
    :Versions:
        * 2015-02-13 ``@ddalle``: First version
    """
    # Check input type
    if opts is not None:
        # Check for "RunControl"
        opts = opts.get("RunControl", opts)
        opts = opts.get("verify", opts)
        # Get settings
        ftri  = opts.get('i', 'Components.i.tri')
        binry = opts.get('binary', False)
        ascii = opts.get('ascii', not binry)
    else:
        # Get settings from inputs
        ftri  = kw.get('i', 'Components.i.tri')
        binry = kw.get('binry', False)
        ascii = kw.get('ascii', not binry) 
    # Build the command.
    cmdi = ['verify', ftri]
    # Type
    if binry:
        # Binary triangulation
        cmdi.append('-binary')
    elif ascii:
        # ASCII triangulation
        cmdi.append('-ascii')
    # Output
    return cmd
# def verify
