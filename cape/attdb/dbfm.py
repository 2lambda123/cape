#!/us/bin/env python
# -*- coding: utf-8 -*-
r"""
-----------------------------------------------------------------
:mod:`cape.attdb.dbfm`: Aero Task Team Force & Moment Databases
-----------------------------------------------------------------

This module provides customizations of :mod:`cape.attdb.rdb` that are
especially useful for launch vehicle force & moment databases.  The
force & moment coefficient names follow common missile naming
conventions:

    =======  ===============  ============================
    Name     Symbol           Description
    =======  ===============  ============================
    *CA*     :math:`C_A`      Axial force
    *CY*     :math:`C_Y`      Side force
    *CN*     :math:`C_N`      Normal force
    *CLL*    :math:`C_\ell`   Rolling moment
    *CLM*    :math:`C_m`      Pitching moment
    *CLN*    :math:`C_n`      Yawing moment
    =======  ===============  ============================


"""

# Standard library modules
import os
import sys

# Third-party modules
import numpy as np

# CAPE modules
import cape.attdb.convert as convert
import cape.tnakit.kwutils as kwutils

# Local modules
from . import rdb
from . import rdbaero


# Sets of common variable names
_alpha_cols = rdbaero.AeroDataKit._tagcols["alpha"]
_aoap_cols  = rdbaero.AeroDataKit._tagcols["aoap"]
_aoav_cols  = rdbaero.AeroDataKit._tagcols["aoav"]
_beta_cols  = rdbaero.AeroDataKit._tagcols["beta"]
_phip_cols  = rdbaero.AeroDataKit._tagcols["phip"]
_phiv_cols  = rdbaero.AeroDataKit._tagcols["phiv"]


# Standard converters: alpha
def convert_alpha(*a, **kw):
    r"""Determine angle of attack from *kwargs*

    All keyword args are listed by ``"Tag"``. For example, instead of
    *alpha*, the user may also use *ALPHA*, *aoa*, or any col in
    *AeroDataKit._tagcols["alpha"]*.
    
    :Call:
        >>> alpha = convert_alpha(*a, **kw)
    :Inputs:
        *a*: :class:`tuple`
            Positional args; discarded here
        *alpha*: :class:`float` | :class:`np.ndarray`
            Direct alias from *_alpha_cols*
        *aoap*: :class:`float` | :class:`np.ndarray`
            Total angle of attack [deg]
        *phip*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Vertical-to-wind roll angle [deg]
        *aoav*: :class:`float` | :class:`np.ndarray`
            Missile-axis angle of attack [deg]
        *phiv*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Missile-axis roll angle [deg]
    :Outputs:
        *alpha*: ``None`` | :class:`float` | :class:`np.ndarray`
            Angle of attack [deg]
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-19 ``@ddalle``: Using :class:`AeroDataKit`
    """
   # --- Direct ---
    # Check for alias
    for col in _alpha_cols:
        # Check if present
        if col in kw:
            # Return that
            return kw[col]
   # --- aoap, phip ---
    # Get total angle of attack
    for col in _aoap_cols:
        # Get total angle of attack
        aoap = kw.get(col)
        # Check
        if aoap is not None:
            break
    # Get roll angle
    for col in _phip_cols:
        # Get total angle of attack
        phip = kw.get(col)
        # Check
        if phip is not None:
            break
    # Check if both are present
    if (aoap is not None):
        # Default roll angle
        if phip is None:
            phip = 0.0
        # Convert to alpha/beta
        alpha, _ = convert.AlphaTPhi2AlphaBeta(aoap, phip)
        # Return *alpha*; discard *beta*
        return alpha
   # --- aoav, phiv ---
    # Get missile-axis angle of attack
    for col in _aoav_cols:
        # Get total angle of attack
        aoav = kw.get(col)
        # Check
        if aoav is not None:
            break
    # Get missile-axis roll angle
    for col in _phiv_cols:
        # Get total angle of attack
        phiv = kw.get(col)
        # Check
        if phiv is not None:
            break
    # Check if both are present
    if (aoav is not None):
        # Default roll angle
        if phiv is None:
            phiv = 0.0
        # Convert to alpha/beta
        alpha, _ = convert.AlphaTPhi2AlphaBeta(aoav, phiv)
        # Return *alpha*; discard *beta*
        return alpha


