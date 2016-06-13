#!/usr/bin/env python
"""
Convert STEP File to Plot3D Multiple Curve File
===============================================

Convert a '.uh3d' file to a Cart3D triangulation format.

:Call:

    .. code-block:: console
    
        $ pc_Step2Crv.py STP CRV [OPTIONS]

:Inputs:
    * *STP*: Name of input ``'.stp`` or ``.step`` file
    * *CRV*: Name of output Plot3D file
    
:Options:
    -h, --help
        Display this help message and exit
        
    -i STP
        Use *STP* as input file
        
    -o CRV
        Use *CRV* as name of created output file
        
    -n N
        Use a minimum of *N* segments per curve (defaults to ``3``)
        
    -ds DS
        Use a maximum arc length of *DS* on each curve
        
    -dth THETA
        Make sure maximum turning angle is below *THETA*
        
    -da PHI
        Make sure maximum turning angle times length of adjoining segments is
        less than or equal to *PHI*
    
    --link
        Link curves and sort by ascending *x* coordinate (default)
        
    --link AXIS
        Link curves and sort by *AXIS*, for example ``+x``, ``-y``, etc.
        
    --no-link
        Do not link curves together or sort
        
    -xtol XTOL
        Truncate nodal coordinates within *XTOL* of x=0 plane to zero
        
    -ytol YTOL
        Truncate nodal coordinates within *YTOL* of y=0 plane to zero
        
    -ztol ZTOL
        Truncate nodal coordinates within *ZTOL* of z=0 plane to zero
    
If the name of the output file is not specified, it will just add '.tri' as the
extension to the input (deleting '.uh3d' if possible).

:Versions:
    * 2016-05-10 ``@ddalle``: First version
"""

# Get the pyCart module.
import cape.step
# Module to handle inputs and os interface
import sys
# Command-line input parser
import cape.argread as argr

# Main function
def Step2Crv(*a, **kw):
    """
    Read the curves from a STEP file and write to a Plot3D multiple curve file
    
    :Call:
        >>> Step2Crv(fstp, fcrv, **kw)
        >>> Step2Crv(i=fstp, o=fcrv, **kw)
    :Inputs:
        *fstp*: :class:`str`
            Name of input file
        *fcrv*: :class:`str`
            Name of output file (defaults to value of *fstp* but with ``.crv``
            as the extension in the place of ``.stp`` or ``.step``)
        *n*: :class:`int`
            Number of intervals to use
        *ds*: :class:`float`
            Upper bound of uniform spacing
        *dth*: :class:`float` | {``None``}
            Maximum allowed turning angle in degrees
        *da*: :class:`float` | {``None``}
            Maximum allowed length-weighted turning angle
        *link*: {``True``} | ``False`` | ``"x"`` | ``"-x"``
            Whether or not to link curves and if so using which axis to sort
        *xtol*: :class:`float` | :class:`str`
            Tolerance for *x*-coordinates to be truncated to zero
        *ytol*: :class:`float` | :class:`str`
            Tolerance for *y*-coordinates to be truncated to zero
        *ztol*: :class:`float` | :class:`str`
            Tolerance for *z*-coordinates to be truncated to zero
    :Versions:
        * 2016-05-10 ``@ddalle``: First version
    """
    # Get the file pyCart settings file name.
    if len(a) == 0:
        # Defaults
        fstp = None
    else:
        # Use the first general input.
        fstp = a[0]
    # Prioritize a "-i" input.
    fstp = kw.get('i', fstp)
    # Must have a file name.
    if fstp is None:
        # Required input.
        print __doc__
        raise IOError("Input file not specified.")
        sys.exit(1)
    
    # Get the file pyCart settings file name.
    if len(a) <= 2:
        # Defaults
        fcrv = fstp.rstrip('stp').rstrip('step') + 'crv'
    else:
        # Use the first general input.
        fcrv = a[1]
    # Prioritize a "-i" input.
    fcrv = kw.get('o', fcrv)
        
    # Read in the STEP file
    stp = cape.step.STEP(fstp,
        xtol=kw.get('xtol'), ytol=kw.get('ytol'), ztol=kw.get('ztol'))
    
    # Sampling options
    n   = kw.get('n', 3)
    ds  = kw.get('ds')
    dth = kw.get('dth')
    da  = kw.get('da')
    # Convert as necessary
    if n   is not None: n   = int(n)
    if ds  is not None: ds  = float(ds)
    if dth is not None: dth = float(dth)
    if da  is not None: da  = float(da)
    
    # Sample curves
    stp.SampleCurves(n=n, ds=ds, dth=dth, da=da)
    
    # Get link options
    nlnk = kw.get('no-link') 
    axis = kw.get('link', 'x')
    # Link/sort as requested
    if nlnk != True and axis == True and axis != False:
        # Default sorting
        stp.LinkCurves()
    elif nlnk != True and axis != False:
        # Specialized sorting
        stp.LinkCurves(axis=axis)
    
    # Write it.
    stp.WritePlot3DCurves(fcrv, bin=False)
    

# Only process inputs if called as a script!
if __name__ == "__main__":
    # Process the command-line interface inputs.
    (a, kw) = argr.readkeys(sys.argv)
    # Check for a help option.
    if kw.get('h',False) or kw.get('help',False):
        print __doc__
        sys.exit()
    # Run the main function.
    Step2Crv(*a, **kw)
    