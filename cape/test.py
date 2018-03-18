#!/usr/bin/python
"""
:mode:`cape.test`: CAPE Testing Module
========================================

This module provides some useful methods for testing pyCart, pyFun, and pyOver
capabilities.
"""

# System interface
import os, sys
import subprocess as sp

# Paths
fcape = os.path.split(os.path.abspath(__file__))[0]
froot = os.path.split(fcape)[0]
ftest = os.path.join(froot, 'test')
# Module folders
fpycart = os.path.join(froot, 'pyCart')
fpyfun  = os.path.join(froot, 'pyFun')
fpyover = os.path.join(froot, 'pyOver')
# Module test folders
ftcape   = os.path.join(ftest, 'cape')
ftpycart = os.path.join(ftest, 'pycart')
ftpyfun  = os.path.join(ftest, 'pyfun')
ftpyover = os.path.join(ftest, 'pyover')

# Wrapper for :func:`os.system` to write error message and exit on fail
def callt(cmd, msg):
    """Call a message while checking the exit status
    
    :Call:
        >>> callt(cmd, msg)
    :Inputs:
        *cmd*: :class:`str`
            Command to run with :func:`os.system`
        *msg*: :class:`str`
            Error message to show on failure
    :Versions:
        * 2017-03-06 ``@ddalle``: First version
    """
    # Status update
    print("\n$ %s" % cmd)
    # Flush to update
    sys.stdout.flush()
    # Run the command
    ierr = os.system(cmd)
    # Check for failure
    if ierr:
        # Open a FAIL file to write error message
        f = open('FAIL', 'w')
        # Write the error message
        f.write(msg + '\n')
        # Get out of here
        f.close()
        sys.exit(ierr)
        
# Simple shell call with status
def shell(cmd, msg=None):
    """Call a command while checking the exit status
    
    The command writes ``$`` and the name of the command, *cmd* to the file
    ``test.out`` within the current working directory.  This is followed the
    contents of both STDOUT and STDERR.
    
    If the command exists with a status other than ``0``, this function raises
    an exception, writing a short message input by the user (if given) to
    ``test.out``.
    
    :Call:
        >>> shell(cmd, msg)
    :Inputs:
        *cmd*: :class:`str`
            Command to run with :func:`os.system`
        *msg*: {``None``} | :class:`str`
            Error message to show on failure
    :Versions:
        * 2018-03-17 ``@ddalle``: First version
    """
    # Open status file
    f = open("test.out", "a")
    # Status update
    f.write("\n$ %s\n" % cmd)
    # Call the command
    ierr = sp.call(cmd, shell=True, stdout=f, stderr=f)
    # Check for failure
    if ierr:
        # Check if message
        if msg is None:
            # No message
            f.write("FAILED\n")
        else:
            # Add a message
            f.write("FAILED: %s\n" % msg)
        # Close the file
        f.close()
        # Raise an exception
        raise ValueError("See status in 'test.out' file")
    else:
        # Close file
        f.close()
        
# Simple shell call with status and capturing output
def check_output(cmd, msg=None):
    """Call a command and capture the contents of STDOUT
    
    The command writes ``$`` and the name of the command, *cmd* to the file
    ``test.out`` within the current working directory.  This is followed the
    contents of both STDOUT and STDERR.
    
    If the command exists with a status other than ``0``, this function raises
    an exception, writing a short message input by the user (if given) to
    ``test.out``.
    
    :Call:
        >>> txt = check_output(cmd, msg)
    :Inputs:
        *cmd*: :class:`str`
            Command to run with :func:`os.system`
        *msg*: {``None``} | :class:`str`
            Error message to show on failure
    :Outputs:
        *txt*: :class:`str`
            Contents of STDOUT
    :Versions:
        * 2018-03-17 ``@ddalle``: First version
    """
    # Open status file
    f = open("test.out", "a")
    # Status update
    f.write("\n$ %s\n" % cmd)
    # Call the command
    txt = sp.check_output(cmd, shell=True, stderr=f)
    # Close file
    f.close()
    # Output
    return txt

# Wrapper for :func:`os.system` that raises exception on failure
def calle(cmd, msg):
    """Call a message while checking the exit status
    
    :Call:
        >>> callt(cmd, msg)
    :Inputs:
        *cmd*: :class:`str`
            Command to run with :func:`os.system`
        *msg*: :class:`str`
            Error message to show on failure
    :Versions:
        * 2017-03-06 ``@ddalle``: First version
    """
    # Status update
    print("$ %s" % cmd)
    # Run the command
    ierr = os.system(cmd)
    # Check for failure
    if ierr:
        # Raise exception
        raise ValueError(msg)
        
# Test a value
def test_val(val, targ, tol, msg=None):
    """Test a value with a target and a tolerance
    
    :Call:
        >>> test_val(val, targ, tol, msg)
    :Inputs:
        *val*: :class:`float`
            Actual value
        *targ*: :class:`float`
            Target value
        *tol*: :class:`float`
            Acceptable tolerance (using <= as test)
        *msg*: {``None``} | :class:`str`
            Error message to show on failure
    :Versions:
        * 2017-03-06 ``@ddalle``: First version
    """
    # Status update
    print("\n> abs(%s - %s) <= %s" % (val, targ, tol))
    os.sys.stdout.flush()
    # Test the value
    if abs(val - targ) > tol:
        # Open a FAIL file to write error message
        f = open('FAIL', 'w')
        # Write the error message
        if msg is None:
            # Default error message
            f.write("Data book value did not match expected result.\n")
        else:
            # Error message provided
            f.write(msg + '\n')
        # Get out of here
        f.close()
        sys.exit(1)
        
# Test a list