# Standard converters: beta
def convert_beta(*a, **kw):
    r"""Determine sideslip angle from *kwargs*

    All keyword args are listed by ``"Tag"``. For example, instead of
    *alpha*, the user may also use *ALPHA*, *aoa*, or any col in
    *AeroDataKit._tagcols["alpha"]*.
    
    :Call:
        >>> beta = convert_beta(*a, **kw)
    :Inputs:
        *a*: :class:`tuple`
            Positional args; discarded here
        *beta*: :class:`float` | :class:`np.ndarray`
            Direct alias from *_alpha_cols*
        *aoap*: :class:`float` | :class:`np.ndarray`
            Total angle of attack [deg]
        *phip*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Vertical-to-wind roll angle [deg]
        *aoav*: :class:`float` | :class:`np.ndarray`
            Missile-axis angle of attack [deg]
        *phiv*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Missile-axis roll angle [deg]
    :Outputs:
        *beta*: :class:`float` | :class:`np.ndarray`
            Sideslip angle [deg]
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-19 ``@ddalle``: Using :class:`AeroDataKit`
    """
   # --- Direct ---
    # Check for alias
    for col in _beta_cols:
        # Check if present
        if col in kw:
            # Return that
            return kw[col]
   # --- aoap, phip ---
    # Get total angle of attack
    for col in _aoap_cols:
        # Get total angle of attack
        aoap = kw.get(col)
        # Check
        if aoap is not None:
            break
    # Get roll angle
    for col in _phip_cols:
        # Get total angle of attack
        phip = kw.get(col)
        # Check
        if phip is not None:
            break
    # Check if both are present
    if (aoap is not None):
        # Default roll angle
        if phip is None:
            phip = 0.0
        # Convert to alpha/beta
        _, beta = convert.AlphaTPhi2AlphaBeta(aoap, phip)
        # Discard *alpha*; return *beta*
        return beta
   # --- aoav, phiv ---
    # Get missile-axis angle of attack
    for col in _aoav_cols:
        # Get total angle of attack
        aoav = kw.get(col)
        # Check
        if aoav is not None:
            break
    # Get missile-axis roll angle
    for col in _phiv_cols:
        # Get total angle of attack
        phiv = kw.get(col)
        # Check
        if phiv is not None:
            break
    # Check if both are present
    if (aoav is not None):
        # Default roll angle
        if phiv is None:
            phiv = 0.0
        # Convert to alpha/beta
        _, beta = convert.AlphaTPhi2AlphaBeta(aoav, phiv)
        # Discard *alpha*; return *beta*
        return beta


# Standard converters: aoap
def convert_aoap(*a, **kw):
    r"""Determine total angle of attack from *kwargs*

    All keyword args are listed by ``"Tag"``. For example, instead of
    *alpha*, the user may also use *ALPHA*, *aoa*, or any col in
    *AeroDataKit._tagcols["alpha"]*.
    
    :Call:
        >>> aoap = convert_aoap(*a, **kw)
    :Inputs:
        *a*: :class:`tuple`
            Positional args; discarded here
        *aoap*: :class:`float` | :class:`np.ndarray`
            Total angle of attack [deg]
        *alpha*: :class:`float` | :class:`np.ndarray`
            Angle of attack [deg]
        *beta*: :class:`float` | :class:`np.ndarray`
            Direct alias from *_alpha_cols*
        *aoav*: :class:`float` | :class:`np.ndarray`
            Missile-axis angle of attack [deg]
        *phiv*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Missile-axis roll angle [deg]
    :Outputs:
        *aoap*: :class:`float` | :class:`np.ndarray`
            Total angle of attack [deg]
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-19 ``@ddalle``: Using :class:`AeroDataKit`
    """
   # --- Direct ---
    # Check for alias
    for col in _aoap_cols:
        # Check if present
        if col in kw:
            # Return that
            return kw[col]
   # --- alpha, beta ---
    # Get angle of attack
    for col in _alpha_cols:
        # Get total angle of attack
        a = kw.get(col)
        # Check
        if a is not None:
            break
    # Get sideslip angle
    for col in _beta_cols:
        # Get total angle of attack
        b = kw.get(col)
        # Check
        if b is not None:
            break
    # Check if both are present
    if (a is not None):
        # Default roll angle
        if b is None:
            b = 0.0
        # Convert to aoap/phip
        aoap, _ = convert.AlphaBeta2AlphaTPhi2(a, b)
        # Return *aoap*; discard *phip*
        return aoap
   # --- aoav, phiv ---
    # Get missile-axis angle of attack
    for col in _aoav_cols:
        # Get total angle of attack
        aoav = kw.get(col)
        # Check
        if aoav is not None:
            break
    # Get missile-axis roll angle
    for col in _phiv_cols:
        # Get total angle of attack
        phiv = kw.get(col)
        # Check
        if phiv is not None:
            break
    # Check if both are present
    if (aoav is not None):
        # Default roll angle
        if phiv is None:
            phiv = 0.0
        # Convert to alpha/beta
        aoap, _ = convert.AlphaMPhi2AlphaTPhip(aoav, phiv)
        # Return *aoap*; discard *phip*
        return aoap


