#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`cape.attdb.rdb`: Template ATTDB database
========================================================

This module provides the class :class:`DataKit` as a subclass of
:class:`dict` that contains methods common to each of the other database
classes.  The :class:`DataKit` class provides an interface to both store
the data and create and call "response surfaces" that define specific,
potentially complex interpolation methods to evaluate the data as a
function of several independent variables.

Finally, having this common template class provides a single point of
entry for testing if an object is based on a product of the
:mod:`cape.attdb.rdb` module.  The following Python sample tests if
any Python object *db* is an instance of any class from this data-file
collection.

    .. code-block:: python

        isinstance(db, cape.attdb.rdb.DataKit)

This class is the basic data container for ATTDB databases and has
interfaces to several different file types.

"""

# Standard library modules
import os
import copy

# Third-party modules
import numpy as np

# Semi-optional third-party modules
try:
    import scipy.interpolate.rbf as scirbf
except ImportError:
    scirbf = None

# CAPE modules
import cape.tnakit.kwutils as kwutils
import cape.tnakit.plot_mpl as pmpl
import cape.tnakit.statutils as statutils
import cape.tnakit.typeutils as typeutils

# Data Interfaces
import cape.attdb.ftypes as ftypes


# Accepted list for eval_method
RBF_METHODS = [
    "rbf",
    "rbf-map",
    "rbf-linear"
]
# RBF function types
RBF_FUNCS = [
    "multiquadric",
    "inverse_multiquadric",
    "gaussian",
    "linear",
    "cubic",
    "quintic",
    "thin_plate"
]


# Options for RDBNull
class DataKitOpts(ftypes.BaseDataOpts):
   # --- Global Options ---
    # List of options
    _optlist = {
        "csv",
        "mat",
        "simplecsv",
        "textdata",
        "xls"
    }

    # Alternate names
    _optmap = {
        "csvsimple": "simplecsv",
        "xlsx": "xlsx",
    }


# Definitions for RDBNull
class DataKitDefn(ftypes.BaseDataDefn):
    pass


# Combine options with parent class
DataKitOpts.combine_optdefs()


# Declare base class
class DataKit(ftypes.BaseData):
    r"""Basic database template without responses
    
    :Call:
        >>> db = DataKit(fname=None, **kw)
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
        *db*: :class:`cape.attdb.rdb.DataKit`
            Generic database
    :Versions:
        * 2019-12-04 ``@ddalle``: First version
        * 2020-02-19 ``@ddalle``: Rename from :class:`DBResponseNull`
    """
  # =====================
  # Class Attributes
  # =====================
  # <
   # --- Options ---
    # Class for options
    _optscls = DataKitOpts
    # Class for definitions
    _defncls = DataKitDefn

   # --- Method Names ---
    # Primary names
    _method_names = [
        "exact",
        "function",
        "multilinear",
        "multilinear-schedule",
        "nearest",
        "rbf",
        "rbf-linear",
        "rbf-map"
    ]

    # Alternates
    _method_map = {
        "fn": "function",
        "func": "function",
        "lin-rbf": "rbf-linear",
        "linear": "multilinear",
        "linear-rbf": "rbf-linear",
        "linear-schedule": "multilinear-schedule",
        "map-rbf": "rbf-map",
        "rbf-global": "rbf",
        "rbf-schedule": "rbf-map",
        "rbf0": "rbf",
        "rbf1": "rbf-map",
    }

    # Method functions
    _method_funcs = {
        0: {
            "exact": "eval_exact",
            "function": "eval_function",
            "multilinear": "eval_multilinear",
            "multilinear-schedule": "eval_multilinear_schedule",
            "nearest": "eval_nearest",
            "rbf": "eval_rbf",
            "rbf-linear": "eval_rbf_linear",
            "rbf-map": "eval_rbf_schedule",
        },
        1: {
            "exact": "eval_exact",
            "function": "eval_function",
            "multilinear": "eval_multilinear",
            "multilinear-schedule": "eval_multilinear_schedule",
            "nearest": "eval_nearest",
        },
    }

    # Method constructors
    _method_constructors = {
        "function": "_construct_function",
        "rbf": "_construct_rbf",
        "rbf-linear": "_construct_rbf_linear",
        "rbf-map": "_construct_rbf_map",
    }
  # >

  # =============
  # Config
  # =============
  # <
   # --- Primary Methods ---
    # Initialization method
    def __init__(self, fname=None, **kw):
        """Initialization method
        
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Required attributes
        self.cols = []
        self.n = 0
        self.defns = {}
        self.bkpts = {}
        self.sources = {}

        # Process keyword options
        self.opts = self.process_kw(_warnmode=0, **kw)
        # Create a mapped copy for below
        kw = kwutils.map_kw(self._optscls._optmap, **kw)

        # Check for null inputs
        if (fname is None) and (not kw):
            return

        # Get file name extension
        if typeutils.isstr(fname):
            # Get extension
            ext = fname.split(".")[-1]
        elif fname is not None:
            # Too confusing
            raise TypeError("Non-keyword input must be ``None`` or a string")
        else:
            # No file extension
            ext = None

        # Initialize file name handles for each type
        fcsv  = None
        fcsvs = None
        ftdat = None
        fxls  = None
        fmat  = None
        # Filter *ext*
        if ext == "csv":
            # Guess it's a mid-level CSV file
            fcsv = fname
        elif ext == "xls":
            # Guess it's a spreadsheet
            fxls = fname
        elif ext == "xlsx":
            # Guess it's a spreadsheet
            fxls = fname
        elif ext == "mat":
            # Guess it's a MATLAB file
            fmat = fname
        elif ext is not None:
            # Unable to guess
            raise ValueError(
                "Unable to guess file type of file name '%s'" % fname)

        # Last-check file names
        fcsv  = kw.pop("csv", fcsv)
        fxls  = kw.pop("xls", fxls)
        fmat  = kw.pop("mat", fmat)
        fcsvs = kw.pop("simplecsv", fcsvs)
        ftdat = kw.pop("textdata",  ftdat)

        # Read
        if fcsv is not None:
            # Read CSV file
            self.read_csv(fcsv, **kw)
        elif fxls is not None:
            # Read XLS file
            self.read_xls(fxls, **kw)
        elif fcsvs is not None:
            # Read simple CSV file
            self.read_csvsimple(fcsvs, **kw)
        elif ftdat is not None:
            # Read generic textual data file
            self.read_textdata(ftdat, **kw)
        elif fmat is not None:
            # Read MATLAB file
            self.read_mat(fmat, **kw)
        else:
            # If reaching this point, process values
            self.process_kw_values(self)

   # --- Copy ---
    # Copy
    def copy(self):
        r"""Make a copy of a database class
        
        Each database class may need its own version of this class
        
        :Call:
            >>> dbcopy = db.copy()
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
        :Outputs:
            *dbcopy*: :class:`cape.attdb.rdb.DataKit`
                Copy of generic database
        :Versions:
            * 2019-12-04 ``@ddalle``: First version
        """
        # Form a new database
        dbcopy = self.__class__()
        # Copy relevant parts
        self.copy_DataKit(dbcopy)
        # Output
        return dbcopy

    # Copy attributes and data known to DataKit class
    def copy_DataKit(self, dbcopy):
        r"""Copy attributes and data relevant to null-response DB
        
        :Call:
            >>> db.copy_DataKit(dbcopy)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *dbcopy*: :class:`cape.attdb.rdb.DataKit`
                Copy of generic database
        :Versions:
            * 2019-12-04 ``@ddalle``: First version
        """
        # Loop through columns
        for col in self.cols:
            dbcopy[col] = copy.copy(self[col])
        # Copy all attributes
        self.copy__dict__(dbcopy, skip=[])

    # Copy any remaining items
    def copy__dict__(self, dbtarg, skip=[]):
        r"""Copy all attributes except for specified list
        
        :Call:
            >>> db.copy__dict__(dbtarg, skip=[])
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *dbtarg*: :class:`cape.attdb.rdb.DataKit`
                Generic database; target copy
            *skip*: :class:`list`\ [:class:`str`]
                List of attributes not to copy
        :Effects:
            ``getattr(dbtarg, k)``: ``getattr(db, k, vdef)``
                Shallow copy of attribute from *DBc* or *vdef* if necessary
        :Versions:
            * 2019-12-04 ``@ddalle``: First version
        """
        
        # Check *skip*
        if not isinstance(skip, (list, tuple)):
            raise TypeError("Attributes to skip during copy must be list")
        # Loop through dict
        for k in self.__dict__:
            # Check if it should be skipped
            if k in skip:
                continue
            # Get copy, if possible
            try:
                # Create the copy
                vcopy = self.copyitem(self.__dict__[k])
                # Set it
                dbtarg.__dict__[k] = vcopy
            except Exception:
                # No copy
                continue

    # Copy an attribute if present
    def copyattr(self, dbtarg, k, vdef={}):
        r"""Make an appropriate copy of an attribute if present

        :Call:
            >>> db.copyattr(dbtarg, k, vdef={})
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *dbtarg*: :class:`cape.attdb.rdb.DataKit`
                Generic database; target copy
            *k*: :class:`str`
                Name of attribute to copy
            *vdef*: {``{}``} | :class:`any`
                Default value for output attribute if ``getattr(db,k)``
                does not exist
        :Effects:
            ``getattr(dbtarg, k)``: ``getattr(db, k, vdef)``
                Shallow copy of attribute from *DBc* or *vdef* if necessary
        :Versions:
            * 2018-06-08 ``@ddalle``: First version
            * 2019-12-04 ``@ddalle``: Copied from :class:`DBCoeff`
        """
        # Check for attribute
        if hasattr(self, k):
            # Get attribute
            v = getattr(self, k)
        else:
            # Use default
            v = vdef
        # Copy item
        vcopy = self.copyitem(v)
        # Save it
        setattr(dbtarg, k, vcopy)

    # Copy an item according to local rules
    def copyitem(self, v):
        r"""Return a copy of appropriate depth following class rules
        
        :Call:
            >>> vcopy = db.copyitem(v)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *v*: :class:`any`
                Variable to be copied
        :Outputs:
            *vcopy*: *v.__class__*
                Copy of *v* (shallow or deep)
        :Versions:
            * 2019-12-04 ``@ddalle``: First version
        """
        # Type
        t = v.__class__
        # Check the type in order to make a copy
        if v is None:
            # Not necessary to copy
            return
        elif t == dict:
            # Deep copy of dictionary
            try:
                return copy.deepcopy(v)
            except Exception:
                return dict(v)
        elif hasattr(v, "copy"):
            # Use class's already-build copy() method
            return v.copy()
        elif t == list:
            # Copy list
            return list(v)
        else:
            # Shallow copy
            return copy.copy(v)
  # >
        
  # ==================
  # Options
  # ==================
  # <
   # --- Column Definitions ---
    # Set a definition
    def set_defn(self, col, defn, _warnmode=0):
        r"""Set a column definition, with checks

        :Call:
            >>> db.set_defn(col, 
        """
        # Get dictionary of options
        defns = self.__dict__.setdefault("defns", {})
        # Create filtered definition
        defn_checked = self._defncls(_warnmode=_warnmode, **defn)
        # Set definition
        defns[col] = defn_checked

   # --- Copy/Link ---
    # Link options
    def copy_options(self, opts, prefix=""):
        r"""Copy a database's options

        :Call:
            >>> db.copy_options(opts, prefix="")
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *opts*: :class:`dict`
                Options dictionary
            *prefix*: {``""``} | :class:`str`
                Prefix to append to key names in *db.opts*
        :Effects:
            *db.opts*: :class:`dict`
                Options merged with or copied from *opts*
            *db.defns*: :class:`dict`
                Merged with ``opts["Definitions"]``
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: Added *db.defns* effect
            * 2020-02-10 ``@ddalle``: Removed *db.defns* effect
        """
        # Check input
        if not isinstance(opts, dict):
            raise TypeError("Options input must be dict-type")
        # Get options
        dbopts = self.__dict__.setdefault("opts", {})
        # Merge options
        for (k, v) in opts.items():
            # Apply prefix
            if prefix:
                # Add strings; no delimiter
                k1 = prefix + k
            else:
                # No prefix
                k1 = k
            # Check for "Definitions"; handled separately
            if k1 == "Definitions":
                continue
            # Get existing value
            v0 = dbopts.get(k1)
            # Check types
            if isinstance(v, dict) and isinstance(v0, dict):
                # Update dictionary
                v0.update(**v)
            else:
                # Overwrite or add
                dbopts[k] = v

    # Link definitions
    def copy_defns(self, defns, prefix="", _warnmode=0):
        r"""Copy a data store's column definitions

        :Call:
            >>> db.copy_defns(defns, prefix="")
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *defns*: :class:`dict`
                Dictionary of column definitions
            *prefix*: {``""``} | :class:`str`
                Prefix to append to key names in *db.opts*
        :Effects:
            *db.opts*: :class:`dict`
                Options merged with or copied from *opts*
            *db.defns*: :class:`dict`
                Merged with ``opts["Definitions"]``
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: Added *db.defns* effect
            * 2020-02-13 ``@ddalle``: Split from :func:`copy_options`
        """
        # Check input
        if not isinstance(defns, dict):
            raise TypeError(
                "'defns' input must be 'dict', got '%s'" % defns.__class__)
        # Loop through input definitions
        for (k, defn) in defns.items():
            # Check definition type
            if not isinstance(defn, dict):
                raise TypeError(
                    ("Definition for col '%s' " % k) +
                    ("must be 'dict', got '%s'" % defns.__class__))
            # Apply prefix
            if prefix:
                # Prepend column name
                col = prefix + k
            else:
                # Reuse column name
                col = k
            # Save the definition (in database format)
            self.set_defn(col, defn, _warnmode)

   # --- Definitions: Get ---
    # Get output dimension
    def get_output_ndim(self, col):
        r"""Get output dimension for column *col*

        :Call:
            >>> ndim = db.get_output_ndim(col)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseLinear`
                Database with multidimensional output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *ndim*: {``0``} | :class:`int`
                Dimension of *col* at a single condition
        :Versions:
            * 2019-12-27 ``@ddalle``: First version
        """
        # Get column definition
        defn = self.get_col_defn(col)
        # Get dimensionality
        ndim = defn.get("OutputDimension")
        # Check valid result
        if ndim is not None:
            return ndim
        # Get default parameter definition
        defn = self.defns.get("_", {})
        # Get dimensionality
        return defn.get("OutputDimension", 0)

   # --- Definitions: Set ---
    # Set dimensionality
    def set_output_ndim(self, col, ndim):
        r"""Set output dimension for column *col*

        :Call:
            >>> db.set_output_ndim(col, ndim)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseLinear`
                Database with multidimensional output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *ndim*: {``0``} | :class:`int`
                Dimension of *col* at a single condition
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get column definition
        defn = self.get_col_defn(col)
        # Check type
        if not isinstance(ndim, int):
            raise TypeError(
                "Output dimension for '%s' must be int (got %s)" %
                (col, type(ndim)))
        # Set it
        defn["OutputDimension"] = ndim
  # >

  # ================
  # Sources
  # ================
  # <
   # --- Get Source ---
    # Get a source by type and number
    def get_source(self, ext, n=None):
        r"""Get a source by category (and number), if possible

        :Call:
            >>> dbf = db.get_source(ext)
            >>> dbf = db.get_source(ext, n)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *ext*: :class:`str`
                Source type, by extension, to retrieve
            *n*: {``None``} | :class:`int` >= 0
                Source number
        :Outputs:
            *dbf*: :class:`cape.attdb.ftypes.basefile.BaseFile`
                Data file interface
        :Versions:
            * 2020-02-13 ``@ddalle``: First version
        """
        # Get sources
        srcs = self.__dict__.get("sources", {})
        # Check for *n*
        if n is None:
            # Loop through sources
            for name, dbf in srcs.items():
                # Check name
                if name.split("-") == ext:
                    # Output
                    return dbf
            else:
                # No match
                return
        else:
            # Get explicit name
            name = "%02i-%s" % (n, ext)
            # Check for source
            return srcs.get(name)

    # Get source, creating if necessary
    def get_dbf(self, ext, cls, n=None, cols=None):
        r"""Get or create a source by category (and number)

        :Call:
            >>> dbf = db.get_dbf(ext, cls)
            >>> dbf = db.get_dbf(ext, cls, n=None, cols=None)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *ext*: :class:`str`
                Source type, by extension, to retrieve
            *cls*: :class:`type`
                Subclass of :class:`BaseFile` to create (if needed)
            *n*: {``None``} | :class:`int` >= 0
                Source number to search for
            *cols*: {*db.cols*} | :class:`list`\ [:class:`str`]
                List of data columns to include in *dbf*
        :Outputs:
            *dbf*: :class:`cape.attdb.ftypes.basefile.BaseFile`
                Data file interface
        :Versions:
            * 2020-02-13 ``@ddalle``: First version
        """
        # Get the source
        dbf = self.get_source(ext, n=n)
        # Check if found
        if dbf is None:
            # Default columns
            if cols is None:
                # Use listed columns
                cols = self.cols
            # Get relevant options
            kw = {}
            # Set values
            kw["Values"] = {col: self[col] for col in cols}
            # Explicit column list
            kw["cols"] = cols
            # Copy definitions
            kw["Definitions"] = self.defns
            # Create from class
            dbf = cls(**kw)
        # Output
        return dbf
  # >

  # ==================
  # I/O
  # ==================
  # <
   # --- CSV ---
    # Read CSV file
    def read_csv(self, fname, **kw):
        r"""Read data from a CSV file
        
        :Call:
            >>> db.read_csv(fname, **kw)
            >>> db.read_csv(dbcsv, **kw)
            >>> db.read_csv(f, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *fname*: :class:`str`
                Name of CSV file to read
            *dbcsv*: :class:`cape.attdb.ftypes.csv.CSVFile`
                Existing CSV file
            *f*: :class:`file`
                Open CSV file interface
            *save*, *SaveCSV*: ``True`` | {``False``}
                Option to save the CSV interface to *db._csv*
        :See Also:
            * :class:`cape.attdb.ftypes.csv.CSVFile`
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Get option to save database
        save = kw.pop("save", kw.pop("SaveCSV", True))
        # Check input type
        if isinstance(fname, ftypes.CSVFile):
            # Already a CSV database
            dbf = fname
        else:
            # Create an instance
            dbf = ftypes.CSVFile(fname, **kw)
        # Link the data
        self.link_data(dbf)
        # Copy the options
        self.copy_defns(dbf.defns)
        # Save the file interface if needed
        if save:
            # Name for this source
            name = "%02i-csv" % len(self.sources)
            # Save it
            self.sources[name] = dbf

    # Write dense CSV file
    def write_csv_dense(self, fname, cols=None):
        r""""Write dense CSV file

        If *db._csv* exists, the database will be written from that
        interface.  Otherwise, :func:`get_CSVFile` will be called.

        :Call:
            >>> db.write_csv_dense(fname, cols=None)
            >>> db.write_csv_dense(f, cols=None)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *fname*: :class:`str`
                Name of file to write
            *f*: :class:`file`
                File open for writing
            *cols*: {*db.cols*} | :class:`list`\ [:class:`str`]
                List of columns to write
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
            * 2020-02-14 ``@ddalle``: Uniform "sources" interface
        """
        # Get CSV file interface
        dbcsv = self.get_dbf("csv", ftypes.CSVFile, cols=cols)
        # Write it
        dbcsv.write_csv_dense(fname, cols=cols)

   # --- Simple CSV ---
    # Read simple CSV file
    def read_csvsimple(self, fname, **kw):
        r"""Read data from a simple CSV file
        
        :Call:
            >>> db.read_csvsimple(fname, **kw)
            >>> db.read_csvsimple(dbcsv, **kw)
            >>> db.read_csvsimple(f, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *fname*: :class:`str`
                Name of CSV file to read
            *dbcsv*: :class:`cape.attdb.ftypes.csv.CSVSimple`
                Existing CSV file
            *f*: :class:`file`
                Open CSV file interface
            *save*, *SaveCSV*: ``True`` | {``False``}
                Option to save the CSV interface to *db._csv*
        :See Also:
            * :class:`cape.attdb.ftypes.csv.CSVFile`
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Get option to save database
        savecsv = kw.pop("save", kw.pop("SaveCSV", True))
        # Check input type
        if isinstance(fname, ftypes.CSVSimple):
            # Already a CSV database
            dbf = fname
        else:
            # Create an instance
            dbf = ftypes.CSVSimple(fname, **kw)
        # Link the data
        self.link_data(dbf)
        # Copy the definitions
        self.copy_defns(dbf.defns)
        # Save the file interface if needed
        if save:
            # Name for this source
            name = "%02i-csvsimple" % len(self.sources)
            # Save it
            self.sources[name] = dbf

   # --- Text Data ---
    # Read text data fiel
    def read_textdata(self, fname, **kw):
        r"""Read data from a simple CSV file
        
        :Call:
            >>> db.read_textdata(fname, **kw)
            >>> db.read_textdata(dbcsv, **kw)
            >>> db.read_textdata(f, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *fname*: :class:`str`
                Name of CSV file to read
            *dbcsv*: :class:`cape.attdb.ftypes.textdata.TextDataFile`
                Existing CSV file
            *f*: :class:`file`
                Open CSV file interface
            *save*: {``True``} | ``False``
                Option to save the CSV interface to *db._csv*
        :See Also:
            * :class:`cape.attdb.ftypes.csv.CSVFile`
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Get option to save database
        savedat = kw.pop("save", True)
        # Check input type
        if isinstance(fname, ftypes.TextDataFile):
            # Already a file itnerface
            dbf = fname
        else:
            # Create an insteance
            dbf = ftypes.TextDataFile(fname, **kw)
        # Linke the data
        self.link_data(dbf)
        # Copy the definitions
        self.copy_defns(dbf.defns)
        # Save the file interface if needed
        if save:
            # Name for this source
            name = "%02i-textdata" % len(self.sources)
            # Save it
            self.sources[name] = dbf

   # --- XLS ---
    # Read XLS file
    def read_xls(self, fname, **kw):
        r"""Read data from an ``.xls`` or ``.xlsx`` file
        
        :Call:
            >>> db.read_xls(fname, **kw)
            >>> db.read_xls(dbxls, **kw)
            >>> db.read_xls(wb, **kw)
            >>> db.read_xls(ws, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *dbxls*: :class:`cape.attdb.ftypes.xls.XLSFile`
                Existing XLS file interface
            *fname*: :class:`str`
                Name of ``.xls`` or ``.xlsx`` file to read
            *sheet*: {``0``} | :class:`int` | :class:`str`
                Worksheet name or number
            *wb*: :class:`xlrd.book.Book`
                Open workbook (spreadsheet file)
            *ws*: :class:`xlrd.sheet.Sheet`
                Direct access to a worksheet
            *skiprows*: {``None``} | :class:`int` >= 0
                Number of rows to skip before reading data
            *subrows*: {``0``} | :class:`int` > 0
                Number of rows below header row to skip
            *skipcols*: {``None``} | :class:`int` >= 0
                Number of columns to skip before first data column
            *maxrows*: {``None``} | :class:`int` > *skiprows*
                Maximum row number of data
            *maxcols*: {``None``} | :class:`int` > *skipcols*
                Maximum column number of data
            *save*, *SaveXLS*: ``True`` | {``False``}
                Option to save the XLS interface to *db._xls*
        :See Also:
            * :class:`cape.attdb.ftypes.xls.XLSFile`
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Get option to save database
        save = kw.pop("save", kw.pop("SaveXLS", True))
        # Check input type
        if isinstance(fname, ftypes.XLSFile):
            # Already a CSV database
            dbf = fname
        else:
            # Create an instance
            dbf = ftypes.XLSFile(fname, **kw)
        # Link the data
        self.link_data(dbf)
        # Copy the definitions
        self.copy_defns(dbf.defns)
        # Save the file interface if needed
        if save:
            # Name for this source
            name = "%02i-xls" % len(self.sources)
            # Save it
            self.sources[name] = dbf


   # --- MAT ---
    # Read MAT file
    def read_mat(self, fname, **kw):
        r"""Read data from a version 5 ``.mat`` file
        
        :Call:
            >>> db.read_mat(fname, **kw)
            >>> db.read_mat(dbmat, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Generic database
            *fname*: :class:`str`
                Name of ``.mat`` file to read
            *dbmat*: :class:`cape.attdb.ftypes.mat.MATFile`
                Existing MAT file interface
            *save*, *SaveMAT*: ``True`` | {``False``}
                Option to save the MAT interface to *db._mat*
        :See Also:
            * :class:`cape.attdb.ftypes.mat.MATFile`
        :Versions:
            * 2019-12-17 ``@ddalle``: First version
        """
        # Get option to save database
        save = kw.pop("save", kw.pop("SaveMAT", True))
        # Check input type
        if isinstance(fname, ftypes.MATFile):
            # Already a MAT database
            dbf = fname
        else:
            # Create an instance
            dbf = ftypes.MATFile(fname, **kw)
        # Columns to keep
        cols = []
        # Make replacements for column names
        for (j, col) in enumerate(dbf.cols):
            # Check name
            if col.startswith("DB."):
                # Strip prefix from name
                col1 = col[3:]
                # Replace key
                dbf[col1] = dbf.pop(col)
                # Save this column
                cols.append(col1)
            elif col.startswith("bkpts."):
                # Strip "bkpts" from name
                col1 = col[6:]
                # Create break points
                bkpts = self.__dict__.setdefault("bkpts", {})
                # Save them
                bkpts[col1] = dbf.pop(col)
            else:
                # No change; save this column
                cols.append(col)
        # Subset column list
        dbf.cols = cols
        # Link the data
        self.link_data(dbf)
        # Copy the definitions
        self.copy_defns(dbf.defns)
        # Link other attributes
        for (k, v) in dbf.__dict__.items():
            # Check if present and nonempty
            if self.__dict__.get(k):
                continue
            # Otherwise link
            self.__dict__[k] = v
        # Save the file interface if needed
        if save:
            # Name for this source
            name = "%02i-mat" % len(self.sources)
            # Save it
            self.sources[name] = dbf

    # Write MAT file
    def write_mat(self, fname, cols=None):
        r""""Write a MAT file

        If *db._mat* exists, the database will be written from that
        interface.  Otherwise, :func:`get_MATFile` will be called.

        :Call:
            >>> db.write_mat(fname, cols=None)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *fname*: :class:`str`
                Name of file to write
            *f*: :class:`file`
                File open for writing
            *cols*: {*db.cols*} | :class:`list`\ [:class:`str`]
                List of columns to write
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Get/create MAT file interface
        dbmat = self.get_dbf("mat", ftypes.MATFile, cols=cols)
        # Write it
        dbmat.write_mat(fname, cols=cols)
  # >

  # ===============
  # Eval/Call
  # ===============
  # <
   # --- Evaluation ---
    # Evaluate interpolation
    def __call__(self, *a, **kw):
        """Generic evaluation function

        :Call:
            >>> v = db(*a, **kw)
            >>> v = db(col, x0, x1, ...)
            >>> V = db(col, x0, X1, ...)
            >>> v = db(col, k0=x0, k1=x1, ...)
            >>> V = db(col, k0=x0, k1=X1, ...)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *x0*: :class:`float` | :class:`int`
                Numeric value for first argument to *coeff* evaluator
            *x1*: :class:`float` | :class:`int`
                Numeric value for second argument to *coeff* evaluator
            *X1*: :class:`np.ndarray` (:class:`float`)
                Array of *x1* values
            *k0*: :class:`str` | :class:`unicode`
                Name of first argument to *coeff* evaluator
            *k1*: :class:`str` | :class:`unicode`
                Name of second argument to *coeff* evaluator
        :Outputs:
            *v*: :class:`float` | :class:`int`
                Function output for scalar evaluation
            *V*: :class:`np.ndarray` (:class:`float`)
                Array of function outputs
        :Versions:
            * 2019-01-07 ``@ddalle``: Version 1.0
            * 2019-12-30 ``@ddalle``: Version 2.0: map of methods
        """
       # --- Get coefficient name ---
        # Process coefficient
        col, a, kw = self._prep_args_colname(*a, **kw)
       # --- Get method and other parameters ---
        # Specific method
        method_col = self.get_eval_method(col)
        # Specific lookup arguments (and copy it)
        args_col = self.get_eval_args(col)
        # Get extra args passed along to evaluator
        kw_fn = self.get_eval_kwargs(col)
        # Attempt to get default aliases
        arg_aliases = self.get_eval_arg_aliases(col)
       # --- Aliases ---
        # Process aliases in *kw*
        for k in dict(kw):
            # Check if there's an alias for *k*
            if k not in arg_aliases:
                continue
            # Get alias for keyword *k*
            alias_k = arg_aliases[k]
            # Save the value under the alias as well
            kw[alias_k] = kw.pop(k)
       # --- Argument values ---
        # Initialize lookup point
        x = []
        # Loop through arguments
        for i, k in enumerate(args_col):
            # Get value
            xi = self.get_arg_value(i, k, *a, **kw)
            # Save it
            x.append(np.asarray(xi))
        # Normalize arguments
        X, dims = self.normalize_args(x)
        # Maximum dimension
        nd = len(dims)
        # Data size
        nx = np.prod(dims)
       # --- Evaluation ---
        # Get class handle
        cls = self.__class__
        # Use lower case with hyphens instead of underscores
        method_col = method_col.lower().replace("_", "-")
        # Get proper method name (default to same)
        method_col = cls._method_map.get(method_col, method_col)
        # Output dimensionality
        ndim_col = self.get_output_ndim(col)
        # Get maps from function name to function callable
        method_funcs = cls._method_funcs[ndim_col]
        # Check if present
        if method_col not in method_funcs:
            # Get close matches
            mtchs = difflib.get_close_matches(
                method_col, list(method_funcs.keys()))
            # Error message
            raise ValueError(
                ("No %i-D eval method '%s'; " % (ndim_col, method_col)) +
                ("closest matches: %s" % mtches))
        # Get the function handle
        f = getattr(self, method_funcs.get(method_col))
        # Combine args (should there be an attribute for this?)
        kw_fn = dict(kw_fn, **kw)
        # Calls
        if nd == 0:
            # Scalar call
            v = f(col, args_col, x, **kw_fn)
            # Output
            return v
        else:
            # Initialize output
            V = np.zeros(nx)
            # Loop through points
            for j in range(nx):
                # Construct inputs
                xj = [Xi[j] for Xi in X]
                # Call scalar function
                V[j] = f(col, args_col, xj, **kw_fn)
            # Reshape
            V = V.reshape(dims)
            # Output
            return V

   # --- Alternative Evaluation ---
    # Evaluate only exact matches
    def eval_exact(self, *a, **kw):
        r"""Evaluate a column but only at points with exact matches

        :Call:
            >>> V, I, J, X = db.eval_exact(*a, **kw)
            >>> V, I, J, X = db.eval_exact(col, x0, X1, ...)
            >>> V, I, J, X = db.eval_exact(col, k0=x0, k1=X1, ...)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *x0*: :class:`float` | :class:`int`
                Value[s] for first argument to *col* evaluator
            *x1*: :class:`float` | :class:`int`
                Value[s] for second argument to *col* evaluator
            *X1*: :class:`np.ndarray`\ [:class:`float`]
                Array of *x1* values
            *k0*: :class:`str`
                Name of first argument to *col* evaluator
            *k1*: :class:`str`
                Name of second argument to *col* evaluator
        :Outputs:
            *V*: :class:`np.ndarray`\ [:class:`float`]
                Array of function outputs
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of cases matching inputs (see :func:`find`)
            *J*: :class:`np.ndarray`\ [:class:`int`]
                Indices of matches within input arrays
            *X*: :class:`tuple`\ [:class:`np.ndarray`]
                Values of arguments at exact matches
        :Versions:
            * 2019-03-11 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
       # --- Get coefficient name ---
        # Process coefficient name and remaining coeffs
        col, a, kw = self._prep_args_colname(*a, **kw)
       # --- Matching values
        # Get list of arguments for this coefficient
        args = self.get_eval_args(coeff)
        # Possibility of fallback values
        arg_defaults = getattr(self, "eval_arg_defaults", {})
        # Find exact matches
        I, J = self.find(args, *a, **kw)
        # Initialize values
        x = []
        # Loop through coefficients
        for (i, k) in enumerate(args):
            # Get values
            V = self.get_all_values(k)
            # Check for mismatch
            if V is None:
                # Attempt to get value from inputs
                xi = self.get_arg_value(i, k, *a, **kw)
                # Check for scalar
                if xi is None:
                    raise ValueError(
                        ("Could not generate array of possible values ") +
                        ("for argument '%s'" % k))
                elif typeutils.isarray(xi):
                    raise ValueError(
                        ("Could not generate fixed scalar for test values ") +
                        ("of argument '%s'" % k))
                # Save the scalar value
                x.append(xi)
            else:
                # Save array of varying test values
                x.append(V[I])
        # Normalize
        X, dims = self.normalize_args(x)
       # --- Evaluation ---
        # Evaluate coefficient at matching points
        if col in self:
            # Use direct indexing
            V = self[col][I]
        else:
            # Use evaluator (necessary for coeffs like *CLMX*)
            V = self.__call__(col, *X, **kw)
        # Output
        return V, I, J, X

    # Evaluate UQ from coefficient
    def eval_uq(self, *a, **kw):
        r"""Evaluate specified UQ cols for a specified col

        This function will evaluate the UQ cols specified for a given
        nominal column by referencing the appropriate subset of
        *db.eval_args* for any UQ cols.  It evaluates the UQ col named
        in *db.uq_cols*.  For example if *CN* is a function of
        ``"mach"``, ``"alpha"``, and ``"beta"``; ``db.uq_cols["CN"]``
        is *UCN*; and *UCN* is a function of ``"mach"`` only, this
        function passes only the Mach numbers to *UCN* for evaluation.

        :Call:
            >>> U = db.eval_uq(*a, **kw)
            >>> U = db.eval_uq(col, x0, X1, ...)
            >>> U = db.eval_uq(col, k0=x0, k1=x1, ...)
            >>> U = db.eval_uq(col, k0=x0, k1=X1, ...)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of **nominal** column to evaluate
            *db.uq_cols*: :class:`dict`\ [:class:`str`]
                Dictionary of UQ col names for each col
            *x0*: :class:`float` | :class:`int`
                Numeric value for first argument to *col* evaluator
            *x1*: :class:`float` | :class:`int`
                Numeric value for second argument to *col* evaluator
            *X1*: :class:`np.ndarray`\ [:class:`float`]
                Array of *x1* values
            *k0*: :class:`str`
                Name of first argument to *col* evaluator
            *k1*: :class:`str`
                Name of second argument to *col* evaluator
        :Outputs:
            *U*: :class:`dict`\ [:class:`float` | :class:`np.ndarray`]
                Values of relevant UQ col(s) by name
        :Versions:
            * 2019-03-07 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
       # --- Get coefficient name ---
        # Process coefficient name and remaining coeffs
        col, a, kw = self._prep_args_colname(*a, **kw)
       # --- Argument processing ---
        # Specific lookup arguments
        args_col = self.get_eval_args(col)
        # Initialize lookup point
        x = []
        # Loop through arguments
        for i, k in enumerate(args_col):
            # Get value
            xi = self.get_arg_value(i, k, *a, **kw)
            # Save it
            x.append(np.asarray(xi))
        # Normalize arguments
        X, dims = self.normalize_args(x)
        # Maximum dimension
        nd = len(dims)
       # --- UQ coeff ---
        # Dictionary of UQ coefficients
        uq_cols = getattr(self, "uq_cols", {})
        # Coefficients for this coefficient
        uq_col = uq_cols.get(col, [])
        # Check for list
        if isinstance(uq_col, (tuple, list)):
            # Save a flag for list of coeffs
            qscalar = False
            # Pass coefficient to list (copy it)
            uq_col_list = list(uq_col)
        else:
            # Save a flag for scalar output
            qscalar = True
            # Make a list
            uq_col_list = [uq_col]
       # --- Evaluation ---
        # Initialize output
        U = {}
        # Loop through UQ coeffs
        for uk in uq_col_list:
            # Get evaluation args
            args_k = self.get_eval_args(uk)
            # Initialize inputs to *uk*
            UX = []
            # Loop through eval args
            for ai in args_k:
                # Check for membership
                if ai not in args_col:
                    raise ValueError(
                        ("UQ col '%s' is a function of " % uk) +
                        ("'%s', but parent col '%s' is not" % (ai, col)))
                # Append value
                UX.append(X[args_col.index(ai)])
            # Evaluate
            U[uk] = self.__call__(uk, *UX, **kw)

       # --- Output ---
        # Check for scalar output
        if qscalar:
            # Return first value
            return U[uk]
        else:
            # Return list
            return U

    # Evaluate coefficient from arbitrary list of arguments
    def eval_from_arglist(self, col, args, *a, **kw):
        r"""Evaluate column from arbitrary argument list

        This function is used to evaluate a col when given the
        arguments to some other column.

        :Call:
            >>> V = db.eval_from_arglist(col, args, *a, **kw)
            >>> V = db.eval_from_arglist(col, args, x0, X1, ...)
            >>> V = db.eval_from_arglist(col, args, k0=x0, k1=x1, ...)
            >>> V = db.eval_from_arglist(col, args, k0=x0, k1=X1, ...)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list`\ [:class:`str`]
                List of arguments provided
            *x0*: :class:`float` | :class:`int`
                Numeric value for first argument to *col* evaluator
            *x1*: :class:`float` | :class:`int`
                Numeric value for second argument to *col* evaluator
            *X1*: :class:`np.ndarray`\ [:class:`float`]
                Array of *x1* values
            *k0*: :class:`str`
                Name of first argument to *col* evaluator
            *k1*: :class:`str`
                Name of second argument to *col* evaluator
        :Outputs:
            *V*: :class:`float` | :class:`np.ndarray`
                Values of *col* as appropriate
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
       # --- Argument processing ---
        # Specific lookup arguments for *coeff*
        args_col = self.get_eval_args(col)
        # Initialize lookup point
        x = []
        # Loop through arguments asgiven
        for i, k in enumerate(args):
            # Get value
            xi = self.get_arg_value(i, k, *a, **kw)
            # Save it
            x.append(np.asarray(xi))
        # Normalize arguments
        X, dims = self.normalize_args(x)
        # Maximum dimension
        nd = len(dims)
       # --- Evaluation ---
        # Initialize inputs to *coeff*
        A = []
        # Get aliases for this coeffiient
        aliases = getattr(self, "eval_arg_aliases", {})
        aliases = aliases.get(col, {})
        # Loop through eval args
        for ai in args_col:
            # Check for membership
            if ai in args:
                # Append value
                A.append(X[args.index(ai)])
                continue
            # Check aliases
            for k, v in aliases.items():
                # Check if we found the argument sought for
                if v != ai:
                    continue
                # Check if this alias is in the provided list
                if k in args:
                    # Replacement argument name
                    ai = k
            # Check for membership (second try)
            if ai in args:
                # Append value
                A.append(X[args.index(ai)])
                continue
            raise ValueError(
                ("Col '%s' is a function of " % col) +
                ("'%s', not provided in argument list" % ai))
        # Evaluate
        return self.__call__(col, *A, **kw)

    # Evaluate coefficient from arbitrary list of arguments
    def eval_from_index(self, col, I, **kw):
        r"""Evaluate data column from indices

        This function has the same output as accessing ``db[col][I]`` if
        *col* is directly present in the database.  However, it's
        possible that *col* can be evaluated by some other technique, in
        which case direct access would fail but this function may still
        succeed.

        This function looks up the appropriate input variables and uses
        them to generate inputs to the database evaluation method.

        :Call:
            >>> V = db.eval_from_index(col, I, **kw)
            >>> v = db.eval_from_index(col, i, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices at which to evaluate function
            *i*: :class:`int`
                Single index at which to evaluate
        :Outputs:
            *V*: :class:`np.ndarray`
                Values of *col* as appropriate
            *v*: :class:`float`
                Scalar evaluation of *col*
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
       # --- Argument processing ---
        # Specific lookup arguments for *col*
        args_col = self.get_eval_args(col)
       # --- Evaluation ---
        # Initialize inputs to *coeff*
        A = []
        # Loop through eval args
        for ai in args_col:
            # Append value
            A.append(self.get_xvals(ai, I, **kw))
        # Evaluate
        return self.__call__(col, *A, **kw)

   # --- Declaration ---
    # Set evaluation methods
    def set_responses(self, cols, method, args, *a, **kw):
        r"""Set evaluation method for a list of columns

        :Call:
            >>> db.set_responses(cols, method, args, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *cols*: :class:`list`\ [:class:`str`]
                List of columns for which to declare evaluation rules
            *method*: ``"nearest"`` | ``"linear"`` | :class:`str`
                Response (lookup/interpolation/evaluation) method name 
            *args*: :class:`list`\ [:class:`str`]
                List of input arguments
            *a*: :class:`tuple`
                Args passed to constructor, if used
            *aliases*: {``{}``} | :class:`dict`\ [:class:`str`]
                Dictionary of alternate variable names during
                evaluation; if *aliases[k1]* is *k2*, that means *k1*
                is an alternate name for *k2*, and *k2* is in *args*
            *eval_kwargs*: {``{}``} | :class:`dict`
                Keyword arguments passed to functions
            *I*: {``None``} | :class:`np.ndarray`
                Indices of cases to include in response {all}
            *function*: {``"cubic"``} | :class:`str`
                Radial basis function type
            *smooth*: {``0.0``} | :class:`float` >= 0
                Smoothing factor for methods that allow inexact
                interpolation, ``0.0`` for exact interpolation
        :Versions:
            * 2019-01-07 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2020-02-18 ``@ddalle``: Name from :func:`SetEvalMethod`
        """
        # Check for list
        if not isinstance(cols, (list, tuple, set)):
            # Not a list
            raise TypeError(
                "Response col list must be list, " +
                ("got '%s'" % type(cols)))
        # Loop through coefficients
        for col in cols:
            # Check type
            if not isinstance(col, typeutils.strlike):
                # Not a string
                raise TypeError("Response col must be a string")
            # Specify individual col
            self.set_response(col, method, args, *a, **kw)

    # Save a method for one coefficient
    def set_response(self, col, method, args, *a, **kw):
        r"""Set evaluation method for a single column

        :Call:
            >>> db.set_response(col, method, args, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column for which to declare evaluation rules
            *method*: ``"nearest"`` | ``"linear"`` | :class:`str`
                Response (lookup/interpolation/evaluation) method name 
            *args*: :class:`list`\ [:class:`str`]
                List of input arguments
            *a*: :class:`tuple`
                Args passed to constructor, if used
            *ndim*: {``0``} | :class:`int` >= 0
                Output dimensionality
            *aliases*: {``{}``} | :class:`dict`\ [:class:`str`]
                Dictionary of alternate variable names during
                evaluation; if *aliases[k1]* is *k2*, that means *k1*
                is an alternate name for *k2*, and *k2* is in *args*
            *eval_kwargs*: {``{}``} | :class:`dict`
                Keyword arguments passed to functions
            *I*: {``None``} | :class:`np.ndarray`
                Indices of cases to include in response surface {all}
            *function*: {``"cubic"``} | :class:`str`
                Radial basis function type
            *smooth*: {``0.0``} | :class:`float` >= 0
                Smoothing factor for methods that allow inexact
                interpolation, ``0.0`` for exact interpolation
        :Versions:
            * 2019-01-07 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2019-12-30 ``@ddalle``: Version 2.0; map of methods
            * 2020-02-18 ``@ddalle``: Name from :func:`_set_method1`
        """
       # --- Input checks ---
        # Check inputs
        if col is None:
            # Set the default
            col = "_"
        # Check for valid argument list
        if args is None:
            raise ValueError("Argument list (keyword 'args') is required")
        # Check for method
        if method is None:
            raise ValueError("Eval method (keyword 'method') is required")
        # Get alias option
        arg_aliases = kw.get("aliases", {})
        # Get alias option
        eval_kwargs = kw.get("eval_kwargs", {})
        # Save aliases
        self.set_eval_arg_aliases(col, arg_aliases)
        self.set_eval_kwargs(col, eval_kwargs)
       # --- Method switch ---
        # Get class
        cls = self.__class__
        # Get dimension
        ndim = kw.get("ndim", self.get_output_ndim(col))
        # Set dimensionality (handles checks first)
        self.set_output_ndim(col, ndim)
        # Use lower case with hyphens instead of underscores
        method = method.lower().replace("_", "-")
        # Get proper method name (default to same)
        method = cls._method_map.get(method, method)
        # Check if present
        if method not in cls._method_names:
             # Get close matches
            mtchs = difflib.get_close_matches(method_col, cls._method_names)
            # Error message
            raise ValueError(
                ("No %i-D eval method '%s'; " % (ndim, method)) +
                ("closest matches: %s" % mtches))
        # Check for required constructor method
        constructor_col = cls._method_constructors.get(method)
        # Apply it if appropriate
        if constructor_col is None:
            # Do nothing
            pass
        elif not callable(constructor_col):
            raise TypeError(
                "Constructor for method '%s' is not callable" % method)
        else:
            # Call the constructor
            constructor_col(*a, args=args, **kw)
        # Save method name
        self.set_eval_method(col, method)
        # Argument list is the same for all methods
        self.set_eval_args(col, args)

   # --- Constructors ---
    # Explicit function
    def _construct_function(self, col, *a, **kw):
        r"""Constructor for ``"function"`` methods

        :Call:
            >>> db._construct_function(col, *a, **kw)
            >>> db._construct_function(col, fn, *a[1:], **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *fn*, *a[0]*: *callable*
                Function to save
            *a*: :class:`tuple`
                Extra positional arguments ignored
        :Keywords:
            *function*, *func*: *callable*
                Callable function to save, overrides *a[0]*
            *self*: {``True``} | ``False``
                Flag to include database in callback
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Create eval_func dictionary
        eval_func = self.__dict__.setdefault("eval_func", {})
        # Create eval_func dictionary
        eval_func_self = self.__dict__.setdefault("eval_func_self", {})
        # Get the function
        if len(a) > 0:
            # Function given as arg
            fn = a[0]
        else:
            # Function better be a keyword because there are no args
            fn = None
        # Save the function
        eval_func[col] = kw.get("function", kw.get("func", fn))
        eval_func_self[col] = kw.get("self", True)

    # Global RBFs
    def _construct_rbf(self, col, *a, **kw):
        r"""Constructor for ``"rbf"`` methods

        :Call:
            >>> db._construct_rbf(col, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *a*: :class:`tuple`
                Extra positional arguments ignored
        :Keywords:
            *args*: :class:`list`\ [:class:`str`]
                List of evaluation arguments
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get arguments arg
        args = kw.pop("args", None)
        # Check types
        if args is None:
            raise ValueError("'args' keyword argument is required")
        elif not isinstance(args, list):
            raise TypeError("'args' list must be list (got %s)" % type(args))
        # Call function
        self.create_global_rbfs([col], args, **kw)

    # Linear-RBFs
    def _construct_rbf_linear(self, col, *a, **kw):
        r"""Constructor for ``"rbf-linear"`` methods

        :Call:
            >>> db._construct_rbf_linear(col, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *a*: :class:`tuple`
                Extra positional arguments ignored
        :Keywords:
            *args*: :class:`list`\ [:class:`str`]
                List of evaluation arguments
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get arguments arg
        args = kw.pop("args", None)
        # Check types
        if args is None:
            raise ValueError("'args' keyword argument is required")
        elif not isinstance(args, list):
            raise TypeError("'args' list must be list (got %s)" % type(args))
        # Call function
        self.create_slice_rbfs([col], args, **kw)

    # Schedule-RBFs
    def _construct_rbf_map(self, col, *a, **kw):
        r"""Constructor for ``"rbf-map"`` methods

        :Call:
            >>> db._construct_rbf_map(col, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *a*: :class:`tuple`
                Extra positional arguments ignored
        :Keywords:
            *args*: :class:`list`\ [:class:`str`]
                List of evaluation arguments
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get arguments arg
        args = kw.pop("args", None)
        # Check types
        if args is None:
            raise ValueError("'args' keyword argument is required")
        elif not isinstance(args, list):
            raise TypeError("'args' list must be list (got %s)" % type(args))
        # Call function
        self.create_slice_rbfs([col], args, **kw)

   # --- Options: Get ---
    # Get argument list
    def get_eval_args(self, col):
        r"""Get list of evaluation arguments

        :Call:
            >>> args = db.get_eval_args(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *args*: :class:`list`\ [:class:`str`]
                List of parameters used to evaluate *col*
        :Versions:
            * 2019-03-11 ``@ddalle``: Forked from :func:`__call__`
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get overall handle
        eval_args = self.__dict__.get("eval_args", {})
        # Get option
        args_col = eval_args.get(col)
        # Check for default
        if args_col is None:
            # Attempt to get a default
            args_col = eval_args.get("_")
        # Create a copy if a list
        if args_col is None:
            # Don't have to copy ``None``
            return args_col
        elif isinstance(args_col, list):
            # Create a copy to prevent muting the definitions
            return list(args_col)
        else:
            # What?
            raise TypeError(
                "eval_args for '%s' must be list (got %s)"
                % (col, type(args_col)))

    # Get evaluation method
    def get_eval_method(self, col):
        r"""Get evaluation method (if any) for a column

        :Call:
            >>> method = db.get_eval_method(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *method*: ``None`` | :class:`str`
                Name of evaluation method for *col* or ``"_"``
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2019-12-30 ``@ddalle``: Added default
        """
        # Get attribute
        eval_methods = self.__dict__.setdefault("eval_method", {})
        # Get method
        method = eval_methods.get(col)
        # Check for ``None``
        if method is None:
            # Get default
            method = eval_methods.get("_")
        # Output
        return method

    # Get evaluation argument converter
    def get_eval_arg_converter(self, k):
        r"""Get evaluation argument converter

        :Call:
            >>> f = db.get_eval_arg_converter(k)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *k*: :class:`str` | :class:`unicode`
                Name of argument
        :Outputs:
            *f*: ``None`` | callable
                Callable converter
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get converter dictionary
        converters = self.__dict__.setdefault("eval_arg_covnerters", {})
        # Get converter
        f = converters.get(k)
        # Output if None
        if f is None:
            return f
        # Check class
        if not callable(f):
            raise TypeError("Converter for '%s' is not callable" % k)
        # Output
        return f

    # Get UQ coefficient
    def get_uq_col(self, col):
        r"""Get name of UQ coefficient(s) for *coeff*

        :Call:
            >>> ucol = db.get_uq_col(col)
            >>> ucols = db.get_uq_col(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
        :Outputs:
            *ucol*: ``None`` | :class:`str`
                Name of UQ columns for *col*
            *ucols*: :class:`list`\ [:class:`str`]
                List of UQ columns for *col*
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2019-12-26 ``@ddalle``: Renamed from :func:`get_uq_coeff`
        """
        # Get dictionary of UQ coeffs
        uq_cols = self.__dict__.setdefault("uq_cols", {})
        # Get entry for this coefficient
        return uq_cols.get(col)

    # Get user-set callable function
    def get_eval_func(self, col):
        r"""Get callable function predefined for a column

        :Call:
            >>> fn = db.get_eval_func(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
        :Outputs:
            *fn*: ``None`` | *callable*
                Specified function for *col*
        :Versions:
            * 2019-12-28 ``@ddalle``: First version
        """
        # Get dictionary
        eval_func = self.__dict__.get("eval_func", {})
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be string (got %s)" % type(col))
        elif not isinstance(eval_func, dict):
            raise TypeError("eval_func attribute is not a dict")
        # Get entry
        fn = eval_func.get(col)
        # If none, acceptable
        if fn is None:
            return
        # Check type if nonempty
        if not callable(fn):
            raise TypeError("eval_func for col '%s' is not callable" % col)
        # Output
        return fn

    # Get aliases for evaluation args
    def get_eval_arg_aliases(self, col):
        r"""Get alias names for evaluation args for a data column

        :Call:
            >>> aliases = db.get_eval_arg_aliases(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
        :Outputs:
            *aliases*: {``{}``} | :class:`dict`
                Alternate names for args while evaluationg *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get attribute
        arg_aliases = self.__dict__.get("eval_arg_aliases", {})
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be string (got %s)" % type(col))
        elif not isinstance(arg_aliases, dict):
            raise TypeError("eval_arg_aliases attribute is not a dict")
        # Get entry
        aliases = arg_aliases.get(col)
        # Check for empty response
        if aliases is None:
            # Use defaults
            aliases = arg_aliases.get("_", {})
        # Check types
        if not isinstance(aliases, dict):
            raise TypeError(
                "Aliases for col '%s' must be dict (got %s)" %
                (col, type(aliases)))
        # (Not checking key-value types)
        # Output
        return aliases

    # Get eval arg keywords
    def get_eval_kwargs(self, col):
        r"""Get any keyword arguments passed to *col* evaluator

        :Call:
            >>> kwargs = db.get_eval_kwargs(col)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
        :Outputs:
            *kwargs*: {``{}``} | :class:`dict`
                Keyword arguments to add while evaluating *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get attribute
        eval_kwargs = self.__dict__.get("eval_eval_kwargs", {})
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be string (got %s)" % type(col))
        elif not isinstance(eval_kwargs, dict):
            raise TypeError("eval_kwargs attribute is not a dict")
        # Get entry
        kwargs = eval_kwargs.get(col)
        # Check for empty response
        if kwargs is None:
            # Use defaults
            kwargs = eval_kwargs.get("_", {})
        # Check types
        if not isinstance(kwargs, dict):
            raise TypeError(
                "eval_kwargs for col '%s' must be dict (got %s)" %
                (col, type(kwargs)))
        # Output
        return kwargs

    # Get xvars for output
    def get_output_xvars(self, col):
        r"""Get list of args to output for column *col*

        :Call:
            >>> xargs = db.get_output_xvars(col)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseLinear`
                Database with multidimensional output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *xargs*: {``[]``} | :class:`list`\ [:class:`str`]
                List of input args to one condition of *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get column definition
        defn = self.get_defn(col)
        # Get dimensionality
        xargs = defn.get("OutputXVars")
        # De-None
        if xargs is None:
            xargs = []
        # Check type
        if not isinstance(xargs, list):
            raise TypeError(
                "OutputXVars for col '%s' must be list (got %s)"
                % (col, type(xargs)))
        # Output (copy)
        return list(xargs)

   # --- Options: Set ---
    # Set evaluation args
    def set_eval_args(self, col, args):
        r"""Set list of evaluation arguments for a column

        :Call:
            >>> db.set_eval_args(col, args)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column
            *args*: :class:`list`\ [:class:`str`]
                List of arguments for evaluating *col*
        :Effects:
            *db.eval_args*: :class:`dict`
                Entry for *col* set to copy of *args* w/ type checks
        :Versions:
            * 2019-12-28 ``@ddalle``: First version
        """
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be str (got %s)" % type(col))
        if not isinstance(args, list):
            raise TypeError(
                "eval_args for '%s' must be list (got %s)"
                % (col, type(args)))
        # Check args
        for (j, k) in enumerate(args):
            if not typeutils.isstr(k):
                raise TypeError(
                    "Arg %i for col '%s' is not a string" % (j, col))
        # Get handle to attribute
        eval_args = self.__dict__.setdefault("eval_args", {})
        # Check type
        if not isinstance(eval_args, dict):
            raise TypeError("eval_args attribute is not a dict")
        # Set parameter (to a copy)
        eval_args[col] = list(args)

    # Set evaluation method
    def set_eval_method(self, col, method):
        r"""Set name (only) of evaluation method

        :Call:
            >>> db.set_eval_method(col, method)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column
            *method*: :class:`str`
                Name of evaluation method (only checked for type)
        :Effects:
            *db.eval_meth*: :class:`dict`
                Entry for *col* set to *method*
        :Versions:
            * 2019-12-28 ``@ddalle``: First version
        """
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be str (got %s)" % type(col))
        if not typeutils.isstr(method):
            raise TypeError(
                "eval_method for '%s' must be list (got %s)"
                % (col, type(method)))
        # Get handle to attribute
        eval_method = self.__dict__.setdefault("eval_method", {})
        # Check type
        if not isinstance(eval_method, dict):
            raise TypeError("eval_method attribute is not a dict")
        # Set parameter (to a copy)
        eval_method[col] = method

    # Set evaluation function
    def set_eval_func(self, col, fn):
        r"""Set specific callable for a column

        :Call:
            >>> db.set_eval_func(col, fn)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column
            *fn*: *callable* | ``None``
                Function or other callable entity
        :Effects:
            *db.eval_meth*: :class:`dict`
                Entry for *col* set to *method*
        :Versions:
            * 2019-12-28 ``@ddalle``: First version
        """
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be str (got %s)" % type(col))
        if (fn is not None) and not callable(fn):
            raise TypeError(
                "eval_func for '%s' must be callable" % col)
        # Get handle to attribute
        eval_func = self.__dict__.setdefault("eval_func", {})
        # Check type
        if not isinstance(eval_func, dict):
            raise TypeError("eval_func attribute is not a dict")
        # Set parameter
        if fn is None:
            # Remove it
            eval_func.pop(col, None)
        else:
            # Set it
            eval_func[col] = fn
            
    # Set a default value for an argument
    def set_arg_default(self, k, v):
        r"""Set a default value for an evaluation argument

        :Call:
            >>> db.set_arg_default(k, v)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *k*: :class:`str`
                Name of evaluation argument
            *v*: :class:`float`
                Default value of the argument to set
        :Versions:
            * 2019-02-28 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get dictionary
        arg_defaults = self.__dict__.setdefault("eval_arg_defaults", {})
        # Save key/value
        arg_defaults[k] = v

    # Set a conversion function for input variables
    def set_arg_converter(self, k, fn):
        r"""Set a function to evaluation argument for a specific argument

        :Call:
            >>> db.set_arg_converter(k, fn)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *k*: :class:`str`
                Name of evaluation argument
            *fn*: :class:`function`
                Conversion function
        :Versions:
            * 2019-02-28 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check input
        if not callable(fn):
            raise TypeError("Converter is not callable")
        # Get dictionary of converters
        arg_converters = self.__dict__.setdefault("eval_arg_converters", {})
        # Save function
        arg_converters[k] = fn

    # Set eval argument aliases
    def set_eval_arg_aliases(self, col, aliases):
        r"""Set alias names for evaluation args for a data column

        :Call:
            >>> db.set_eval_arg_aliases(col, aliases)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
            *aliases*: {``{}``} | :class:`dict`
                Alternate names for args while evaluationg *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Transform any False-like thing to {}
        if not aliases:
            aliases = {}
        # Get attribute
        arg_aliases = self.__dict__.setdefault("eval_arg_aliases", {})
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be string (got %s)" % type(col))
        elif not isinstance(arg_aliases, dict):
            raise TypeError("eval_arg_aliases attribute is not a dict")
        elif not isinstance(aliases, dict):
            raise TypeError(
                "aliases arg must be dict (got %s)" % type(aliases))
        # Check key-value types
        for (k, v) in aliases.items():
            # Check key
            if not typeutils.isstr(k):
                raise TypeError(
                    "Found alias key for '%s' that is not a string" % col)
            if not typeutils.isstr(v):
                raise TypeError(
                    "Alias for '%s' in col '%s' is not a string" % (k, col))
        # Save it
        arg_aliases[col] = aliases

    # Set eval argument keyword arguments
    def set_eval_kwargs(self, col, kwargs):
        r"""Set evaluation keyword arguments for *col* evaluator

        :Call:
            >>> db.set_eval_kwargs(col, kwargs)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of data column to evaluate
            *kwargs*: {``{}``} | :class:`dict`
                Keyword arguments to add while evaluating *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Transform any False-like thing to {}
        if not kwargs:
            kwargs = {}
        # Get attribute
        eval_kwargs = self.__dict__.setdefault("eval_kwargs", {})
        # Check types
        if not typeutils.isstr(col):
            raise TypeError(
                "Data column name must be string (got %s)" % type(col))
        elif not isinstance(eval_kwargs, dict):
            raise TypeError("eval_kwargs attribute is not a dict")
        elif not isinstance(kwargs, dict):
            raise TypeError(
                "kwargs must be dict (got %s)" % type(kwargs))
        # Check key-value types
        for (k, v) in kwargs.items():
            # Check key
            if not typeutils.isstr(k):
                raise TypeError(
                    "Found keyword for '%s' that is not a string" % col)
        # Save it
        eval_kwargs[col] = kwargs

    # Set xvars for output
    def set_output_xvars(self, col, xargs):
        r"""Set list of args to output for column *col*

        :Call:
            >>> db.set_output_xvars(col, xargs)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseLinear`
                Database with multidimensional output functions
            *col*: :class:`str`
                Name of column to evaluate
                List of input args to one condition of *col*
        :Versions:
            * 2019-12-30 ``@ddalle``: First version
        """
        # Get column definition
        defn = self.get_defn(col)
        # De-None
        if xargs is None:
            xargs = []
        # Check type
        if not isinstance(xargs, list):
            raise TypeError(
                "OutputXVars for col '%s' must be list (got %s)"
                % (col, type(xargs)))
        # Check contents
        for (j, k) in enumerate(xargs):
            if not typeutils.isstr(k):
                raise TypeError(
                    "Output arg %i for col '%s' must be str (got %s)"
                    % (j, col, type(k)))
        # Set (copy)
        defn["OutputXVars"] = list(xargs)

   # --- Arguments ---
    # Attempt to get all values of an argument
    def get_all_values(self, k):
        r"""Attempt to get all values of a specified argument

        This will use *db.eval_arg_converters* if possible.

        :Call:
            >>> V = db.get_all_values(k)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *k*: :class:`str`
                Name of evaluation argument
        :Outputs:
            *V*: ``None`` | :class:`np.ndarray`\ [:class:`float`]
                *db[k]* if available, otherwise an attempt to apply
                *db.eval_arg_converters[k]*
        :Versions:
            * 2019-03-11 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check if present
        if k in self:
            # Get values
            return self[k]
        # Otherwise check for evaluation argument
        arg_converters = self.__dict__.get("eval_arg_converters", {})
        # Check if there's a converter
        if k not in arg_converters:
            return None
        # Get converter
        f = arg_converters.get(k)
        # Check if there's a converter
        if f is None:
            # No converter
            return
        elif not callable(f):
            # Not callable
            raise TypeError("Converter for col '%s' is not callable" % k)
        # Attempt to apply it
        try:
            # Call in keyword-only mode
            V = f(**self)
            # Return values
            return V
        except Exception:
            # Failed
            return None

    # Attempt to get values of an argument or column, with mask
    def get_values(self, col, I=None):
        r"""Attempt to get all or some values of a specified column

        This will use *db.eval_arg_converters* if possible.

        :Call:
            >>> V = db.get_values(col)
            >>> V = db.get_values(col, I=None)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of evaluation argument
            *I*: :class:`np.ndarray`\ [:class:`int` | :class:`bool`]
                Optional subset of *db* indices to access
        :Outputs:
            *V*: ``None`` | :class:`np.ndarray`\ [:class:`float`]
                *db[col]* if available, otherwise an attempt to apply
                *db.eval_arg_converters[col]*
        :Versions:
            * 2020-02-21 ``@ddalle``: First version
        """
        # Get all values
        V = self.get_all_values(col)
        # Check for empty result
        if V is None:
            return
        # Check for mask
        if I is None:
            # No mask
            return V
        # Check mask
        if not isinstance(I, np.ndarray):
            raise TypeError("Index mask must be NumPy array")
        elif I.ndim != 1:
            raise IndexError("Index mask must be 1D array")
        elif I.size == 0:
            raise ValueError("Index mask must not be empty")
        # Size of full array
        n = V.size
        # Get data type (as string)
        dtype = I.dtype.name
        # Check type
        if "int" in dtype:
            # Check indices
            if np.max(I) >= n:
                raise IndexError(
                    ("Cannot access element %i " % np.max(I)) +
                    ("for array of length %i" % n))
            # Access
            return V[I]
        elif dtype == "bool":
            # Check size
            if I.size != n:
                raise IndexError(
                    ("Bool index mask has size %i; " % I.size) +
                    ("array has size %i" % n))
            # Access
            return V[I]
        else:
            raise TypeError("Index mask must be int or bool array")

    # Get argument value
    def get_arg_value(self, i, k, *a, **kw):
        r"""Get the value of the *i*\ th argument to a function

        :Call:
            >>> v = db.get_arg_value(i, k, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *i*: :class:`int`
                Argument index within *db.eval_args*
            *k*: :class:`str`
                Name of evaluation argument
            *a*: :class:`tuple`
                Arguments to :func:`__call__`
            *kw*: :class:`dict`
                Keyword arguments to :func:`__call__`
        :Outputs:
            *v*: :class:`float` | :class:`np.ndarray`
                Value of the argument, possibly converted
        :Versions:
            * 2019-02-28 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Number of direct arguments
        na = len(a)
        # Converters
        arg_converters = self.__dict__.get("eval_arg_converters", {})
        arg_defaults   = self.__dict__.get("eval_arg_defaults",   {})
        # Check for sufficient non-keyword inputs
        if na > i:
            # Directly specified
            xi = kw.get(k, a[i])
        else:
            # Get from keywords
            xi = kw.get(k)
        # In most cases, this is sufficient
        if xi is not None:
            return xi
        # Check for a converter
        fk = arg_converters.get(k)
        # Apply converter
        if fk:
            # Apply converters
            try:
                # Convert values
                try:
                    # Use args and kwargs
                    xi = fk(*x, **kw)
                except Exception:
                    # Use just kwargs
                    xi = fk(**kw)
                # Save it
                if xi is not None: return xi
            except Exception:
                # Function failure
                print("Eval argument converter for '%s' failed" % k)
        # Get default
        xi = arg_defaults.get(k)
        # Final check
        if xi is None:
            # No value determined
            raise ValueError(
                "Could not determine value for argument '%s'" % k)
        else:
            # Final output
            return xi

    # Get dictionary of argument values
    def get_arg_value_dict(self, *a, **kw):
        r"""Return a dictionary of normalized argument variables

        Specifically, he dictionary contains a key for every argument used to
        evaluate the coefficient that is either the first argument or uses the
        keyword argument *coeff*.

        :Call:
            >>> X = db.get_arg_value_dict(*a, **kw)
            >>> X = db.get_arg_value_dict(coeff, x1, x2, ..., k3=x3)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *coeff*: :class:`str`
                Name of coefficient
            *x1*: :class:`float` | :class:`np.ndarray`
                Value(s) of first argument
            *x2*: :class:`float` | :class:`np.ndarray`
                Value(s) of second argument, if applicable
            *k3*: :class:`str`
                Name of third argument or optional variant
            *x3*: :class:`float` | :class:`np.ndarray`
                Value(s) of argument *k3*, if applicable
        :Outputs:
            *X*: :class:`dict` (:class:`np.ndarray`)
                Dictionary of values for each key used to evaluate *coeff*
                according to *b.eval_args[coeff]*; each entry of *X* will
                have the same size
        :Versions:
            * 2019-03-12 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
       # --- Get coefficient name ---
        # Coeff name should be either a[0] or kw["coeff"]
        coeff, a, kw = self._prep_args_colname(*a, **kw)
       # --- Argument processing ---
        # Specific lookup arguments
        args_coeff = self.get_eval_args(coeff)
        # Initialize lookup point
        x = []
        # Loop through arguments
        for i, k in enumerate(args_coeff):
            # Get value
            xi = self.get_arg_value(i, k, *a, **kw)
            # Save it
            x.append(np.asarray(xi))
        # Normalize arguments
        xn, dims = self.normalize_args(x)
       # --- Output ---
        # Initialize
        X = {}
        # Loop through args
        for i, k in enumerate(args_coeff):
            # Save value
            X[k] = xn[i]
        # Output
        return X

    # Process coefficient name
    def _prep_args_colname(self, *a, **kw):
        r"""Process coefficient name from arbitrary inputs

        :Call:
            >>> col, a, kw = db._prep_args_colname(*a, **kw)
            >>> col, a, kw = db._prep_args_colname(col, *a, **kw)
            >>> col, a, kw = db._prep_args_colname(*a, col=c, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of evaluation col
            *a*: :class:`tuple`
                Other sequential inputs
            *kw*: :class:`dict`
                Other keyword inputs
        :Outputs:
            *col*: :class:`str`
                Name of column to evaluate, from *a[0]* or *kw["col"]*
            *a*: :class:`tuple`
                Remaining inputs with coefficient name removed
            *kw*: :class:`dict`
                Keyword inputs with coefficient name removed
        :Versions:
            * 2019-03-12 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2019-12-18 ``@ddalle``: From :func:`_process_coeff`
        """
        # Check for keyword
        coeff = kw.pop("coeff", None)
        # Check for string
        if typeutils.isstr(coeff):
            # Output
            return coeff, a, kw
        # Number of direct inputs
        na = len(a)
        # Process *coeff* from *a* if possible
        if na > 0:
            # First argument is coefficient
            coeff = a[0]
            # Check for string
            if typeutils.isstr(coeff):
                # Remove first entry
                a = a[1:]
                # Output
                return coeff, a, kw
        # Must be string-like
        raise TypeError("Coefficient must be a string")

    # Normalize arguments
    def normalize_args(self, x, asarray=False):
        r"""Normalized mixed float and array arguments

        :Call:
            >>> X, dims = db.normalize_args(x, asarray=False)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *x*: :class:`list`\ [:class:`float` | :class:`np.ndarray`]
                Values for arguments, either float or array
            *asarray*: ``True`` | {``False``}
                Force array output (otherwise allow scalars)
        :Outputs:
            *X*: :class:`list`\ [:class:`float` | :class:`np.ndarray`]
                Normalized arrays/floats all with same size
            *dims*: :class:`tuple` (:class:`int`)
                Original dimensions of non-scalar input array
        :Versions:
            * 2019-03-11 ``@ddalle``: First version
            * 2019-03-14 ``@ddalle``: Added *asarray* input
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
            * 2019-12-18 ``@ddalle``: Removed ``@staticmethod``
        """
        # Input size by argument
        nxi = [xi.size for xi in x]
        ndi = [xi.ndim for xi in x]
        # Maximum size
        nx = np.max(nxi)
        nd = np.max(ndi)
        # Index of maximum size
        ix = nxi.index(nx)
        # Corresponding shape
        dims = x[ix].shape
        # Check for forced array output
        if asarray and (nd == 0):
            # Ensure 1D output
            nd = 1
            dims = (1,)
        # Initialize final arguments
        X = []
        # Loop through arguments again
        for (i, xi) in enumerate(x):
            # Check for trivial case
            if nd == 0:
                # Save scalar
                X.append(xi)
                continue
            # Get sizes
            nxk = nxi[i]
            ndk = ndi[i]
            # Check for expansion
            if ndk == 0:
                # Scalar to array
                X.append(xi*np.ones(nx))
            elif ndk != nd:
                # Inconsistent size
                raise ValueError(
                    "Cannot normalize %iD and %iD inputs" % (ndk, nd))
            elif nxk != nx:
                # Inconsistent size
                raise IndexError(
                    "Cannot normalize inputs with size %i and %i" % (nxk, nx))
            else:
                # Already array
                X.append(xi.flatten())
        # Output
        return X, dims

   # --- Breakpoint Schedule ---
    # Return break points for schedule
    def get_schedule(self, args, x, extrap=True):
        r"""Get lookup points for interpolation scheduled by master key

        This is a utility that is used for situations where the break
        points of some keys may vary as a schedule of another one.
        For example if the maximum angle of attack in the database is
        different at each Mach number.  This utility provides the
        appropriate point at which to interpolate the remaining keys
        at the value of the first key both above and below the input
        value.  The first argument, ``args[0]``, is the master key
        that controls the schedule.

        :Call:
            >>> i0, i1, f, x0, x1 = db.get_schedule(args, x, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *args*: :class:`list`\ [:class:`str`]
                List of input argument names (*args[0]* is master key)
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *extrap*: {``True``} | ``False``
                If ``False``, raise error when lookup value is outside
                break point range for any key at any slice
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is at upper bound
            *x0*: :class:`np.ndarray` (:class:`float`)
                Evaluation values for ``args[1:]`` at *i0*
            *x1*: :class:`np.ndarray` (:class:`float`)
                Evaluation values for ``args[1:]`` at *i1*
        :Versions:
            * 2019-04-19 ``@ddalle``: First version
            * 2019-07-26 ``@ddalle``: Vectorized
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Number of args
        narg = len(args)
        # Error check
        if narg < 2:
            raise ValueError("At least two args required for scheduled lookup")
        # Flag for array or scalar
        qvec = False
        # Number of points in arrays (if any)
        n = None
        # Loop through args
        for i, k in enumerate(args):
            # Get value
            V = x[i]
            # Check type
            if typeutils.isarray(V):
                # Turn on array flag
                qvec = True
                # Get size
                nk = len(V)
                # Check consistency
                if n is None:
                    # New size
                    n = nk
                elif nk != n:
                    # Inconsistent size
                    raise ValueError(
                        "Eval arg '%s' has size %i, expected %i" % (k, nk, n))
            elif not isinstance(V, (float, int, np.ndarray)):
                # Improper type
                raise TypeError(
                    "Eval arg '%s' has type '%s'" % (k, type(V)))
        # Check for arrays
        if not qvec:
            # Call scalar version
            return self._get_schedule(args, x, extrap=extrap)
        # Initialize tuple of fixed-size lookup points
        X = tuple()
        # Loop through args again
        for i, k in enumerate(args):
            # Get value
            V = x[i]
            # Check type
            if isinstance(V, (float, int)):
                # Create constant-value array
                X += (V * np.ones(n),)
            else:
                # Copy array
                X += (V,)
        # Otherwise initialize arrays
        I0 = np.zeros(n, dtype="int")
        I1 = np.zeros(n, dtype="int")
        F  = np.zeros(n)
        # Initialize tuples of modified lookup points
        X0 = tuple([np.zeros(n) for i in range(narg-1)])
        X1 = tuple([np.zeros(n) for i in range(narg-1)])
        # Loop through points
        for j in range(n):
            # Get lookup points
            xj = tuple([X[i][j] for i in range(narg)])
            # Evaluations
            i0, i1, f, x0, x1 = self._get_schedule(
                list(args), xj, extrap=extrap)
            # Save indices
            I0[j] = i0
            I1[j] = i1
            # Save lookup fraction
            F[j] = f
            # Save modified lookup points
            for i in range(narg-1):
                X0[i][j] = x0[i]
                X1[i][j] = x1[i]
        # Output
        return I0, I1, F, X0, X1

    # Return break points for schedule
    def _get_schedule(self, args, x, extrap=True):
        r"""Get lookup points for interpolation scheduled by master key

        This is a utility that is used for situations where the break
        points of some keys may vary as a schedule of another one.
        For example if the maximum angle of attack in the database is
        different at each Mach number.  This utility provides the
        appropriate point at which to interpolate the remaining keys
        at the value of the first key both above and below the input
        value.  The first argument, ``args[0]``, is the master key
        that controls the schedule.

        :Call:
            >>> i0, i1, f, x0, x1 = db.get_schedule(args, x, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *args*: :class:`list`\ [:class:`str`]
                List of input argument names (*args[0]* is master key)
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *extrap*: {``True``} | ``False``
                If ``False``, raise error when lookup value is outside
                break point range for any key at any slice
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is at upper bound
            *x0*: :class:`np.ndarray` (:class:`float`)
                Evaluation values for ``args[1:]`` at *i0*
            *x1*: :class:`np.ndarray` (:class:`float`)
                Evaluation values for ``args[1:]`` at *i1*
        :Versions:
            * 2019-04-19 ``@ddalle``: First version
        """
        # Error check
        if len(args) < 2:
            raise ValueError("At least two args required for scheduled lookup")
        # Slice/scheduling key
        skey = args.pop(0)
        # Lookup value for first variable
        i0, i1, f = self.get_bkpt_index(skey, x[0])
        # Number of additional args
        narg = len(args)
        # Initialize lookup points at slice *i0* and slice *i1*
        x0 = np.zeros(narg)
        x1 = np.zeros(narg)
        # Loop through arguments
        for j, k in enumerate(args):
            # Get min and max values
            try:
                # Try the case of varying break points indexed to *skey*
                xmin0 = self.get_bkpt(k, i0, 0)
                xmin1 = self.get_bkpt(k, i1, 0)
                xmax0 = self.get_bkpt(k, i0, -1)
                xmax1 = self.get_bkpt(k, i1, -1)
            except TypeError:
                # Fixed break points (apparently)
                xmin0 = self.get_bkpt(k, 0)
                xmin1 = self.get_bkpt(k, 0)
                xmax0 = self.get_bkpt(k, -1)
                xmax1 = self.get_bkpt(k, -1)
            # Interpolate to current *skey* value
            xmin = (1-f)*xmin0 + f*xmin1
            xmax = (1-f)*xmax0 + f*xmax1
            # Get the progress fraction at current inter-slice *skey* value
            fj = (x[j+1] - xmin) / (xmax-xmin)
            # Check for extrapolation
            if not extrap and ((fj < -1e-3) or (fj - 1 > 1e-3)):
                # Raise extrapolation error
                raise ValueError(
                    ("Lookup value %.4e is outside " % x[j+1]) +
                    ("scheduled bounds [%.4e, %.4e]" % (xmin, xmax)))
            # Get lookup points at slices *i0* and *i1* using this prog frac
            x0[j] = (1-fj)*xmin0 + fj*xmax0
            x1[j] = (1-fj)*xmin1 + fj*xmax1
        # Output
        return i0, i1, f, x0, x1

   # --- Nearest/Exact ---
    # Find exact match
    def eval_exact(self, col, args, x, **kw):
        r"""Evaluate a coefficient by looking up exact matches

        :Call:
            >>> y = db.eval_exact(col, args, x, **kw)
            >>> Y = db.eval_exact(col, args, x, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of explanatory col names (numeric)
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *tol*: {``1.0e-4``} | :class:`float` > 0
                Default tolerance for exact match
            *tols*: {``{}``} | :class:`dict`\ [:class:`float` > 0]
                Dictionary of key-specific tolerances
        :Outputs:
            *y*: ``None`` | :class:`float` | *db[col].__class__*
                Value of ``db[col]`` exactly matching conditions *x*
            *Y*: :class:`np.ndarray`
                Multiple values matching exactly
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check for column
        if (col not in self.cols) or (col not in self):
            # Missing col
            raise KeyError("Col '%s' is not present" % col)
        # Get values
        V = self[col]
        # Create mask
        I = np.arange(len(V))
        # Tolerance dictionary
        tols = kw.get("tols", {})
        # Default tolerance
        tol = 1.0e-4
        # Loop through keys
        for (i, k) in enumerate(args):
            # Get value
            xi = x[i]
            # Get tolerance
            toli = tols.get(k, kw.get("tol", tol))
            # Apply test
            qi = np.abs(self[k][I] - xi) <= toli
            # Combine constraints
            I = I[qi]
            # Break if no matches
            if len(I) == 0:
                return None
        # Test number of outputs
        if len(I) == 1:
            # Single output
            return V[I[0]]
        else:
            # Multiple outputs
            return V[I]

    # Lookup nearest value
    def eval_nearest(self, col, args, x, **kw):
        r"""Evaluate a coefficient by looking up nearest match

        :Call:
            >>> y = db.eval_nearest(col, args, x, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of (numeric) column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of explanatory col names (numeric)
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *weights*: {``{}``} | :class:`dict` (:class:`float` > 0)
                Dictionary of key-specific distance weights
        :Outputs:
            *y*: :class:`float` | *db[col].__class__*
                Value of *db[col]* at point closest to *x*
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check for column
        if (col not in self.cols) or (col not in self):
            # Missing col
            raise KeyError("Col '%s' is not present" % col)
        # Get values
        V = self[col]
        # Array length
        n = len(V)
        # Initialize distances
        d = np.zeros(n, dtype="float")
        # Dictionary of distance weights
        W = kw.get("weights", {})
        # Loop through keys
        for (i, k) in enumerate(args):
            # Get value
            xi = x[i]
            # Get weight
            wi = W.get(k, 1.0)
            # Distance
            d += wi*(self[k] - xi)**2
        # Find minimum distance
        j = np.argmin(d)
        # Use that value
        return V[j]

   # --- Linear ---
    # Multilinear lookup
    def eval_multilinear(self, col, args, x, **kw):
        r"""Perform linear interpolation in *n* dimensions

        This assumes the database is ordered with the first entry of
        *args* varying the most slowly and that the data is perfectly
        regular.

        :Call:
            >>> y = db.eval_multilinear(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *bkpt*: ``True`` | {``False``}
                Flag to interpolate break points instead of data
        :Outputs:
            *y*: ``None`` | :class:`float` | ``db[col].__class__``
                Interpolated value from ``db[col]``
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Call root method without two of the options
        return self._eval_multilinear(col, args, x, **kw)

    # Evaluate multilinear interpolation with caveats
    def _eval_multilinear(self, col, args, x, I=None, j=None, **kw):
        r"""Perform linear interpolation in *n* dimensions

        This assumes the database is ordered with the first entry of
        *args* varying the most slowly and that the data is perfectly
        regular.

        :Call:
            >>> y = db._eval_multilinear(col, args, x, I=None, j=None)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *I*: {``None``} | :class:`np.ndarray`\ [:class:`int`]
                Optional subset of database on which to perform
                interpolation
            *j*: {``None``} | :class:`int`
                Slice index, used by :func:`eval_multilinear_schedule`
            *bkpt*: ``True`` | {``False``}
                Flag to interpolate break points instead of data
        :Outputs:
            *y*: ``None`` | :class:`float` | ``DBc[coeff].__class__``
                Interpolated value from ``DBc[coeff]``
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-04-19 ``@ddalle``: Moved from :func:`eval_multilnear`
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check for break-point evaluation flag
        bkpt = kw.get("bkpt", kw.get("breakpoint", False))
        # Possible values
        try:
            # Extract coefficient
            if bkpt:
                # Lookup from breakpoints
                V = self.bkpts[col]
            else:
                # Lookup from main data
                V = self[col]
        except KeyError:
            # Missing key
            raise KeyError("Coefficient '%s' is not present" % coeff)
        # Subset if appropriate
        if I is not None:
            # Attempt to subset
            try:
                # Select some indices
                V = V[I]
            except Exception:
                # Informative error
                raise ValueError(
                    "Failed to subset col '%s' using class '%s'"
                    % (coeff, I.__class__))
        # Number of keys
        nk = len(args)
        # Dimension
        ndim = V.ndim
        # Check it
        if ndim not in [1, 2]:
            raise ValueError(
                "Col '%s' must have dimension 1 or 2; got %i" % (col, ndim))
        # Count
        n = V.shape[-1]
        # Get break points for this schedule
        bkpts = {}
        for k in args:
            bkpts[k] = self._scheduled_bkpts(k, j)
        # Lengths for each variable
        N = [len(bkpts[k]) for k in args]
        # Check consistency
        if np.prod(N) != n:
            raise ValueError(
                ("Column '%s' has size %i, " % (col, n)),
                ("but total size of args %s is %i." % (args, np.prod(N))))
        # Initialize list of indices for each key
        I0 = []
        I1 = []
        F1 = []
        # Get lookup indices for each argument
        for (i, k) in enumerate(args):
            # Lookup value
            xi = x[i]
            # Values
            Vk = bkpts[k]
            # Get indices
            i0, i1, f = self._bkpt_index(Vk, xi)
            # Check for problems
            if i0 is None:
                # Below
                raise ValueError(
                    ("Value %s=%.4e " % (k, xi)) +
                    ("below lower bound (%.4e)" % Vk[0]))
            elif i1 is None:
                raise ValueError(
                    ("Value %s=%.4e " % (k, xi)) +
                    ("above upper bound (%.4e)" % Vk[-1]))
            # Save values
            I0.append(i0)
            I1.append(i1)
            F1.append(f)
        # Index of the lowest corner
        j0 = 0
        # Loop through the keys
        for i in range(nk):
            # Get value
            i0 = I0[i]
            # Overall ; multiply index by size of remaining block
            j0 += i0 * int(np.prod(N[i+1:]))
        # Initialize overall indices and weights
        J = j0 * np.ones(2**nk, dtype="int")
        F = np.ones(2**nk)
        # Counter from 0 to 2^nk-1
        E = np.arange(2**nk)
        # Loop through keys again
        for i in range(nk):
            # Exponent of two to use for this key
            e = nk - i
            # Up or down for each of the 2^nk individual lookup points
            jupdown = E % 2**e // 2**(e-1)
            # Size of remaining block
            subblock = int(np.prod(N[i+1:]))
            # Increment overall indices
            J += jupdown*subblock
            # Progress fraction for this variable
            fi = F1[i]
            # Convert up/down to either fi or 1-fi
            Fi = (1-fi)*(1-jupdown) + jupdown*fi
            # Apply weights
            F *= Fi
        # Perform interpolation
        if ndim == 1:
            # Regular weighted sum of scalars
            return np.sum(F*V[J])
        elif ndim == 2:
            # Weighted dot product (of columns)
            return np.dot(V[:,J], F)

   # --- Multilinear-schedule ---
    # Multilinear lookup at each value of arg
    def eval_multilinear_schedule(self, col, args, x, **kw):
        r"""Perform "scheduled" linear interpolation in *n* dimensions

        This assumes the database is ordered with the first entry of
        *args* varying the most slowly and that the data is perfectly
        regular.  However, each slice at a constant value of *args[0]*
        may have separate break points for all the other args.  For
        example, the matrix of angle of attack and angle of sideslip
        may be different at each Mach number.  In this case, *db.bkpts*
        will be a list of 1D arrays for *alpha* and *beta* and just a
        single 1D array for *mach*.

        :Call:
            >>> y = db.eval_multilinear(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
            *tol*: {``1e-6``} | :class:`float` >= 0
                Tolerance for matching slice key
        :Outputs:
            *y*: ``None`` | :class:`float` | ``db[col].__class__``
                Interpolated value from ``db[col]``
        :Versions:
            * 2019-04-19 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Slice tolerance
        tol = kw.get("tol", 1e-6)
        # Name of master (slice) key
        skey = args[0]
        # Get lookup points at both sides of scheduling key
        i0, i1, f, x0, x1 = self.get_schedule(args, x, extrap=False)
        # Get the values for the slice key
        x00 = self.get_bkpt(skey, i0)
        x01 = self.get_bkpt(skey, i1)
        # Find indices of the two slices
        I0 = np.where(np.abs(self[skey] - x00) <= tol)[0]
        I1 = np.where(np.abs(self[skey] - x01) <= tol)[0]
        # Perform interpolations
        y0 = self._eval_multilinear(col, args, x0, I=I0, j=i0)
        y1 = self._eval_multilinear(col, args, x1, I=I1, j=i1)
        # Linear interpolation in the schedule key
        return (1-f)*y0 + f*y1

   # --- Radial Basis Functions ---
    # RBF lookup
    def eval_rbf(self, col, args, x, **kw):
        """Evaluate a single radial basis function

        :Call:
            >>> y = DBc.eval_rbf(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
        :Outputs:
            *y*: :class:`float` | :class:`np.ndarray`
                Interpolated value from *db[col]*
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get the radial basis function
        f = self.get_rbf(col)
        # Evaluate
        return f(*x)

    # Get an RBF
    def get_rbf(self, col, *I):
        r"""Extract a radial basis function, with error checking

        :Call:
            >>> f = db.get_rbf(col, *I)
            >>> f = db.get_rbf(col)
            >>> f = db.get_rbf(col, i)
            >>> f = db.get_rbf(col, i, j)
            >>> f = db.get_rbf(col, i, j, ...)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *I*: :class:`tuple`
                Tuple of lookup indices
            *i*: :class:`int`
                (Optional) first RBF list index
            *j*: :class:`int`
                (Optional) second RBF list index
        :Outputs:
            *f*: :class:`scipy.interpolate.rbf.Rbf`
                Callable radial basis function
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get the radial basis function
        try:
            fn = self.rbf[col]
        except AttributeError:
            # No radial basis functions at all
            raise AttributeError("No radial basis functions found")
        except KeyError:
            # No RBF for this coefficient
            raise KeyError("No radial basis function for col '%s'" % col)
        # Number of indices given
        nd = len(I)
        # Loop through indices
        for n, i in enumerate(I):
            # Try to extract
            try:
                # Get the *ith* list entry
                fn = fn[i]
            except TypeError:
                # Reached RBF too soon
                raise TypeError(
                    ("RBF for '%s':\n" % col) +
                    ("Expecting %i-dimensional " % nd) +
                    ("array but found %i-dim" % n))
        # Test type
        if not callable(fn):
            raise TypeError("RBF '%s' index %i is not callable" % (col, I))
        # Output
        return fn

   # --- RBF-linear ---
    # Multiple RBF lookup
    def eval_rbf_linear(self, col, args, x, **kw):
        r"""Evaluate two RBFs at slices of first *arg* and interpolate

        :Call:
            >>> y = db.eval_rbf_linear(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
        :Outputs:
            *y*: :class:`float` | :class:`np.ndarray`
                Interpolated value from *db[col]*
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Lookup value for first variable
        i0, i1, f = self.get_bkpt_index(args[0], x[0])
        # Get lookup functions for *i0* and *i1*
        f0 = self.get_rbf(col, i0)
        f1 = self.get_rbf(col, i1)
        # Evaluate both functions
        y0 = f0(*x[1:])
        y1 = f1(*x[1:])
        # Interpolate
        y = (1-f)*y0 + f*y1
        # Output
        return y

   # --- RBF-schedule ---
    # Multiple RBF lookup, curvilinear
    def eval_rbf_schedule(self, col, args, x, **kw):
        r"""Evaluate two RBFs at slices of first *arg* and interpolate

        :Call:
            >>> y = db.eval_rbf_schedule(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
        :Outputs:
            *y*: :class:`float` | :class:`np.ndarray`
                Interpolated value from *db[col]*
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
        """
        # Extrapolation option
        extrap = kw.get("extrap", False)
        # Get lookup points at both sides of scheduling key
        i0, i1, f, x0, x1 = self.get_schedule(list(args), x, extrap=extrap)
        # Get lookup functions for *i0* and *i1*
        f0 = self.get_rbf(col, i0)
        f1 = self.get_rbf(col, i1)
        # Evaluate the RBFs at both slices
        y0 = f0(*x0)
        y1 = f1(*x1)
        # Interpolate between the slices
        y = (1-f)*y0 + f*y1
        # Output
        return y

   # --- Generic Function ---
    # Generic function
    def eval_function(self, col, args, x, **kw):
        r"""Evaluate a single user-saved function

        :Call:
            >>> y = db.eval_function(col, args, x)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
            *args*: :class:`list` | :class:`tuple`
                List of lookup key names
            *x*: :class:`list` | :class:`tuple` | :class:`np.ndarray`
                Vector of values for each argument in *args*
        :Outputs:
            *y*: ``None`` | :class:`float` | ``DBc[coeff].__class__``
                Interpolated value from ``DBc[coeff]``
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get the function
        f = self.get_eval_func(col)
        # Evaluate
        if self.eval_func_self.get(col):
            # Use reference to *self*
            return f(self, *x, **kw)
        else:
            # Stand-alone function
            return f(*x, **kw)
  # >

  # ===================
  # Break Points
  # ===================
  # <
   # --- Breakpoint Creation ---
    # Get automatic break points
    def get_bkpts(self, cols, nmin=5, tol=1e-12):
        r"""Create automatic list of break points for interpolation

        :Call:
            >>> db.get_bkpts(col, nmin=5, tol=1e-12)
            >>> db.get_bkpts(cols, nmin=5, tol=1e-12)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *col*: :class:`str`
                Individual lookup variable
            *cols*: :class:`list`\ [:class:`str`]
                List of lookup variables
            *nmin*: {``5``} | :class:`int` > 0
                Minimum number of data points at one value of a key
            *tol*: {``1e-12``} | :class:`float` >= 0
                Tolerance cutoff
        :Outputs:
            *DBc.bkpts*: :class:`dict`
                Dictionary of 1D unique lookup values
            *DBc.bkpts[key]*: :class:`np.ndarray` (:class:`float`)
                Unique values of *DBc[key]* with at least *nmin* entries
        :Versions:
            * 2018-06-08 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Updated for :mod:`rdbnull`
        """
        # Check for single key list
        if not isinstance(cols, (list, tuple)):
            # Make list
            cols = [cols]
        # Initialize break points
        bkpts = self.__dict__.setdefault("bkpts", {})
        # Loop through keys
        for col in cols:
            # Check type
            if not isinstance(col, typeutils.strlike):
                raise TypeError("Column name is not a string")
            # Check if present
            if col not in self.cols:
                raise KeyError("Lookup column '%s' is not present" % col)
            # Get all values
            V = self[col]
            # Get data type
            dtype = self.get_col_dtype(col)
            # Check dtype
            if dtype == "str":
                # Get unique values without converting to array
                B = list(set(V))
            elif dtype.startswith("int"):
                # No need to apply tolerance
                B = np.unique(V)
            else:
                # Get unique values of array
                U = np.unique(V)
                # Initialize filtered value
                B = np.zeros_like(U)
                n = 0
                # Loop through entries
                for v in U:
                    # Check if too close to a previous entry
                    if (n > 0) and np.min(np.abs(v - B[:n])) <= tol:
                        # Close to previous "unique" value
                        continue
                    # Count entries
                    if np.count_nonzero(np.abs(V - v) <= tol) >= nmin:
                        # Save the value
                        B[n] = v
                        # Increase count
                        n += 1
                # Trim
                B = B[:n]
            # Save these break points
            bkpts[col] = B

    # Map break points from other key
    def map_bkpts(self, cols, scol, tol=1e-12):
        r"""Map break points of one column to one or more others

        The most common purpose to use this method is to create
        non-ascending break points.  One common example is to keep track
        of the dynamic pressure values at each Mach number.  These
        dynamic pressures may be unique, but sorting them by dynamic
        pressure is different from the order in which they occur in
        flight.

        :Call:
            >>> db.map_bkpts(cols, scol, tol=1e-12)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *cols*: :class:`list`\ [:class:`str`]
                Individual lookup variable
            *scol*: :class:`str`
                Name of key to drive map/schedule
            *tol*: {``1e-12``} | :class:`float` >= 0
                Tolerance cutoff (used for *scol*)
        :Outputs:
            *DBc.bkpts*: :class:`dict`
                Dictionary of 1D unique lookup values
            *DBc.bkpts[key]*: :class:`np.ndarray` (:class:`float`)
                Unique values of *DBc[key]* with at least *nmin* entries
        :Versions:
            * 2018-06-29 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Ported to :mod:`rdbnull`
        """
        # Check inputs
        if not isinstance(cols, list):
            raise TypeError("Columns input must be a list")
        elif not isinstance(scol, typeutils.strlike):
            raise TypeError("Schedule key must be a string")
        # Get break points
        bkpts = self.__dict__.get("bkpts")
        # Check break points for *scol*
        if bkpts is None:
            raise AttributeError("No 'bkpts' attribute; call get_bkpts()")
        elif scol not in bkpts:
            raise AttributeError("No bkpts for col '%s'" % col)
        # Get data type of *scol*
        dtype = self.get_col_dtype(scol)
        # Check data type
        if not (dtype.startswith("float") or dtype.startswith("int")):
            raise TypeError(
                ("Schedule col '%s' must have either " % scol) +
                ("float or int type (got %s)" % dtype))
        # Get schedule break points and nominal values
        V0 = self[scol]
        U0 = self.bkpts[scol]
        # Loop through keys
        for col in cols:
            # Check type
            if not isinstance(col, typeutils.strlike):
                raise TypeError("Column name is not a string")
            # Check if present
            if col not in self.cols:
                raise KeyError("Lookup column '%s' is not present" % col)
            # Get data type
            dtype = self.get_col_dtype(col)
            # Check it
            if not (dtype.startswith("float") or dtype.startswith("int")):
                raise TypeError(
                    ("Break point col '%s' must have either " % col) +
                    ("float or int type (got %s)" % dtype))
            # Values for *col*
            V = self[col]
            # Initialize break point array for *col*
            U = np.zeros(U0.size, dtype=dtype)
            # Check shape
            if V.size != V0.size:
                raise ValueError(
                    ("Col '%s' (%i) has different size " % (col, V.size)) +
                    ("from schedule col '%s' (%i)" % (scol, V0.size)))
            # Loop through slice values
            for (j, v0) in enumerate(U0):
                # Find value of slice key matching that parameter
                i = np.where(np.abs(V0 - v0) <= tol)[0][0]
                # Save value of that index from col
                V[j] = V[i]
            # Save break points
            bkpts[col] = V

    # Schedule break points at slices at other key
    def schedule_bkpts(self, cols, scol, nmin=5, tol=1e-12):
        r"""Create lists of unique values at each unique value of *scol*

        This function creates a break point list of the unique values of
        each *col* in *cols* at each unique value of a "scheduling"
        column *scol*.  For example, if a different run matrix of
        *alpha* and *beta* is used at each *mach* number, this function
        creates a list of the unique *alpha* and *beta* values for each
        Mach number in *db.bkpts["mach"]*.

        :Call:
            >>> db.schedule_bkpts(cols, scol)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *cols*: :class:`list`\ [:class:`str`]
                Individual lookup variable
            *scol*: :class:`str`
                Name of key to drive map/schedule
            *nmin*: {``5``} | :class:`int` > 0
                Minimum number of data points at one value of a key
            *tol*: {``1e-12``} | :class:`float` >= 0
                Tolerance cutoff
        :Outputs:
            *db.bkpts*: :class:`dict`
                Dictionary of unique lookup values
            *db.bkpts[col]*: :class:`list`\ [:class:`np.ndarray`]
                Unique values of *db[col]* at each value of *scol*
        :Versions:
            * 2018-06-29 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Ported to :mod:`rdbnull`
        """
        # Check inputs
        if not isinstance(cols, list):
            raise TypeError("Columns input must be a list")
        elif not isinstance(scol, typeutils.strlike):
            raise TypeError("Schedule key must be a string")
        # Get break points
        bkpts = self.__dict__.get("bkpts")
        # Check break points for *scol*
        if bkpts is None:
            raise AttributeError("No 'bkpts' attribute; call get_bkpts()")
        elif scol not in bkpts:
            raise AttributeError("No bkpts for col '%s'" % col)
        # Get data type of *scol*
        dtype = self.get_col_dtype(scol)
        # Check data type
        if not (dtype.startswith("float") or dtype.startswith("int")):
            raise TypeError(
                ("Schedule col '%s' must have either " % scol) +
                ("float or int type (got %s)" % dtype))
        # Get schedule break points and nominal values
        V0 = self[scol]
        U0 = self.bkpts[scol]
        # Loop through keys
        for col in cols:
            # Check type
            if not isinstance(col, typeutils.strlike):
                raise TypeError("Column name is not a string")
            # Check if present
            if col not in self.cols:
                raise KeyError("Lookup column '%s' is not present" % col)
            # Get data type
            dtype = self.get_col_dtype(col)
            # Check it
            if not (dtype.startswith("float") or dtype.startswith("int")):
                raise TypeError(
                    ("Break point col '%s' must have either " % col) +
                    ("float or int type (got %s)" % dtype))
            # Values for *col*
            V = self[col]
            # Initialize break point array for *col*
            U = np.zeros(U0.size, dtype=dtype)
            # Check shape
            if V.size != V0.size:
                raise ValueError(
                    ("Col '%s' (%i) has different size " % (col, V.size)) +
                    ("from schedule col '%s' (%i)" % (scol, V0.size)))
            # Initialize scheduled break points
            X = []
            # Get all values for this key
            V = self[col]
            # Loop through slice values
            for (j, v0) in enumerate(U0):
                # Indices of points in this slice
                I = np.where(np.abs(V0 - v0) <= tol)[0]
                # Check for broken break point
                if I.size == 0:
                    # This shouldn't happen
                    raise ValueError("No points matching slice at " +
                        ("%s = %.2e" % (scol, v0)))
                elif I.size < nmin:
                    # No hope of break points at this *scol* value
                    X.append(np.zeros(0, dtype=V.dtype))
                    continue
                # Get unique values on the slice
                U = np.unique(V[I])
                # Initialize filtered value
                B = np.zeros_like(U)
                n = 0
                # Loop through entries
                for v in U:
                    # Check if too close to a previous entry
                    if (n > 0) and np.min(np.abs(v - B[:n])) <= tol:
                        continue
                    # Count entries
                    if np.count_nonzero(np.abs(V[I] - v) <= tol) >= nmin:
                        # Save the value
                        B[n] = v
                        # Increment count
                        n += 1
                # Save break point
                X.append(B[:n])
            # Save break points
            bkpts[col] = X

   # --- Breakpoint Lookup ---
    # Find index of break point value
    def get_bkpt_index(self, col, v, tol=1e-8):
        r"""Get interpolation weights for 1D linear interpolation

        :Call:
            >>> i0, i1, f = db.get_bkpt_index(k, v, tol=1e-8)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *col*: :class:`str`
                Individual lookup variable from *db.bkpts*
            *v*: :class:`float`
                Value at which to lookup
            *tol*: {``1e-8``} | :class:`float` >= 0
                Tolerance for left and right bounds
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is equal to upper bound
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Updated for :mod:`rdbnull`
        """
        # Extract values
        try:
            # Naive extractions
            V =self.bkpts[col]
        except AttributeError:
            # No break points
            raise AttributeError("No break point dict present")
        except KeyError:
            # Missing key
            raise KeyError(
                "Col '%s' is not present in break point dict" % col)
        # Check type
        if not isinstance(V, np.ndarray):
            # Bad break point array type
            raise TypeError(
                "Break point list for '%s' is not np.ndarray" % col)
        elif V.ndim != 1:
            # Multidmensional array
            raise ValueError(
                ("Cannot perform lookup on %iD array " % V.ndim) +
                ("for column '%s'" % col))
        elif V.size == 0:
            # No break points
            raise ValueError("Break point array for col '%s' is empty" % col)
        elif V.size == 1:
            # Only one
            raise ValueError(
                "Break point array for col '%s' has only one entry" % col)
        # Output
        return self._bkpt_index(V, v, tol=tol)

    # Function to get interpolation weights for uq
    def get_bkpt_index_schedule(self, k, v, j):
        """Get weights 1D interpolation of *k* at a slice of master key

        :Call:
            >>> i0, i1, f = db.get_bkpt_index_schedule(k, v, j)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *k*: :class:`str`
                Name of trajectory key in *FM.bkpts* for lookup
            *v*: :class:`float`
                Value at which to lookup
            *j*: :class:`int`
                Index of master "slice" key, if *k* has scheduled
                break points
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is equal to upper bound
        :Versions:
            * 2018-04-19 ``@ddalle``: First version
        """
        # Get potential values
        V = self._scheduled_bkpts(k, j)
        # Lookup within this vector
        return self._bkpt(V, v)

    # Get break point from vector
    def _bkpt_index(self, V, v, tol=1e-8, col=None):
        r"""Get interpolation weights for 1D interpolation

        This function tries to find *i0* and *i1* such that *v* is
        between *V[i0]* and *V[i1]*.  It assumes the values of *V* are
        unique and ascending (not checked).

        :Call:
            >>> i0, i1, f = db._bkpt_index(V, v, tol=1e-8)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *V*: :class:`np.ndarray`\ [:class:`float`]
                1D array of data values
            *v*: :class:`float`
                Value at which to lookup
            *tol*: {``1e-8``} | :class:`float` >= 0
                Tolerance for left and right bounds
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is equal to upper bound;
                can be outside 0-1 bound for extrapolation
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Updated for :mod:`rdbnull`
        """
        # Get length
        n = V.size
        # Get min/max
        vmin = np.min(V)
        vmax = np.max(V)
        # Check for extrapolation cases
        if v < vmin - tol*(vmax-vmin):
            # Extrapolation left
            return None, 0, (v-V[0])/(V[1]-V[0])
        elif v > vmax + tol*(vmax-vmin):
            # Extrapolation right
            return n-1, None, (v-V[-1])/(V[-1]-V[-2])
        # Otherwise, count up values below
        i0 = np.sum(V[:-1] <= v) - 1
        i1 = i0 + 1
        # Progress fraction
        f = (v - V[i0]) / (V[i1] - V[i0])
        # Output
        return i0, i1, f

    # Get a break point, with error checking
    def get_bkpt(self, col, *I):
        r"""Extract a breakpoint by index, with error checking

        :Call:
            >>> v = db.get_bkpt(col, *I)
            >>> v = db.get_bkpt(col)
            >>> v = db.get_bkpt(col, i)
            >>> v = db.get_bkpt(col, i, j)
            >>> v = db.get_bkpt(col, i, j, ...)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *col*: :class:`str`
                Individual lookup variable from *db.bkpts*
            *I*: :class:`tuple`
                Tuple of lookup indices
            *i*: :class:`int`
                (Optional) first break point list index
            *j*: :class:`int`
                (Optional) second break point list index
        :Outputs:
            *v*: :class:`float` | :class:`np.ndarray`
                Break point or array of break points
        :Versions:
            * 2018-12-31 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Updated for :mod:`rdbnull`
        """
        # Get the break points
        try:
            v = self.bkpts[col]
        except AttributeError:
            # No radial basis functions at all
            raise AttributeError("No break points found")
        except KeyError:
            # No RBF for this coefficient
            raise KeyError("No break points for col '%s'" % col)
        # Number of indices given
        nd = len(I)
        # Loop through indices
        for n, i in enumerate(I):
            # Try to extract
            try:
                # Get the *ith* list entry
                v = v[i]
            except (IndexError, TypeError):
                # Reached scalar too soon
                raise TypeError(
                    ("Breakpoints for '%s':\n" % k) +
                    ("Expecting %i-dimensional " % nd) +
                    ("array but found %i-dim" % n))
        # Output
        return v

    # Get all break points
    def _scheduled_bkpts(self, col, j):
        """Get list of break points for key *col* at schedule *j*

        :Call:
            >>> i0, i1, f = db._scheduled_bkpts(col, j)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *col*: :class:`str`
                Individual lookup variable from *db.bkpts*
            *j*: :class:`int`
                Index of master "slice" key, if *col* has scheduled
                break points
        :Outputs:
            *i0*: ``None`` | :class:`int`
                Lower bound index, if ``None``, extrapolation below
            *i1*: ``None`` | :class:`int`
                Upper bound index, if ``None``, extrapolation above
            *f*: 0 <= :class:`float` <= 1
                Lookup fraction, ``1.0`` if *v* is equal to upper bound
        :Versions:
            * 2018-12-30 ``@ddalle``: First version
            * 2019-12-16 ``@ddalle``: Updated for :mod:`rdbnull`
        """
        # Get the break points
        try:
            V = self.bkpts[col]
        except AttributeError:
            # No radial basis functions at all
            raise AttributeError("No break points found")
        except KeyError:
            # No RBF for this coefficient
            raise KeyError("No break points for col '%s'" % col)
        # Get length
        n = len(V)
        # Size check
        if n == 0:
            raise ValueError("Empty break point array for col '%s'" % col)
        # Check first key for array
        if isinstance(V[0], (np.ndarray, list)):
            # Get break points for this slice
            V = V[j]
            # Reset size
            n = V.size
            # Recheck size
            if n == 0:
                raise ValueError(
                    ("Empty break point array for col '%s' " % col) +
                    ("at slice %i" % j))
        # Output
        return V

   # --- Full Factorial ---
    # Fill out a slice matrix
    def get_fullfactorial(self, scol=None, cols=None):
        r"""Create full-factorial matrix of values in break points
        
        This allows some of the break points cols to be scheduled, i.e.
        there are different matrices of *cols* for each separate value
        of *scol*.
        
        :Call:
            >>> X, slices = db.get_fullfactorial(scol=None, cols=None)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *scol*: {``None``} | :class:`str` | :class:`list`
                Optional name of slicing col(s)
            *cols*: {``None``} | :class:`list`\ [:class:`str`]
                List of (ordered) input keys, default is from *DBc.bkpts*
        :Outputs:
            *X*: :class:`dict`
                Dictionary of full-factorial matrix
            *slices*: :class:`dict` (:class:`ndarray`)
                Array of slice values for each col in *scol*
        :Versions:
            * 2018-11-16 ``@ddalle``: First version
        """
       # --- Slice col Checks ---
        # Check for list or string
        if isinstance(scol, list):
            # Get additional slice keys
            subcols = subcol[1:]
            # Single slice key
            maincol = subcol[0]
        elif scol is None:
            # No slices at all
            subcols = []
            maincol = None
        elif typeutils.isstr(scol):
            # No additional slice keys
            subcols = []
            maincol = scol
            # List of slice keys
            scol = [scol]
        else:
            raise TypeError("Slicing column must be 'list' or 'str'")
       # --- col Checks ---
        # Get break points
        bkpts = self.__dict__.get("bkpts", {})
        # Default col list
        if cols is None:
            # Default list
            cols = []
            # Loop through breakpoints
            for (col, V) in bkpts.items():
                # Check if *V* is an array
                if not isinstance(V, np.ndarray):
                    # Non-array
                    continue
                elif V.size == 0:
                    # Empty break points
                    continue
                elif V.ndim != 1:
                    # What? ND array
                    continue
                elif not isinstance(V[0], float):
                    # Not a simple number
                    continue
                # If reaching this point, usable column
                cols.append(col)
        else:
            # Loop through breakpoints
            for col in cols:
                # Get break points
                V = bkpts.get(col)
                # Check if *V* is an array
                if V is None:
                    raise KeyError("No breakpoints for col '%s'" % col)
                elif not isinstance(V, np.ndarray):
                    # Non-array
                    raise TypeError(
                        "Breakpoints for col '%s' is not array" % col)
                elif V.size == 0:
                    # Empty break points
                    raise IndexError(
                        "Breakpoints for col '%s' is empty" % col)
                elif V.ndim != 1:
                    # What? ND array
                    raise IndexError(
                        "Breakpoints for col '%s' is not 1D" % col)
                elif not isinstance(V[0], (float, int, complex)):
                    # Not a simple number
                    raise TypeError(
                        "Non-numeric breakpoitns for col '%s'" % col)
            # Make a copy
            cols = list(cols)
        # Eliminate *skey* if in key list
        if maincol in cols:
            cols.remove(maincol)
        # Number of columns
        ncol = len(cols)
       # --- Slice Init ---
        # Initialize slice dictionary
        slices = {}
        # Initialize main slice values
        if maincol is not None:
            slices[maincol] = np.zeros(0)
        # Loop through slice keys
        for col in subcols:
            # Initialize slice
            slices[col] = np.zeros(0)
        # Number of slice keys
        if scol is None:
            # No slices
            nscol = 0
        else:
            # Get length
            nscol = len(scol)
       # --- Matrix Init ---
        # Initialize dictionary of full-factorial matrix
        X = {}
        # Set values
        for col in cols:
            X[col] = np.zeros(0)
        # Slice check
        if maincol is None:
            # No values to check
            M = np.zeros(1)
        else:
            # Get breakpoints for specified value
            M = bkpts[maincol]
            # Also keep track of slice key values
            X[maincol] = np.zeros(0)
       # --- Main Slice Loop ---
        # Loop through slice values
        for (im, m) in enumerate(M):
            # Initialize matrix for this slice
            Xm = {}
            # Initialize slice values for this slice
            Xs = {}
            if maincol:
                Xs[maincol] = np.array([m])
            # Copy values
            for col in cols:
                # Get values
                Vm = bkpts[col]
                # Get first entry for type checks
                v0 = bkpts[col][0]
                # Check if it's a scheduled key; will be a list
                if isinstance(v0, list):
                    # Get break points for this slice key value
                    Vm = Vm[im]
                # Save the values
                Xm[col] = Vm
                # Save slice if appropriate
                if col in subcols:
                    Xs[col] = Vm
            # Loop through break point keys to create full-factorial inputs
            for i in range(1, ncol):
                # Name of first key
                col1 = cols[i]
                # Loop through keys 0 to *i*-1
                for j in range(i):
                    # Name of second key
                    col2 = cols[j]
                    # Create N+1 dimensional interpolation
                    x1, x2 = np.meshgrid(Xm[col1], Xm[col2])
                    # Flatten
                    Xm[col2] = x2.flatten()
                    # Save first key if *j* ix 0
                    if j == i-1:
                        Xm[col1] = x1.flatten()
            # Loop through slice keys to create full-factorial inputs
            for i in range(1, nscol):
                # Name of first key
                col1 = scol[i]
                # Loop through keys 0 to *i*-1
                for j in range(i):
                    # Name of second key
                    col2 = scol[j]
                    # Create N+1 dimensional interpolation
                    x1, x2 = np.meshgrid(Xs[col1], Xs[col2])
                    # Flatten
                    Xs[col2] = x2.flatten()
                    # Save first key if *j* ix 0
                    if j == i-1:
                        Xs[col1] = x1.flatten()
            # Save values
            for col in cols:
                X[col] = np.hstack((X[col], Xm[col]))
            # Process slices
            if maincol is not None:
                # Append to *scol* matrix
                X[maincol] = np.hstack(
                    (X[maincol], m*np.ones_like(Xm[col])))
                # Save slice full-factorial matrix
                for col in scol:
                    slices[col] = np.hstack((slices[col], Xs[col]))
        # Output
        return X, slices
  # >

  # ====================
  # RBF Tools
  # ====================
  # <
   # --- RBF construction ---
    # Regularization
    def create_global_rbfs(self, cols, args, I=None, **kw):
        r"""Create global radial basis functions for one or more columns

        :Call:
            >>> db.create_global_rbfs(cols, args, I=None)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *cols*: :class:`list`\ [:class:`str`]
                List of columns to create RBFs for
            *args*: :class:`list`\ [:class:`str`]
                List of (ordered) input keys, default is from *db.bkpts*
            *I*: {``None``} | :class:`np.ndarray`
                Indices of cases to include in RBF (default is all)
            *function*: {``"cubic"``} | :class:`str`
                Radial basis function type
            *smooth*: {``0.0``} | :class:`float` >= 0
                Smoothing factor, ``0.0`` for exact interpolation
        :Effects:
            *db.rbf[col]*: :class:`scipy.interpolate.rbf.Rbf`
                Radial basis function for each *col* in *cols*
        :Versions:
            * 2019-01-01 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check for module
        if scirbf is None:
            raise ImportError("No scipy.interpolate.rbf module")
        # Create *rbf* attribute if needed
        rbf = self.__dict__.setdefault("rbf", {})
        # RBF options
        func   = kw.get("function", "cubic")
        smooth = kw.get("smooth", 0.0)
        # Default indices
        if I is None:
            # Size of database
            n = len(self[args[0]])
            # All the indices
            I = np.arange(n)
        # Create tuple of input points
        V = tuple(self[k][I] for k in args)
        # Loop through coefficients
        for col in cols:
            # Eval arguments for status update
            txt = str(tuple(args)).replace(" ", "")
            # Trim if too long
            if len(txt) > 50:
                txt = txt[:45] + "...)"
            # Status update line
            txt = "Creating RBF for %s%s" % (col, txt)
            sys.stdout.write("%-72s\r" % txt)
            sys.stdout.flush()
            # Append reference values to input tuple
            Z = V + (self[col][I],)
            # Create a single RBF
            f = scirbf.Rbf(*Z, function=func, smooth=smooth)
            # Save it
            rbf[col] = f
        # Clean up the prompt
        sys.stdout.write("%72s\r" % "")
        sys.stdout.flush()

    # Regularization
    def create_slice_rbfs(self, cols, args, I=None, **kw):
        r"""Create radial basis functions for each slice of *args[0]*

        The first entry in *args* is interpreted as a "slice" key; RBFs
        will be constructed at constant values of *args[0]*.

        :Call:
            >>> db.create_slice_rbfs(coeffs, args, I=None)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *cols*: :class:`list`\ [:class:`str`]
                List of columns to create RBFs for
            *args*: :class:`list`\ [:class:`str`]
                List of (ordered) input keys, default is from *db.bkpts*
            *I*: {``None``} | :class:`np.ndarray`
                Indices of cases to include in RBF (default is all)
            *function*: {``"cubic"``} | :class:`str`
                Radial basis function type
            *smooth*: {``0.0``} | :class:`float` >= 0
                Smoothing factor, ``0.0`` for exact interpolation
        :Effects:
            *db.rbf[col]*: :class:`list`\ [:class:`scirbf.Rbf`]
                List of RBFs at each slice for each *col* in *cols*
        :Versions:
            * 2019-01-01 ``@ddalle``: First version
            * 2019-12-17 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Check for module
        if scirbf is None:
            raise ImportError("No scipy.interpolate.rbf module")
        # Create *rbf* attribute if needed
        self.__dict__.setdefault("rbf", {})
        # RBF options
        func  = kw.get("function", "cubic")
        smooth = kw.get("smooth", 0.0)
        # Name of slice key
        skey = args[0]
        # Tolerances
        tols = kw.get("tols", {})
        # Tolerance for slice key
        tol = kw.get("tol", tols.get(skey, 1e-6))
        # Default indices
        if I is None:
            # Size of database
            n = len(self[skey])
            # All the indices
            I = np.arange(n)
        # Get break points for slice key
        B = self.bkpts[skey]
        # Number of slices
        nslice = len(B)
        # Initialize the RBFs
        for col in cols:
            self.rbf[col] = []
        # Loop through slices
        for b in B:
            # Get slice constraints
            qj = np.abs(self[skey][I] - b) <= tol
            # Select slice and add to list
            J = I[qj]
            # Create tuple of input points
            V = tuple(self[k][J] for k in args[1:])
            # Create a string for slice coordinate and remaining args
            arg_string_list = ["%s=%g" % (skey,b)]
            arg_string_list += [str(k) for k in args[1:]]
            # Joint list with commas
            arg_string = "(" + (",".join(arg_string_list)) + ")"
            # Loop through coefficients
            for coeff in coeffs:
                # Status update
                txt = "Creating RBF for %s%s" % (col, arg_string)
                sys.stdout.write("%-72s\r" % txt[:72])
                sys.stdout.flush()
                # Append reference values to input tuple
                Z = V + (self[coeff][J],)
                # Create a single RBF
                f = scirbf.Rbf(*Z, function=func, smooth=smooth)
                # Save it
                self.rbf[col].append(f)
        # Clean up the prompt
        sys.stdout.write("%72s\r" % "")
        sys.stdout.flush()
  # >

  # ==================
  # Data
  # ==================
  # <
   # --- Save/Add ---
   # --- Copy/Link ---
    # Link data
    def link_data(self, dbsrc, cols=None):
        r"""Save a column to database
        
        :Call:
            >>> db.link_data(dbsrc, cols=None)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *cols*: {``None``} | :class:`list`\ [:class:`str`]
                List of columns to link (or *dbsrc.cols*)
        :Effects:
            *db.cols*: :class:`list`\ [:class:`str`]
                Appends each *col* in *cols* where not present
            *db[col]*: *dbsrc[col]*
                Reference to *dbsrc* data for each *col*
        :Versions:
            * 2019-12-06 ``@ddalle``: First version
        """
        # Check type of data set
        if not isinstance(dbsrc, dict):
            # Source must be a dictionary
            raise TypeError("Source data must be a dict")
        # Default columns
        if cols is None:
            # Check for explicit list
            if "cols" in dbsrc.__dict__:
                # Explicit list
                cols = dbsrc.cols
            else:
                # Get all keys
                cols = list(dbsrc.keys())
        # Check type of *cols*
        if not isinstance(cols, list):
            # Column list must be a list
            raise TypeError(
                "Column list must be a list, got '%s'"
                % cols.__class__.__name__)
        # Loop through columns
        for col in cols:
            # Check type
            if not typeutils.isstr(col):
                raise TypeError("Column names must be strings")
            # Check if data is present
            if col not in dbsrc:
                raise KeyError("No column '%s'" % col)
            # Save the data
            self.save_col(col, dbsrc[col])

   # --- Access ---
    # Look up a generic key
    def get_col(self, k=None, defnames=[], **kw):
        """Process a key name, using an ordered list of defaults

        :Call:
            >>> col = db.get_key(k=None, defnames=[], **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data container
            *k*: {``None``} | :class:`str`
                User-specified col name; if ``None``, automatic value
            *defnamess*: :class:`list`
                List of applicable default names for the col
            *title*: {``"lookup"``} | :class:`str`
                Key title to use in any error messages
            *error*: {``True``} | ``False``
                Raise an exception if no col is found
        :Outputs:
            *col*: *k* | *defnamess[0]* | *defnamess[1]* | ... 
                Name of lookup key in *db.cols*
        :Versions:
            * 2018-06-22 ``@ddalle``: First version
        """
        # Get default
        if (k is not None):
            # Check if it's present
            if k not in self.cols:
                # Error option
                if kw.get("error", True):
                    # Get title for error message, e.g. "angle of attack"
                    ttl = kw.get("title", "lookup")
                    # Error message
                    raise KeyError("No %s key found" % ttl)
                else:
                    # If no error, return ``None``
                    return defnames[0]
            # Otherwise, done
            return k
        # Check list
        if not isinstance(defnames, list):
            raise TypeError("Default col names must be list") 
        # Loop through defaults
        for col in defnames:
            # Check if it's present
            if col in self.cols:
                return col
        # If this point is reached, no default found
        if not kw.get("error", True):
            # No error, as specified by user
            return defnames[0]
        # Get title for error message, e.g. "angle of attack"
        ttl = kw.get("title", "lookup")
        # Error message
        raise KeyError("No %s key found" % ttl)

   # --- Independent Key Values ---
    # Get the value of an independent variable if possible
    def get_xvals(self, col, I=None, **kw):
        r"""Get values of specified column, which may need conversion

        This function can be used to calculate independent variables
        (*xvars*) that are derived from extant data columns.  For
        example if columns *alpha* and *beta* (for angle of attack and
        angle of sideslip, respectively) are present and the user wants
        to get the total angle of attack *aoap*, this function will
        attempt to use ``db.eval_arg_converters["aoap"]`` to convert
        available *alpha* and *beta* data.

        :Call:
            >>> V = db.get_xvals(col, I=None, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to access
            *I*: ``None`` | :class:`np.ndarray` | :class:`int`
                Subset indices or single index
            *kw*: :class:`dict`
                Dictionary of values in place of *db* (e.g. *kw[col]*
                instead of *db[col]*)
            *IndexKW*: ``True`` | {``False``}
                Option to use *kw[col][I]* instead of just *kw[col]*
        :Outputs:
            *V*: :class:`np.ndarray` | :class:`float`
                Array of values or scalar for column *col*
        :Versions:
            * 2019-03-12 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit.db.db1`
        """
        # Option for processing keywrods
        qkw = kw.pop("IndexKW", False)
        # Check for direct membership
        if col in kw:
            # Get values from inputs
            V = kw[col]
            # Checking for quick output
            if not qkw:
                return V
        elif col in self:
            # Get all values from column
            V = self[col]
        else:
            # Get converter
            f = self.get_eval_arg_converter(col)
            # Check for converter
            if f is None:
                raise ValueError("No converter for col '%s'" % col)
            elif not callable(f):
                raise TypeError("Converter for col '%s' not callable" % col)
            # Create a dictionary of values
            X = dict(self, **kw)
            # Attempt to convert
            try:
                # Use entire dictionary as inputs
                V = f(**X)
            except Exception:
                raise ValueError("Conversion function for '%s' failed" % col)
        # Check for indexing
        if I is None:
            # No subset
            return V
        elif typeutils.isarray(V):
            # Apply subset
            return V[I]
        else:
            # Not subsettable
            return V

    # Get independent variable from eval inputs
    def get_xvals_eval(self, k, *a, **kw):
        r"""Return values of a column from inputs to :func:`__call__`

        For example, this can be used to derive the total angle of
        attack from inputs to an evaluation call to *CN* when it is a
        function of *mach*, *alpha*, and *beta*.  This method attempts
        to use :func:`db.eval_arg_converters`.

        :Call:
            >>> V = db.get_xvals_eval(k, *a, **kw)
            >>> V = db.get_xvals_eval(k, coeff, x1, x2, ..., k3=x3)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *k*: :class:`str`
                Name of key to calculate
            *col*: :class:`str`
                Name of output data column
            *x1*: :class:`float` | :class:`np.ndarray`
                Value(s) of first argument
            *x2*: :class:`float` | :class:`np.ndarray`
                Value(s) of second argument, if applicable
            *k3*: :class:`str`
                Name of third argument or optional variant
            *x3*: :class:`float` | :class:`np.ndarray`
                Value(s) of argument *k3*, if applicable
        :Outputs:
            *V*: :class:`np.ndarray`
                Values of key *k* from conditions in *a* and *kw*
        :Versions:
            * 2019-03-12 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
        # Process coefficient
        X = self.get_arg_value_dict(*a, **kw)
        # Check if key is present
        if k in X:
            # Return values
            return X[k]
        else:
            # Get dictionary of converters
            converters = getattr(self, "eval_arg_converters", {})
            # Check for membership
            if k not in converters:
                raise ValueError(
                    "Could not interpret xvar '%s'" % k)
            # Get converter
            f = converters[k]
            # Check class
            if not callable(f):
                raise TypeError("Converter for '%s' is not callable" % k)
            # Attempt to convert
            try:
                # Use entire dictionary as inputs
                V = f(**X)
            except Exception:
                raise ValueError("Conversion function for '%s' failed" % k)
            # Output
            return V

   # --- Dependent Key Values ---
    # Get exact values
    def get_yvals_exact(self, col, I=None, **kw):
        r"""Get exact values of a data column

        :Call:
            >>> V = db.get_yvals_exact(col, I=None, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to access
            *I*: {``None``} | :class:`np.ndarray`\ [:class:`int`]
                Database indices
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit`
        """
        # Check for direct membership
        if col in self:
            # Get all values from column
            V = self[col]
            # Check for indexing
            if I is None:
                # No subset
                return V
            else:
                # Apply subset
                return V[I]
        else:
            # Get evaluation type
            meth = self.get_eval_method(col)
            # Only allow "function" type
            if meth != "function":
                raise ValueError(
                    ("Cannot evaluate exact values for '%s', " % col) +
                    ("which has method '%s'" % meth))
            # Get args
            args = self.get_eval_args(col)
            # Create inputs
            a = tuple([self.get_xvals(k, I, **kw) for k in args])
            # Evaluate
            V = self.__call__(col, *a)
            # Output
            return V

   # --- Search ---
    # Find matches
    def find(self, args, *a, **kw):
        r"""Find cases that match a condition [within a tolerance]

        :Call:
            >>> I, J = db.find(args, *a, **kw)
            >>> Imap, J = db.find(args, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *args*: :class:`list`\ [:class:`str`]
                List of columns names to match
            *a*: :class:`tuple`\ [:class:`float`]
                Values of the arguments
            *mask*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *db* to consider
            *tol*: {``1e-4``} | :class:`float` >= 0
                Default tolerance for all *args*
            *tols*: {``{}``} | :class:`dict`\ [:class:`float` >= 0]
                Dictionary of tolerances specific to arguments
            *once*: ``True`` | {``False``}
                Option to find max of one *db* index per test point
            *mapped*: ``True`` | {``False``}
                Option to switch output to *Imap* (overrides *once*)
            *kw*: :class:`dict`
                Additional values to use during evaluation
        :Outputs:
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of cases in *db* that match conditions
            *J*: :class:`np.ndarray`\ [:class:`int`]
                Indices of (*a*, *kw*) that have a match in *db*
            *Imap*: :class:`list`\ [:class:`np.ndarray`]
                List of *db* indices for each test point in *J*
        :Versions:
            * 2019-03-11 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :func:`DBCoeff.FindMatches`
            * 2020-02-20 ``@ddalle``: Added *mask*, *once* kwargs
        """
       # --- Input Checks ---
        # Find a valid argument
        for arg in args:
            # Attempt to either access or convert it
            V = self.get_all_values(arg)
            # Check if it was processed
            if V is not None:
                # Found at least one valid argument
                break
        else:
            # Loop completed; nothing found
            raise ValueError(
                "Cannot find matches for argument list %s" % args)
        # Mask
        mask = kw.pop("mask", None)
        # Overall tolerance default
        tol = kw.pop("tol", 1e-4)
        # Specific tolerances
        tols = kw.pop("tols", {})
        # Option for unique matches
        once = kw.pop("once", False)
        # Option for mapped matches
        mapped = kw.pop("mapped", False)
        # Number of values
        n0 = V.size
       # --- Mask Prep ---
        # Check mask type
        if mask is None:
            # Ok
            pass
        elif not isinstance(mask, np.ndarray):
            # Bad type
            raise TypeError(
                "Index mask must be 'ndarray', got '%s'" % type(mask).__name__)
        elif mask.size == 0:
            # Empty mask
            raise IndexError("Index mask cannot be empty")
        elif mask.ndim != 1:
            # Dimension error
            raise IndexError("Index mask must be one-dimensional array")
        # Filter mask
        if mask is None:
            # Create indices
            mask_index = np.arange(n0)
        elif mask.dtype.name == "bool":
            # Get indices
            mask_index = np.where(mask)[0]
            # Check consistency
            if mask.size != n0:
                # Size mismatch
                raise IndexError(
                    ("Index mask has size %i; " % mask.size) +
                    ("test values size is %i" % n0))
        elif mask.dtype.name.startswith("int"):
            # Convert to indices
            mask_index = mask
            # Check values
            if np.max(mask) >= n0:
                raise IndexError(
                    "Cannot mask element %i for test values with size %i"
                    % (np.max(mask), n0))
        else:
            # Bad type
            raise TypeError("Mask must have dtype 'bool' or 'int'")
        # Update test size
        n = mask_index.size
       # --- Argument values ---
        # Initialize lookup point
        x = []
        # Loop through arguments
        for i, col in enumerate(args):
            # Get value
            xi = self.get_arg_value(i, col, *a, **kw)
            # Save it
            x.append(np.asarray(xi))
        # Normalize arguments
        X, dims = self.normalize_args(x, True)
        # Number of test points
        nx = np.prod(dims)
       # --- Checks ---
        # Initialize tests for database indices (set to ``False``)
        MI = np.arange(n) < 0
        # Initialize tests for input data indices (set to ``False``)
        MJ = np.arange(nx) < 0
        # Initialize maps if needed
        if mapped:
            Imap = []
        # Loop through entries
        for i in range(nx):
            # Initialize tests for this point (set to ``True``)
            Mi = np.arange(n) > -1
            # Loop through arguments
            for j, k in enumerate(args):
                # Get array of database values
                Xk = self.get_all_values(k)
                # Check if present
                if (k is None) or (Xk is None):
                    continue
                # Check size
                if len(Xk) != n0:
                    raise ValueError(
                        ("Parameter '%s' has size %i, " % (k, len(Xk))) +
                        ("expecting %i" % n))
                # Apply mask
                if mask is not None:
                    Xk = Xk[mask]
                # Get input test value
                xi = X[j][i]
                # Get tolerance for this key
                xtol = tols.get(k, tol)
                # Check tolerance
                Mi = np.logical_and(Mi, np.abs(Xk-xi) <= xtol)
            # Check for any matches of this test point
            found = np.any(Mi)
            # Got to next test point if no match
            if not found:
                # Save status
                Mj[i] = found
                continue
            # Check reporting method
            if mapped:
                # Save test-point status (no uniqueness check)
                MJ[i] = found
                # Find matches
                I = np.where(Mi)[0]
                # Invert mask if needed
                if mask is not None:
                    I = mask_index[I]
                # Append to map
                Imap.append(I)
            elif once:
                # Check for uniqueness
                M2 = np.logical_and(np.logical_not(MI), Mi)
                # Check that
                found = np.any(M2)
                # Save status
                MJ[i] = found
                # Exit if not found (match but previously used)
                if not found:
                    continue
                # Select first not-previously-used match
                j2 = np.where(M2)[0][0]
                # Save it
                MI[j2] = True
            else:
                # Save test-point status (no uniqueness check)
                MJ[i] = found
                # Combine point constraints (*Mi* multiple matches)
                MI = np.logical_or(MI, Mi)
        # Convert test point status to indices
        J = np.where(MJ)[0]
        # Convert database point mask to indices
        if mapped:
            # Output map and test point index array
            return Imap, J
        else:
            # Convert masks to indices
            I = np.where(MI)[0]
            # Invert mask if needed
            if mask is not None:
                I = mask_index[I]
            # Return combined set of matches
            return I, J

    # Find matches from a target
    def find_pairwise(self, dbt, maskt=None, cols=None, **kw):
        r"""Find cases with matching values of specified list of cols

        :Call:
            >>> I, J = db.find_pairwise(dbt, maskt, cols=None, **kw)
            >>> Imap, J = db.find_pairwise(dbt, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data kit with response surfaces
            *dbt*: :class:`dict` | :class:`cape.attdb.rdb.DataKit`
                Target data set
            *maskt*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *dbt* to consider
            *mask*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *db* to consider
            *cols*: {``None``} | :class:`np.ndarray`\ [:class:`int`]
                List of cols to compare (default all *db* float cols)
            *tol*: {``1e-4``} | :class:`float` >= 0
                Default tolerance for all *args*
            *tols*: {``{}``} | :class:`dict`\ [:class:`float` >= 0]
                Dictionary of tolerances specific to arguments
            *once*: ``True`` | {``False``}
                Option to find max of one *db* index per test point
            *mapped*: ``True`` | {``False``}
                Option to switch output to *Imap* (overrides *once*)
            *kw*: :class:`dict`
                Additional values to use during evaluation
        :Outputs:
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of cases in *db* that have a match in *dbt*
            *J*: :class:`np.ndarray`\ [:class:`int`]
                Indices of cases in *dbt* that have a match in *db*
            *Imap*: :class:`list`\ [:class:`np.ndarray`]
                List of *db* indices for each test point in *J*
        :Versions:
            * 2020-02-20 ``@ddalle``: First version
        """
        # Check types
        if not isinstance(dbt, dict):
            raise TypeError("Target database is not a DataKit")
        # Default columns
        if cols is None:
            # Take all columns with a "float" type
            cols = [col for col in self.cols
                if self.get_col_dtype(col).startswith("float")
            ]
        # Check *cols* type
        if not isinstance(cols, list):
            raise TypeError(
                "Column list must be 'list', got '%s'" % type(cols).__name__)
        # Check for nontrivial cols
        if len(cols) == 0:
            raise ValueError("Empty column list")
        # Check mask type
        if maskt is None:
            # Ok
            pass
        elif not isinstance(maskt, np.ndarray):
            # Bad type
            raise TypeError(
                "Target mask must be 'ndarray', got '%s'"
                % type(maskt).__name__)
        elif maskt.size == 0:
            # Empty mask
            raise IndexError("Target index mask cannot be empty")
        elif maskt.ndim != 1:
            # Dimension error
            raise IndexError("Target index mask must be one-dimensional array")
        # Filter mask
        if maskt is None:
            # No inversion
            pass
        elif maskt.dtype.name == "bool":
            # Get indices
            maskt_index = np.where(maskt)[0]
        elif maskt.dtype.name.startswith("int"):
            # Convert to indices
            maskt_index = maskt
        else:
            # Bad type
            raise TypeError("Target mask must have dtype 'bool' or 'int'")
        # Create list or args and their values to :func:`find`
        args = []
        argvals = []
        # Check mode for data-kit (versus generic dict) target
        isdatakit = isinstance(dbt, DataKit)
        # Loop through columns
        for col in cols:
            # Check type
            if not typeutils.isstr(col):
                raise TypeError(
                    "Col name must be 'str', got '%s'" % type(col).__name__)
            # Get *dbt* values
            if isdatakit:
                # Get value; use converters if necessary
                V = dbt.get_all_values(col)
            else:
                # Get value from a dict
                V = dbt.get(col)
            # Ensure array
            if V is None:
                # No match
                continue
            elif isinstance(V, (list, np.ndarray)):
                # Check size
                if len(V) == 0:
                    continue
                # Check data type
                if typeutils.isstr(V[0]):
                    # No strings
                    continue
                # If list, convert
                if isinstance(V, list):
                    # Force array
                    V = np.asarray(V)
                # Apply mask
                if maskt is not None:
                    V = V[maskt]
            elif not isinstance(V, (int, float, complex)):
                # Non-numeric type
                continue
            # Save to arg list
            args.append(col)
            # Save value
            argvals.append(V)
        # Find matches in *db* based on args
        I, J = self.find(args, *argvals, **kw)
        # Check for mask
        if maskt is not None:
            # Invert mask
            J = maskt_index[J]
        # Output
        return I, J

   # --- Statistics ---
    # Get coverage
    def est_cov_interval(self, dbt, col, mask=None, cov=0.95, **kw):
        r"""Calculate Student's t-distribution confidence region
        
        If the nominal application of the Student's t-distribution fails
        to cover a high enough fraction of the data, the bounds are
        extended until the data is covered.
        
        :Call:
            >>> a, b = db.est_cov_interval(dbt, col, mask, cov, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data kit with response surfaces
            *dbt*: :class:`dict` | :class:`cape.attdb.rdb.DataKit`
                Target data set
            *mask*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *db* to consider
            *maskt*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *dbt* to consider
            *cov*: {``0.95``} | 0 < :class:`float` < 1
                Coverage percentage
            *cdf*, *CoverageCDF*: {*cov*} | 0 < :class:`float` < 1
                CDF if no extra coverage needed
            *osig*, *OutlierSigma*: {``1.5*ksig``} | :class:`float`
                Multiple of standard deviation to identify outliers;
                default is 150% of the nominal coverage calculated using
                t-distribution
            *searchcols*: {``None``} | :class:`list`\ [:class:`str`]
                List of cols to use for finding matches; default is all
                :class:`float` cols of *db*
            *tol*: {``1e-8``} | :class:`float`
                Default tolerance for matching conditions
            *tols*: :class:`dict`\ [:class:`float`]
                Dict of tolerances for specific columns during search
        :Outputs:
            *a*: :class:`float`
                Lower bound of coverage interval
            *b*: :class:`float`
                Upper bound of coverage intervalregion
        :Versins:
            * 2018-09-28 ``@ddalle``: First version
            * 2020-02-21 ``@ddalle``: Rewritten from :mod:`attdb.fm`
        """
        # Process search kwargs
        kw_find = {
            "mask": "mask",
            "maskt": kw.pop("maskt", None),
            "once": True,
            "cols": kw.pop("searchcols", None),
        }
        # Find indices of matches
        I, J = self.find_pairwise(dbt, **kw_find)
        # Check for empty
        if I.size == 0:
            raise ValueError("No matches between databases")
        # Get values from this database
        V1 = self.get_values(col, I)
        # Get values from target database
        if isinstance(dbt, DataKit):
            # Get values with converters
            V2 = dbt.get_values(col, J)
        else:
            # Get values from dict
            V2 = dbt[col][J]
        # Deltas (signed)
        dV = V2 - V1
        # Calculate interval
        return statutils.get_cov_interval(dV, cov, **kw)

    # Get coverage
    def est_range(self, dbt, col, mask=None, cov=0.95, **kw):
        r"""Calculate Student's t-distribution confidence range
        
        If the nominal application of the Student's t-distribution fails
        to cover a high enough fraction of the data, the bounds are
        extended until the data is covered.
        
        :Call:
            >>> r = db.est_range(dbt, col, mask, cov, **kw)
        :Inputs:
            *db*: :class:`cape.attdb.rdb.DataKit`
                Data kit with response surfaces
            *dbt*: :class:`dict` | :class:`cape.attdb.rdb.DataKit`
                Target data set
            *mask*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *db* to consider
            *maskt*: :class:`np.ndarray`\ [:class:`bool` | :class:`int`]
                Subset of *dbt* to consider
            *cov*: {``0.95``} | 0 < :class:`float` < 1
                Coverage percentage
            *cdf*, *CoverageCDF*: {*cov*} | 0 < :class:`float` < 1
                CDF if no extra coverage needed
            *osig*, *OutlierSigma*: {``1.5*ksig``} | :class:`float`
                Multiple of standard deviation to identify outliers;
                default is 150% of the nominal coverage calculated using
                t-distribution
            *searchcols*: {``None``} | :class:`list`\ [:class:`str`]
                List of cols to use for finding matches; default is all
                :class:`float` cols of *db*
            *tol*: {``1e-8``} | :class:`float`
                Default tolerance for matching conditions
            *tols*: :class:`dict`\ [:class:`float`]
                Dict of tolerances for specific columns during search
        :Outputs:
            *r*: :class:`float`
                Half-width of coverage range
        :Versins:
            * 2018-09-28 ``@ddalle``: First version
            * 2020-02-21 ``@ddalle``: Rewritten from :mod:`attdb.fm`
        """
        # Process search kwargs
        kw_find = {
            "mask": "mask",
            "maskt": kw.pop("maskt", None),
            "once": True,
            "cols": kw.pop("searchcols", None),
        }
        # Find indices of matches
        I, J = self.find_pairwise(dbt, **kw_find)
        # Check for empty
        if I.size == 0:
            raise ValueError("No matches between databases")
        # Get values from this database
        V1 = self.get_values(col, I)
        # Get values from target database
        if isinstance(dbt, DataKit):
            # Get values with converters
            V2 = dbt.get_values(col, J)
        else:
            # Get values from dict
            V2 = dbt[col][J]
        # Deltas (unsigned)
        R = np.abs(V2 - V1)
        # Calculate interval
        return statutils.get_range(R, cov, **kw)
  # >

  # ===================
  # Plot
  # ===================
  # <
   # --- Preprocessors ---
    # Process arguments to PlotCoeff()
    def _process_plot_args1(self, *a, **kw):
        r"""Process arguments to :func:`plot` and other plot methods

        :Call:
            >>> col, I, J, a, kw = db._process_plot_args1(*a, **kw)
            >>> col, I, J, a, kw = db._process_plot_args1(I, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *a*: :class:`tuple`\ [:class:`np.ndarray` | :class:`float`]
                Array of values for arguments to :func:`db.__call__`
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of exact entries to plot
            *kw*: :class:`dict`
                Keyword arguments to plot function and evaluation
        :Outputs:
            *col*: :class:`str`
                Data field to evaluate
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of exact entries to plot
            *J*: :class:`np.ndarray`\ [:class:`int`]
                Indices of matches within *a*
            *a*: :class:`tuple`\ [:class:`float` | :class:`np.ndarray`]
                Values for arguments for *coeff* evaluator
            *kw*: :class:`dict`
                Processed keyword arguments with defaults applied
        :Versions:
            * 2019-03-14 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit.db.db1`
        """
       # --- Argument Types ---
        # Process coefficient name and remaining coeffs
        col, a, kw = self._prep_args_colname(*a, **kw)
        # Get list of arguments
        arg_list = self.get_eval_args(col)
        # Get key for *x* axis
        xk = kw.setdefault("xk", arg_list[0])
        # Check for indices
        if len(a) == 0:
            raise ValueError("At least 2 inputs required; received 1")
        # Process first second arg as indices
        I = np.asarray(a[0])
        # Check for integer
        if (I.ndim > 0) and isinstance(I[0], int):
            # Request for exact values
            qexact  = True
            qinterp = False
            qmark   = False
            qindex  = True
            # Get values of arg list from *DBc* and *I*
            A = []
            # Loop through *eval_args*
            for col in arg_list:
                # Get values
                A.append(self.get_xvals(col, I, **kw))
            # Convert to tuple
            a = tuple(A)
            # Plot all points
            J = np.arange(I.size)
        else:
            # No request for exat values
            qexact  = False
            qinterp = True
            qmark   = True
            qindex  = False
            # Find matches from *a to database points
            I, J = self.find(arg_list, *a, **kw)
       # --- Options: What to plot ---
        # Plot exact values, interpolated (eval), and markers of actual data
        qexact  = kw.setdefault("PlotExact",  qexact)
        qinterp = kw.setdefault("PlotInterp", qinterp and (not qexact))
        qmark   = kw.setdefault("MarkExact",  qmark and (not qexact))
        # Default UQ coefficient
        uk_def = self.get_uq_col(col)
        # Check situation
        if typeutils.isarray(uk_def):
            # Get first entry
            uk_def = uk_def[0]
        # Get UQ coefficient
        uk  = kw.get("uk",  kw.get("ucol"))
        ukM = kw.get("ukM", kw.get("ucol_minus", uk))
        ukP = kw.get("ukP", kw.get("ucol_plus",  uk))
        # Turn on *PlotUQ* if UQ key specified
        if ukM or ukP:
            kw.setdefault("ShowUncertainty", True)
        # UQ flag
        quq = kw.get("ShowUncertainty", kw.get("ShowUQ", False))
        # Set default UQ keys if needed
        if quq:
            uk  = kw.setdefault("uk",  uk_def)
            ukM = kw.setdefault("ukM", uk)
            ukP = kw.setdefault("ukP", uk)
       # --- Default Labels ---
        # Default label starter: db.name
        dlbl = self.__dict__.get("name")
        # Some fallbacks
        if dlbl is None:
            dlbl = self.__dict__.get("comp")
        if dlbl is None:
            dlbl = self.__dict__.get("Name")
        if dlbl is None:
            dlbl = col
        # Set default label
        kw.setdefault("Label", dlbl)
        # Default x-axis label is *xk*
        kw.setdefault("XLabel", xk)
        kw.setdefault("YLabel", col)
       # --- Cleanup ---
        # Output
        return col, I, J, a, kw

   # --- Base Plot Commands ---
    # Plot a sweep of one or more coefficients
    def plot_scalar(self, *a, **kw):
        r"""Plot a sweep of one data column over several cases

        This is the base method upon which scalar data book sweep plotting is built.
        Other methods may call this one with modifications to the default
        settings.  For example :func:`cape.cfdx.dataBook.DBTarget.PlotCoeff` changes
        the default *LineOptions* to show a red line instead of the standard
        black line.  All settings can still be overruled by explicit inputs to
        either this function or any of its children.

        :Call:
            >>> h = db.plot_scalar(col, *a, **kw)
            >>> h = db.plot_scalar(col, I, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with scalar output functions
            *col*: :class:`str`
                Data column (or derived column) to evaluate
            *a*: :class:`tuple`\ [:class:`np.ndarray` | :class:`float`]
                Array of values for arguments to evaluator for *col*
            *I*: :class:`np.ndarray` (:class:`int`)
                Indices of exact entries to plot
        :Keyword Arguments:
            *xcol*, *xk*: {``None``} | :class:`str`
                Key/column name for *x* axis
            *PlotExact*: ``True`` | ``False``
                Plot exact values directly from database without interpolation
                Default is ``True`` if *I* is used
            *PlotInterp*: ``True`` | ``False``
                Plot values by using :func:`DBc.__call__`
            *MarkExact*: ``True`` | ``False``
                Mark interpolated curves with markers where actual data points
                are present
        :Plot Options:
            *ShowLegend*: {``None``} | ``True`` | ``False``
                Whether or not to use a legend
            *LegendFontSize*: {``9``} | :class:`int` > 0 | :class:`float`
                Font size for use in legends
            *Grid*: {``None``} | ``True`` | ``False``
                Turn on/off major grid lines, or leave as is if ``None``
            *GridStyle*: {``{}``} | :class:`dict`
                Dictionary of major grid line line style options
            *MinorGrid*: {``None``} | ``True`` | ``False``
                Turn on/off minor grid lines, or leave as is if ``None``
            *MinorGridStyle*: {``{}``} | :class:`dict`
                Dictionary of minor grid line line style options
        :Outputs:
            *h*: :class:`plot_mpl.MPLHandle`
                Object of :mod:`matplotlib` handles
        :Versions:
            * 2015-05-30 ``@ddalle``: First version
            * 2015-12-14 ``@ddalle``: Added error bars
            * 2019-12-26 ``@ddalle``: From :mod:`tnakit.db.db1`
        """
       # --- Process Args ---
        # Process coefficient name and remaining coeffs
        col, I, J, a, kw = self._process_plot_args1(*a, **kw)
        # Get list of arguments
        arg_list = self.get_eval_args(col)
        # Get key for *x* axis
        xk = kw.pop("xcol", kw.pop("xk", arg_list[0]))
       # --- Options: What to plot ---
        # Plot exact values, interpolated (eval), and markers of actual data
        qexact  = kw.pop("PlotExact",  False)
        qinterp = kw.pop("PlotInterp", True)
        qmark   = kw.pop("MarkExact",  True)
        # Default UQ coefficient
        uk_def = self.get_uq_col(col)
        # Ensure string
        if typeutils.isarray(uk_def):
            uk_def = uk_def[0]
        # Get UQ coefficient
        uk  = kw.pop("ucol",       kw.pop("uk", uk_def))
        ukM = kw.pop("ucol_minus", kw.pop("ukM", uk))
        ukP = kw.pop("ucol_plus",  kw.pop("ukP", uk))
       # --- Plot Values ---
        # Initialize output
        h = pmpl.MPLHandle()
        # Initialize plot options in order to reduce aliases, etc.
        opts = pmpl.MPLOpts(warnmode=0, **kw)
        # Uncertainty plot flag
        quq = opts.get("ShowUncertainty", False)
        # Y-axis values: exact
        if qexact:
            # Get corresponding *x* values
            xe = self.get_xvals(xk, I, **kw)
            # Try to get values directly from database
            ye = self.get_yvals_exact(col, I, **kw)
            # Evaluate UQ-minus
            if quq and ukM:
                # Get UQ value below
                uyeM = self.eval_from_index(ukM, I, **kw)
            elif quq:
                # Use zeros for negative error term
                uyeM = np.zeros_like(ye)
            # Evaluate UQ-pluts
            if quq and ukP and ukP==ukM:
                # Copy negative terms to positive
                uyeP = uyeM
            elif quq and ukP:
                # Evaluate separate UQ above
                uyeP = self.eval_from_index(ukP, I, **kw)
            elif quq:
                # Use zeros
                uyeP = np.zeros_like(ye)
        # Y-axis values: evaluated/interpolated
        if qmark or qinterp:
            # Get values for *x*-axis
            xv = self.get_xvals_eval(xk, col, *a, **kw)
            # Evaluate function
            yv = self.__call__(col, *a, **kw)
            # Evaluate UQ-minus
            if quq and ukM:
                # Get UQ value below
                uyM = self.eval_from_arglist(ukM, arg_list, *a, **kw)
            elif quq:
                # Use zeros for negative error term
                uyM = np.zeros_like(yv)
            # Evaluate UQ-pluts
            if quq and ukP and ukP==ukM:
                # Copy negative terms to positive
                uyP = uyM
            elif quq and ukP:
                # Evaluate separate UQ above
                uyP = self.eval_from_arglist(ukP, arg_list, *a, **kw)
            elif quq:
                # Use zeros
                uyP = np.zeros_like(yv)
       # --- Data Cleanup ---
        # Create input to *markevery*
        if qmark:
            # Check length
            if J.size == xv.size:
                # Mark all cases
                marke = None
            else:
                # Convert to list
                marke = list(J)
        # Remove extra keywords if possible
        for k in arg_list:
            kw.pop(k, None)
       # --- Primary Plot ---
        # Initialize output
        h = pmpl.MPLHandle()
        # Initialize plot options in order to reduce aliases, etc.
        opts = pmpl.MPLOpts(**kw)
        # Initialize plot options and get them locally
        kw_p = opts.setdefault("PlotOptions", {})
        # Create a copy
        kw_p0 = dict(kw_p)
        # Existing uncertainty plot type
        t_uq = opts.get("UncertaintyPlotType")
        # Marked and interpolated data
        if qinterp or qmark:
            # Default marker setting
            if qmark:
                kw_p.setdefault("marker", "^")
            else:
                kw_p.setdefault("marker", "")
            # Default line style
            if not qinterp:
                # Turn off lines
                kw_p.setdefault("ls", "")
                # Default UQ style is error bars
                if t_uq is None:
                    opts["UncertaintyPlotType"] = "errorbar"
            # Check for uncertainty
            if quq:
                # Set values
                opts["yerr"] = np.array([uyM, uyP])
            # Call the main function
            hi = pmpl.plot(xv, yv, **opts)
            # Apply markers
            if qmark:
                # Get line handle
                hl = hi.lines[0]
                # Apply which indices to mark
                hl.set_markevery(marke)
            # Combine
            h.add(hi)
       # --- Exact Plot ---
        # Plot exact values
        if qexact:
            # Turn on marker
            if "marker" not in kw_p0:
                kw_p["marker"] = "^"
            # Turn *lw* off
            if "ls" not in kw_p0:
                kw_p["ls"] = ""
            # Set UQ style to "errorbar"
            if t_uq is None:
                opts["UncertaintyPlotType"] = "errorbar"
            # Check for uncertainty
            if quq:
                # Set values
                opts["yerr"] = np.array([uyeM, uyeP])
            # Plot exact data
            he = pmpl.plot(xe, ye, **opts)
            # Combine
            h.add(he)
       # --- Cleanup ---
        # Output
        return h
       # ---
  # >

  # ===================
  # Regularization
  # ===================
  # <
   # --- RBF ---
    # Regularization using radial basis functions
    def regularize_by_rbf(self, cols, args=None, **kw):
        r"""Regularize col(s) to full-factorial matrix of several args

        The values of each *arg* to use for the full-factorial matrix
        are taken from the *db.bkpts* dictionary, usually generated by
        :func:`get_bkpts`.  The values in *db.bkpts*, however, can be
        set manually in order to interpolate the data onto a specific
        matrix of points.
        
        :Call:
            >>> db.regularize_by_rbf(cols=None, args=None, **kw)
        :Inputs:
            *db*: :class:`attdb.rdb.DataKit`
                Database with response toolkit
            *cols*: :class:`list`\ [:class:`str`]
                List of output data columns to regularize
            *args*: {``None``} | :class:`list`\ [:class:`str`]
                List of arguments; default from *db.eval_args*
            *scol*: {``None``} | :class:`str` | :class:`list`
                Optional name of slicing arg for matrix
            *cocols*: {``None``} | :class:`list`\ [:class:`str`]
                Other dependent input cols; default from *db.bkpts*
            *function*: {``"cubic"``} | ``"multiquadric"`` | ``"linear"``
                Basis function for :class:`scipy.interpolate.Rbf`
            *tol*: {``1e-4``}  | :class:`float`
                Default tolerance to use in combination with *slices*
            *tols*: {``{}``} | :class:`dict`
                Dictionary of specific tolerances for single keys in *slices*
        :Versions:
            * 2018-06-08 ``@ddalle``: First version
            * 2020-02-24 ``@ddalle``: Version 2.0
        """
       # --- Options ---
        # Get translators
        trans = kw.get("translators", {})
        prefix = kw.get("prefix")
        suffix = kw.get("suffix")
        # Translator args
        tr_args = (trans, prefix, suffix)
       # --- Status Checks ---
        # Get break points
        bkpts = self.__dict__.get("bkpts")
        # Check
        if bkpts is None:
            raise AttributeError(
                "Break point dict must be present; see get_bkpts()")
       # --- Cols Check ---
        # Convert single column
        if typeutils.isstr(cols):
            cols = [cols]
        # Check columns
        if not isinstance(cols, list):
            raise TypeError(
                "Regularization cols must be list, got %s" % type(cols))
        # Number of cols
        ncols = len(cols)
        # Check for empty list
        if ncols == 0:
            raise IndexError("Col list is empty")
        # Check each column
        for (j, col) in enumerate(cols):
            # Check type
            if not typeutils.isstr(col):
                raise TypeError(
                    "Col %i must be str, got %s" % (j, type(col)))
            # Check availability
            if col not in self:
                raise KeyError("Col '%s' is not in database" % col)
            # Get data type
            dtype = self.get_col_dtype(col)
            # Ensure float
            if not (dtype.startswith("float") or dtype.startswith("complex")):
                raise TypeError(
                    "Nonnumeric dtype '%s' for col '%s'" % (dtype, col))
       # --- Args Check ---
        # Default input args
        if args is None:
            # Use args for last *col*
            args = self.get_eval_args(col)
        # Backup input args
        if args is None:
            # Initialize list
            args = []
            # Loop through keys of *bkpts*
            # Note uncontrolled order
            for arg in bkpts:
                # Check if used as *col*
                if arg in cols:
                    continue
                # Get data type
                dtype = self.get_col_dtype(arg)
                # Ensure float
                if (dtype is not None) and not dtype.startswith("float"):
                    continue
                # Otherwise use it
                args.append(arg)
        # Checks
        if not isinstance(args, list):
            raise TypeError("Arg list must be 'list', got %s" % type(args))
        # Number of input args
        narg = len(args)
        # Check types
        for (j, arg) in enumerate(args):
            # Check type
            if not typeutils.isstr(arg):
                raise TypeError(
                    "Arg %i must be str, got %s" % (j, type(arg)))
            # Check presence
            if arg not in bkpts:
                raise KeyError("No break points for arg '%s'" % arg)
       # --- Slice Cols ---
        # Get optional slice column
        scol = kw.get("scol")
        # Check for list
        if isinstance(scol, list):
            # Get additional slice keys
            subcols = scol[1:]
            # Single slice key
            maincol = scol[0]
        elif scol is None:
            # No slices at all
            subcols = []
            maincol = None
        else:
            # No additional slice keys
            subcols = []
            maincol = scol
            # List of slice keys
            scol = [scol]
        # Remove slice keys from arg list to interpolants
        if scol is None:
            # No checks
            iargs = args
        else:
            # Check against *scol*
            iargs = [arg for arg in args if arg not in scol]
       # --- Full-Factorial Matrix ---
        # Get full-factorial matrix at the current slice value
        X, slices = self.get_fullfactorial(scol=scol, cols=args)
        # Number of output points
        nX = X[args[0]].size
        # 
        # Save the lookup values
        for arg in args:
            # Translate column name
            argreg = self._translate_colname(arg, *tr_args)
            # Save values
            self.save_col(argreg, X[arg])
            # Check if new
            if argreg != arg:
                # Get previous definition
                defn = self.get_defn(arg)
                # Save a copy
                self.defns[argref] = self._defncls(**defn)
                # Link break points
                bkpts[argreg] = bkpts[arg]
       # --- Regularization ---
        # Perform interpolations
        for c in coeffs:
            # Status update
            if kw.get("v"):
                print("  Interpolating coefficient '%s'" % c)
            # Check for slices
            if skey is None:
                # One interpolant
                f = self.CreateRBF(c, keys, **kw)
                # Create tuple of input arguments
                args = tuple(X[k] for k in keys)
                # Evaluate coefficient
                DBi[c] = f(*args)
                
            else:
                
                # Number of slices
                nslice = slices[mainkey].size
                # Initialize data
                V = np.zeros_like(X[mainkey])
                # Loop through slices
                for i in range(nslice):
                    # Status update
                    if kw.get("v"):
                        # Get main key value
                        m = slices[mainkey][i]
                        # Get value in fixed number of characters
                        sv = ("%6g" % m)[:6]
                        # In-place status update
                        sys.stdout.write("    Slice %s=%s (%i/%i)\r"
                            % (mainkey, sv, i+1, nslice))
                        sys.stdout.flush()
                        
                    # Initialize mask
                    J = np.ones(nX, dtype="bool")
                    # Initialize slice
                    slice_i = {}
                    # Loop through keys
                    for k in skey:
                        # Get value
                        vk = slices[k][i]
                        # Constrain
                        J = np.logical_and(J, X[k]==vk)
                        # Save local slice
                        slice_i[k] = vk
                    # Get indices of slice
                    I = np.where(J)[0]
                    # Create interpolant for fixed value of *skey*
                    f = self.CreateRBF(c, ikeys, slices=slice_i, **kw)
                    # Create tuple of input arguments
                    args = tuple(X[k][I] for k in ikeys)
                    # Evaluate coefficient
                    V[I] = f(*args)
                # Save the values
                DBi[c] = V
                # Clean up prompt
                if kw.get("v"):
                    print("")
            # Add to coefficient list
            DBi.coeffs.append(c)
        # Trajectory co-keys
        cokeys = kw.get("cokeys", self.bkpts.keys())
        # Map other breakpoint keys
        for k in cokeys:
            # Skip if already present
            if k in DBi.bkpts: continue
            # Check for slices
            if mainkey is None: break
            # Check size
            if self[mainkey].size != self[k].size:
                continue
            # Regular matrix values of slice key
            M = X[mainkey]
            # Initialize data
            V = np.zeros_like(M)
            # Initialize break points
            T = []
            # Status update
            if kw.get("v"):
                print("  Mapping key '%s'" % k)
            # Loop through slice values
            for m in DBi.bkpts[mainkey]:
                # Find value of slice key matching that parameter
                i = np.where(self[mainkey] == m)[0][0]
                # Output value
                v = self[k][i]
                # Get the indices of break points with that value
                J = np.where(M == m)[0]
                # Evaluate coefficient
                V[J] = v
                # Save break point
                T.append(v)
            # Save the values
            DBi[k] = V
            # Save break points
            DBi.bkpts[k] = np.array(T)
            # Save key name if needed
            if k not in DBi.coeffs: DBi.coeffs.append(k)
            
        # Copy any other keys
        for k in kw.get("copykeys", self.coeffs):
            # Skip if already processed
            if k in DBi: continue
            # Otherwise, copy
            DBi[k] = self[k].copy()
            # Save the coefficient to the list, too
            DBi.coeffs.append(k)
            
        # Normalize trajectory
        DBi.GetTrajectory()
        # Output
        return DBi
  # >