# Standard converters: phip
def convert_phip(*a, **kw):
    r"""Determine body-to-wind roll angle from *kwargs*

    All keyword args are listed by ``"Tag"``. For example, instead of
    *alpha*, the user may also use *ALPHA*, *aoa*, or any col in
    *AeroDataKit._tagcols["alpha"]*.
    
    :Call:
        >>> phip = convert_phip(*a, **kw)
    :Inputs:
        *a*: :class:`tuple`
            Positional args; discarded here
        *phip*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Vertical-to-wind roll angle [deg]
        *alpha*: :class:`float` | :class:`np.ndarray`
            Angle of attack [deg]
        *beta*: :class:`float` | :class:`np.ndarray`
            Direct alias from *_alpha_cols*
        *aoav*: :class:`float` | :class:`np.ndarray`
            Missile-axis angle of attack [deg]
        *phiv*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Missile-axis roll angle [deg]
    :Outputs:
        *phip*: {``0.0``} | :class:`float` | :class:`np.ndarray`
            Vertical-to-wind roll angle [deg]
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-19 ``@ddalle``: Using :class:`AeroDataKit`
    """
   # --- Direct ---
    # Check for alias
    for col in _phip_cols:
        # Check if present
        if col in kw:
            # Return that
            return kw[col]
   # --- alpha, beta ---
    # Get angle of attack
    for col in _alpha_cols:
        # Get total angle of attack
        a = kw.get(col)
        # Check
        if a is not None:
            break
    # Get sideslip angle
    for col in _beta_cols:
        # Get total angle of attack
        b = kw.get(col)
        # Check
        if b is not None:
            break
    # Check if both are present
    if (a is not None):
        # Default roll angle
        if b is None:
            b = 0.0
        # Convert to aoap/phip
        _, phip = convert.AlphaBeta2AlphaTPhi2(a, b)
        # Discard *aoap*; return *phip*
        return phip
   # --- aoav, phiv ---
    # Get missile-axis angle of attack
    for col in _aoav_cols:
        # Get total angle of attack
        aoav = kw.get(col)
        # Check
        if aoav is not None:
            break
    # Get missile-axis roll angle
    for col in _phiv_cols:
        # Get total angle of attack
        phiv = kw.get(col)
        # Check
        if phiv is not None:
            break
    # Check if both are present
    if (aoav is not None):
        # Default roll angle
        if phiv is None:
            phiv = 0.0
        # Convert to alpha/beta
        _, phip = convert.AlphaMPhi2AlphaTPhip(aoav, phiv)
        # Discard *aoap*; return *phip*
        return phip


# Special evaluators: CLM vs x
def eval_CLMX(db, *a, **kw):
    r"""Evaluate *CLM* about arbitrary *x* moment reference point
    
    :Call:
        >>> CLMX = eval_CLMX(db, *a, **kw)
    :Inputs:
        *db*: :class:`DBFM`
            Force & moment data kit
        *a*: :class:`tuple`
            Arguments to call ``db("CLM", *a)`` [plus *xMRP*]
        *kw*: :class:`dict`
            Keywords used as alternate definition of *a*
    :Outputs:
        *CLMX*: :class:`float` | :class:`np.ndarray`
            Pitching moment about arbitrary *xMRP*
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-20 ``@ddalle``: :class:`DataKit` version
    """
    # *xMRP* of original data
    xmrp = db.xMRP / db.Lref
    # Number of original arguments
    nf = len(db.eval_args["CLM"])
    # Get value for *xMRP*
    xMRP = db.get_arg_value(nf, "xMRP", *a, **kw)
    # Check for an *xhat*
    xhat = kw.get("xhat", xMRP/FM.Lref)
    # Evaluate main functions
    CLM = db("CLM", *a, **kw)
    CN  = db("CN",  *a, **kw)
    # Transfer
    return CLM + (xhat-xmrp)*CN


# Special evaluators: CLN vs x
def eval_CLNX(db, *a, **kw):
    r"""Evaluate *CLN* about arbitrary *x* moment reference point
    
    :Call:
        >>> CLNX = eval_CLNX(db, *a, **kw)
    :Inputs:
        *db*: :class:`DBFM`
            Force & moment data kit
        *a*: :class:`tuple`
            Arguments to call ``FM("CLM", *a)`` [plus *xMRP*]
        *kw*: :class:`dict`
            Keywords used as alternate definition of *a*
    :Outputs:
        *CLNX*: :class:`float` | :class:`np.ndarray`
            Pitching moment about arbitrary *xMRP*
    :Versions:
        * 2019-02-28 ``@ddalle``: First version
        * 2020-03-20 ``@ddalle``: :class:`DataKit` version
    """
    # *xMRP* of original data
    xmrp = db.xMRP / db.Lref
    # Number of original arguments
    nf = len(db.eval_args["CLN"])
    # Get value for *xMRP*
    xMRP = db.get_arg_value(nf, "xMRP", *a, **kw)
    # Check for an *xhat*
    xhat = kw.get("xhat", xMRP/FM.Lref)
    # Evaluate main functions
    CLN = db("CLN", *a, **kw)
    CY  = db("CY",  *a, **kw)
    # Transfer
    return CLN + (xhat-xmrp)*CY


# Evaluate *UCLM* about different x
def eval_UCLMX(db, *a, **kw):
    r"""Evaluate *UCLM* about arbitrary *x* moment reference point

    :Call:
        >>> UCLMX = eval_UCLMX(db, *a, **kw)
    :Inputs:
        *db*: :class:`DBFM`
            Force & moment data kit
        *a*: :class:`tuple`
            Arguments to call ``FM("CLM", *a)`` [plus *xMRP*]
        *kw*: :class:`dict`
            Keywords used as alternate definition of *a*
    :Outputs:
        *UCLMX*: :class:`float` | :class:`np.ndarray`
            Pitching moment uncertainty about arbitrary *xMRP*
    :Versions:
        * 2019-03-13 ``@ddalle``: First version
        * 2020-03-20 ``@ddalle``: :class:`DataKit` version
    """
    # *xMRP* of original data
    xmrp = db.xMRP / db.Lref
    # Number of original arguments
    nf = len(db.eval_args["CLM"])
    # Get value for *xMRP*
    xMRP = db.get_arg_value(nf, "xMRP", *a, **kw)
    # Check for an *xhat*
    xhat = kw.get("xhat", xMRP/FM.Lref)
    # Evaluate main functions
    UCLM = db("UCLM", *a, **kw)
    xCLM = db("xCLM", *a, **kw)
    UCN  = db("UCN",  *a, **kw)
    # Transfer
    UCLMX = np.sqrt(UCLM*UCLM + ((xCLM-xhat)*UCN)**2)
    # Output
    return UCLMX


# Evaluate *UCLN* about different x
def eval_UCLNX(db, *a, **kw):
    r"""Evaluate *UCLN* about arbitrary *x* moment reference point
    
    :Call:
        >>> UCLNX = eval_UCLNX(db, *a, **kw)
    :Inputs:
        *db*: :class:`DBFM`
            Force & moment data kit
        *a*: :class:`tuple`
            Arguments to call ``FM("CLM", *a)`` [plus *xMRP*]
        *kw*: :class:`dict`
            Keywords used as alternate definition of *a*
    :Outputs:
        *UCLNX*: :class:`float` | :class:`np.ndarray`
            Pitching moment uncertainty about arbitrary *xMRP*
    :Versions:
        * 2019-03-13 ``@ddalle``: First version
        * 2020-03-20 ``@ddalle``: :class:`DataKit` version
    """
    # *xMRP* of original data
    xmrp = db.xMRP / FM.Lref
    # Number of original arguments
    nf = len(db.eval_args["CLN"])
    # Get value for *xMRP*
    xMRP = db.get_arg_value(nf, "xMRP", *a, **kw)
    # Check for an *xhat*
    xhat = kw.get("xhat", xMRP/FM.Lref)
    # Evaluate main functions
    UCLN = db("UCLN", *a, **kw)
    xCLN = db("xCLN", *a, **kw)
    UCY  = db("UCY",  *a, **kw)
    # Transfer
    UCLNX = np.sqrt(UCLN*UCLN + ((xCLN-xhat)*UCY)**2)
    # Output
    return UCLNX


# DBFM options
class _DBFMOpts(rdb.DataKitOpts):
   # --- Global Options ---
    # List of options
    _optlist = {
        "RefLength",
        "RefArea",
        "xMRP",
        "yMRP",
        "zMRP",
    }

    # Alternate names
    _optmap = {
        "Aref": "RefArea",
        "Lref": "RefLength",
        "XMRP": "xMRP",
        "YMRP": "yMRP",
        "ZMRP": "zMRP",
    }


# DBFM definition
class _DBFMDefn(rdb.DataKitDefn):
    pass


# Combine options with parent class
_DBFMOpts.combine_optdefs()


# Create class
class DBFM(rdbaero.AeroDataKit):
    r"""Database class for launch vehicle force & moment

    :Call:
        >>> db = dbfm.DBFM(fname=None, **kw)
    :Inputs:
        *fname*: {``None``} | :class:`str`
            File name; extension is used to guess data format
        *csv*: {``None``} | :class:`str`
            Explicit file name for :class:`CSVFile` read
        *textdata*: {``None``} | :class:`str`
            Explicit file name for :class:`TextDataFile`
        *simplecsv*: {``None``} | :class:`str`
            Explicit file name for :class:`CSVSimple`
        *xls*: {``None``} | :class:`str`
            File name for :class:`XLSFile`
        *mat*: {``None``} | :class:`str`
            File name for :class:`MATFile`
    :Outputs:
        *db*: :class:`cape.attdb.dbfm.DBFM`
            LV force & moment database
    :Versions:
        * 2020-03-20 ``@ddalle``: First version
    """
  # ==================
  # Class Attributes
  # ==================
  # <
   # --- Options ---
    # Class for options
    _optscls = _DBFMOpts
    # Class for definitions
    _defncls = _DBFMDefn

   # --- Tags ---
    # Additional tags
    _tagmap = {
        "CA":   "CA",
        "CLL":  "CLL",
        "CLM":  "CLM",
        "CLN":  "CLN",
        "CN":   "CN",
        "CY":   "CY",
    }
  # >

  # ==================
  # Config
  # ==================
  # <
   # --- Init ---
    # Initialization method
    def __init__(self, fname=None, **kw):
        r"""Initialization method

        :Versions:
            * 2020-03-20 ``@ddalle``: First version
        """
        # Call parent's init method
        rdbaero.AeroDataKit.__init__(self, fname, **kw)
        # Set default arg converters
        self._make_arg_converters_aero()
        # Set UQ cols
        self._make_uq_cols_FM()
        self._make_uq_ecols_FM()
        self._make_uq_acols_FM()
        # Save reference properties
        self.Lref = self.opts.get_option("RefLength", 1.0)
        self.Aref = self.opts.get_option("RefArea", 0.25*np.pi)
        self.xMRP = self.opts.get_option("xMRP", 0.0)
        self.yMRP = self.opts.get_option("yMRP", 0.0)
        self.zMRP = self.opts.get_option("zMRP", 0.0)
        # Set default arguments
        self.set_arg_default("xMRP", self.xMRP)
        self.set_arg_default("yMRP", self.yMRP)
        self.set_arg_default("zMRP", self.zMRP)
        # 
        
  # >

  # ==================
  # Attributes
  # ==================
  # <
   # --- Arg Converters ---
    # Automate arg converters for preset tags
    def _make_arg_converters_aero(self):
        r"""Set default arg converters for cols with known tags

        :Call:
            >>> db._make_arg_converters_aero()
        :Inputs:
            *db*: :class:`cape.attdb.dbfm.DBFM`
                LV force & moment database
        :Versions:
            * 2020-03-19 ``@ddalle``: First version
        """
        # Loop through any keys with "alpha" tag
        for col in self.get_cols_by_tag("alpha"):
            # Set converter
            self.set_arg_converter(col, convert_alpha)
        # Loop through any keys with "beta" tag
        for col in self.get_cols_by_tag("beta"):
            # Set converter
            self.set_arg_converter(col, convert_beta)
        # Loop through any keys with "aoap" tag
        for col in self.get_cols_by_tag("aoap"):
            # Set converter
            self.set_arg_converter(col, convert_aoap)
        # Loop through any keys with "phip" tag
        for col in self.get_cols_by_tag("phip"):
            # Set converter
            self.set_arg_converter(col, convert_phip)

   # --- UQ Columns ---
    # Set UQ col for all FM cols
    def _make_uq_cols_FM(self):
        r"""Set default UQ col names for forces & moments

        :Call:
            >>> db._make_uq_cols_FM()
        :Inputs:
            *db*: :class:`cape.attdb.dbfm.DBFM`
                LV force & moment database
        :Versions:
            * 2020-03-20 ``@ddalle``: First version
        """
        # List FM tags
        tags = ["CA", "CY", "CN", "CLL", "CLM", "CLN"]
        # Loop through them
        for tag in tags:
            # Get cols with matching tag
            for col in self.get_cols_by_tag(tag):
                # Name of [default] UQ col
                ucol = "U" + col
                # Set it
                self.set_uq_col(col, ucol)

    # Set UQ extra cols for all FM cols
    def _make_uq_ecols_FM(self):
        r"""Set default UQ extra cols for reference UQ MRP

        :Call:
            >>> db._make_uq_ecols_FM()
        :Inputs:
            *db*: :class:`cape.attdb.dbfm.DBFM`
                LV force & moment database
        :Versions:
            * 2020-03-23 ``@ddalle``: First version
        """
        # List moment tags
        tags = ["CLM", "CLN"]
        # Loop through them
        for tag in tags:
            # Get cols with matching tag
            for col in self.get_cols_by_tag(tag):
                # Get actual UQ col
                ucol = self.get_uq_col(col)
                # Default UQ col if needed
                if ucol is None:
                    ucol = "U" + col
                # Form ecol name
                if ucol.startswith("U"):
                    # Strip "U" and prepend with "x"
                    ecol = "x" + ucol[1:]
                else:
                    # Just prepend *col* with "x"
                    ecol = "x" + col
                # Set it
                self.set_uq_ecol(ucol, ecol)

    # Set UQ aux cols for moment cols
    def _make_uq_acols_FM(self):
        r"""Set default UQ aux cols for reference UQ MRP

        :Call:
            >>> db._make_uq_acols_FM()
        :Inputs:
            *db*: :class:`cape.attdb.dbfm.DBFM`
                LV force & moment database
        :Versions:
            * 2020-03-23 ``@ddalle``: First version
        """
        # List moment tags
        tags = ["CLM", "CLN"]
        # Loop through them
        for tag in tags:
            # Get cols with matching tag
            for col in self.get_cols_by_tag(tag):
                # Check col names' ending
                if col.endswith("LM"):
                    # CLM -> CN
                    acol = col[:-2] + "N"
                elif col.endswith("LN"):
                    # CLN -> CY
                    acol = col[:-2] + "Y"
                elif col.endswith("m"):
                    # Cm -> CN
                    acol = col[:-1] + "N"
                elif col.endswith("n"):
                    # Cn -> CY
                    acol = col[:-1] + "Y"
                # Get actual UQ col
                ucol = self.get_uq_col(col)
                # Default UQ col if needed
                if ucol is None:
                    ucol = "U" + col
                # Set it
                self.set_uq_acol(ucol, acol)
   # >


# Combine options
kwutils._combine_val(DBFM._tagmap, rdbaero.AeroDataKit._tagmap)

# Invert the _tagmap
DBFM.create_tagcols()
