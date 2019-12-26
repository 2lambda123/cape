#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`cape.attdb.rdbscalar`: ATTDB with scalar output functions
================================================================

This module provides the class :class:`DBResponseScalar` as a subclass
of :class:`DBResponseNull` that adds support for output variables that
have scalars that are a function of one or more variables.  For example
if *db* is an instance of :class:`DBResponseScalar` with an axial force
coefficient *CA* that is a function of Mach number (``"mach"``) and
angle of attack (``"alpha"``), the database can allow for the following
syntax.

    .. code-block:: pycon

        >>> CA = db("CA", mach=1.2, alpha=0.2)

This is accomplished by implementing the special :func:`__call__`
method for this class.

This class also serves as a type test for non-null "response" databases
in the ATTDB framework.  Databases that can be evaluated in this manor
will pass the following test:

    .. code-block:: python

        isinstance(db, cape.attdb.rdbscalar.DBResponseScalar)

Because this class inherits from :class:`DBResponseNull`, it has
interfaces to several different file types.

"""

# Standard library modules
import os

# Third-party modules
import numpy as np

# Semi-optional third-party modules
try:
    import scipy.interpolate.rbf as scirbf
except ImportError:
    scirbf = None

# CAPE modules
import cape.tnakit.kwutils as kwutils
import cape.tnakit.typeutils as typeutils
import cape.tnakit.plot_mpl as pmpl

# Data types
import cape.attdb.ftypes as ftypes

# Local modules, direct
from .rdbnull import DBResponseNull


# Accepted list for eval_method
RBF_METHODS = [
    "rbf", "rbf-map", "rbf-linear"
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


# Declare base class
class DBResponseScalar(DBResponseNull):
    r"""Basic database template with scalar output variables
    
    :Call:
        >>> db = DBResponseScalar(fname=None, **kw)
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
        *db*: :class:`cape.attdb.rdbscalar.DBResponseScalar`
            Database with scalar output functions
    :Versions:
        * 2019-12-26 ``@ddalle``: First version
    """
  # =====================
  # Class Attributes
  # =====================
  # <
  # >

  # ===================
  # Config
  # ===================
  # <
   # --- Attributes ---
    # Get attribute with defaults
    def getattrdefault(self, attr, vdef):
        r"""Get attribute from instance

        :Call:
            >>> v = db.getattrdefault(attr, vdef)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *attr*: :class:`str`
                Name of attribute
            *vdef*: any
                Default value of attribute
        :Outputs:
            *v*: *db.__dict__[attr]* | *vdef*
                One of the two values specified above
        :Effects:
            *db.__dict__[attr]*: *v*
                Sets *db.(attr)* if necessary
        :Versions:
            * 2019-12-18 ``@ddalle``: First version
        """
        return self.__dict__.setdefault(attr, vdef)

    # Get an attribute with default to dictionary
    def getattrdict(self, attr):
        r"""Get attribute from instance

        :Call:
            >>> v = db.getattrdefault(attr, vdef)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *attr*: :class:`str`
                Name of attribute
            *vdef*: any
                Default value of attribute
        :Outputs:
            *v*: *db.__dict__[attr]* | *vdef*
                One of the two values specified above
        :Effects:
            *db.__dict__[attr]*: *v*
                Sets *db.__dict__[attr]* if necessary
        :Versions:
            * 2019-12-18 ``@ddalle``: First version
        """
        return self.__dict__.setdefault(attr, {})
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            * 2019-01-07 ``@ddalle``: First version
        """
       # --- Get coefficient name ---
        # Process coefficient
        col, a, kw = self._prep_args_colname(*a, **kw)
       # --- Get method ---
        # Attempt to get default evaluation method
        try:
            # Check for evaluation methods and "_" key is default
            method_def = self.eval_method["_"]
        except AttributeError:
            # No evaluation method at all
            raise AttributeError("Database has no evaluation methods")
        except KeyError:
            # No default
            method_def = "nearest"
        # Specific method
        method_col = self.eval_method.get(col, method_def)
        # Check for ``None``, which forbids lookup
        if method_col is None:
            raise ValueError("Col '%s' is not an evaluation column" % col)
       # --- Get argument list ---
        # Specific lookup arguments (and copy it)
        args_col = list(self.get_eval_arg_list(col))
       # --- Evaluation kwargs ---
        # Attempt to get default aliases
        try:
            # Check for attribute and "_" default
            kw_def = self.eval_kwargs["_"]
            # Use default as fallback
            kw_fn = self.eval_kwargs.get(col, kw_def)
        except AttributeError:
            # No kwargs to eval functions
            kw_fn = {}
        except KeyError:
            # No default
            kw_fn = self.eval_kwargs.get(col, {})
       # --- Aliases ---
        # Attempt to get default aliases
        try:
            # Check for attribute and "_" default
            alias_def = self.eval_arg_aliases["_"]
            # Use default as fallback
            arg_aliases = self.eval_arg_aliases.get(col, alias_def)
        except AttributeError:
            # No aliases
            arg_aliases = {}
        except KeyError:
            # No default
            arg_aliases = self.eval_arg_aliases.get(col, {})
        # Process aliases in *kw*
        for k in dict(kw):
            # Check if there's an alias for *k*
            if k not in arg_aliases: continue
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
        # Process the appropriate lookup function
        if method_col in ["nearest"]:
            # Evaluate nearest-neighbor lookup
            f = self.eval_nearest
        elif method_col in ["linear", "multilinear"]:
            # Evaluate using multilinear interpolation
            f = self.eval_multilinear
        elif method_col in ["linear-schedule", "multilinear-schedule"]:
            # Evaluate using scheduled (in 1D) multilinear interpolation
            f = self.eval_multilinear_schedule
        elif method_col in ["rbf"]:
            # Evaluate global radial basis function
            f = self.eval_rbf
        elif method_col in ["rbf-slice", "rbf-linear"]:
            # Evaluate linear interpolation of two RBFs
            f = self.eval_rbf_linear
        elif method_col in ["rbf-map", "rbf-schedule"]:
            # Evaluate curvilinear interpolation of slice RBFs
            f = self.eval_rbf_schedule
        elif method_col in ["function", "func", "fn"]:
            # Combine args
            kw_fn = dict(kw_fn, **kw)
            # Evaluate specific function
            f = self.eval_function
        else:
            # Unknown method
            raise ValueError(
                "Could not interpret evaluation method '%s'" % method_col)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        args = self.get_eval_arg_list(coeff)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        args_col = self.get_eval_arg_list(col)
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
            args_k = self.get_eval_arg_list(uk)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        args_col = self.get_eval_arg_list(col)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        args_col = self.get_eval_arg_list(col)
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
    def SetEvalMethod(self, cols=None, method=None, args=None, *a, **kw):
        r"""Set evaluation method for a one or more columns

        :Call:
            >>> db.SetEvalMethod(col, method=None, args=None, **kw)
            >>> db.SetEvalMethod(cols, method=None, args=None, **kw)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *cols*: :class:`list`\ [:class:`str`]
                List of columns for which to declare evaluation rules
            *col*: :class:`str`
                Name of column for which to declare evaluation rules
            *method*: ``"nearest"`` | ``"linear"`` | :class:`str`
                Response (lookup/interpolation/evaluation) method name 
            *args*: :class:`list`\ [:class:`str`]
                List of input arguments
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
        """
        # Check for list
        if isinstance(cols, typeutils.strlike):
            # Singleton list
            cols = [cols]
        elif not isinstance(cols, (list, tuple, set)):
            # Not a list
            raise TypeError(
                "Columns to specify evaluation for must be list; " +
                ("got '%s'" % type(cols)))
        # Loop through coefficients
        for col in cols:
            # Check type
            if not isinstance(col, typeutils.strlike):
                # Not a string
                raise TypeError("Eval col must be a string")
            # Specify individual col
            self._set_method1(col, method, args, *a, **kw)

    # Save a method for one coefficient
    def _set_method1(self, col=None, method=None, args=None, *a, **kw):
        r"""Set evaluation method for a single column

        :Call:
            >>> db._set_method1(col=None, method=None, args=None, **kw)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column for which to declare evaluation rules
            *method*: ``"nearest"`` | ``"linear"`` | :class:`str`
                Response (lookup/interpolation/evaluation) method name 
            *args*: :class:`list`\ [:class:`str`]
                List of input arguments
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
        """
       # --- Metadata checks ---
        # Dictionary of methods
        eval_method = self.getattrdict("eval_method")
        # Argument lists
        eval_args = self.getattrdict("eval_args")
        # Argument aliases (i.e. alternative names)
        eval_arg_aliases = self.getattrdict("eval_arg_aliases")
        # Evaluation keyword arguments
        eval_kwargs = self.getattrdict("eval_kwargs")
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
        # Check for ``None``
        if (not arg_aliases):
            # Empty option is empty dictionary
            arg_aliases = {}
        # Save aliases
        eval_arg_aliases[col] = arg_aliases
        # Get alias option
        eval_kwargs_kw = kw.get("eval_kwargs", {})
        # Check for ``None``
        if (not eval_kwargs_kw):
            # Empty option is empty dictionary
            eval_kwargs_kw = {}
        # Save keywords (new copy)
        eval_kwargs[col] = dict(eval_kwargs_kw)
       # --- Method switch ---
        # Check for identifiable method
        if method in ["nearest"]:
            # Nearest-neighbor lookup
            eval_method[col] = "nearest"
        elif method in ["linear", "multilinear"]:
            # Linear/multilinear interpolation
            eval_method[col] = "multilinear"
        elif method in ["linear-schedule", "multilinear-schedule"]:
            # (N-1)D linear interp in last keys, 1D in first key
            eval_method[col] = "multilinear-schedule"
        elif method in ["rbf", "rbg-global", "rbf0"]:
            # Create global RBF
            self.CreateGlobalRBFs([col], args, **kw)
            # Metadata
            eval_method[col] = "rbf"
        elif method in ["lin-rbf", "rbf-linear", "linear-rbf"]:
            # Create RBFs on slices
            self.CreateSliceRBFs([col], args, **kw)
            # Metadata
            eval_method[col] = "rbf-linear"
        elif method in ["map-rbf", "rbf-schedule", "rbf-map", "rbf1"]:
            # Create RBFs on slices but scheduled
            self.CreateSliceRBFs([col], args, **kw)
            # Metadata
            eval_method[col] = "rbf-map"
        elif method in ["function", "fn", "func"]:
            # Create eval_func dictionary
            eval_func = self.getattrdict("eval_func")
            # Create eval_func dictionary
            eval_func_self = self.getattrdict("eval_func_self")
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

            # Dedicated function
            eval_method[col] = "function"
        else:
            raise ValueError(
                "Did not recognize evaluation type '%s'" % method)
        # Argument list is the same for all methods
        eval_args[col] = args

   # --- Options: Get ---
    # Get argument list
    def get_eval_arg_list(self, col):
        r"""Get list of evaluation arguments

        :Call:
            >>> args = db.get_eval_arg_list(col)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        # Attempt to get default
        try:
            # Check for attribute and "_" default
            args_def = self.eval_args["_"]
        except AttributeError:
            # No argument lists at all
            raise AttributeError("Database has no evaluation argument lists")
        except KeyError:
            # No default
            args_def = None
        # Specific lookup arguments
        args_col = self.eval_args.get(col, args_def)
        # Check for ``None``, which forbids lookup
        if args_col is None:
            raise ValueError("Column '%s' is not an evaluation cooeff" % col)
        # Output a copy
        return list(args_col)

    # Get evaluation method
    def get_eval_method(self, col):
        r"""Get evaluation method (if any) for a column

        :Call:
            >>> meth = db.get_eval_method(col)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *col*: :class:`str`
                Name of column to evaluate
        :Outputs:
            *meth*: ``None`` | :class:`str`
                Name of evaluation method, if any
        :Versions:
            * 2019-03-13 ``@ddalle``: First version
            * 2019-12-18 ``@ddalle``: Ported from :mod:`tnakit`
        """
        # Get attribute
        eval_methods = self.__dict__.setdefault("eval_method", {})
        # Get method
        return eval_methods.get(col)

    # Get evaluation argument converter
    def get_eval_arg_converter(self, k):
        r"""Get evaluation argument converter

        :Call:
            >>> f = db.get_eval_arg_converter(k)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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

   # --- Options: Set ---
    # Set a default value for an argument
    def set_arg_default(self, k, v):
        r"""Set a default value for an evaluation argument

        :Call:
            >>> db.set_arg_default(k, v)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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

   # --- Arguments ---
    # Attempt to get all values of an argument
    def get_all_values(self, k):
        r"""Attempt to get all values of a specified argument

        This will use *db.eval_arg_converters* if possible.

        :Call:
            >>> V = db.get_all_values(k)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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

    # Get argument value
    def get_arg_value(self, i, k, *a, **kw):
        r"""Get the value of the *i*\ th argument to a function

        :Call:
            >>> v = db.get_arg_value(i, k, *a, **kw)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        args_coeff = self.get_eval_arg_list(coeff)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        # Count
        n = len(V)
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
        return np.sum(F*V[J])

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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        try:
            f = self.eval_func[col]
        except AttributeError:
            # No evaluation functions set
            raise AttributeError(
                "No evaluation functions present in database")
        except KeyError:
            # No keys
            raise KeyError(
                "No evaluation function for col '%s'" % col)
        # Evaluate
        if self.eval_func_self.get(col):
            # Use reference to *self*
            return f(self, *x, **kw)
        else:
            # Stand-alone function
            return f(*x, **kw)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
    def CreateSliceRBFs(self, cols, args, I=None, **kw):
        r"""Create radial basis functions for each slice of *args[0]*

        The first entry in *args* is interpreted as a "slice" key; RBFs
        will be constructed at constant values of *args[0]*.

        :Call:
            >>> db.CreateSliceRBFs(coeffs, args, I=None)
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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

  # ===================
  # Data
  # ===================
  # <
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
            args = self.get_eval_arg_list(col)
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
        :Inputs:
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
                Database with scalar output functions
            *args*: :class:`list`\ [:class:`str`]
                List of argument names to match
            *a*: :class:`tuple`\ [:class:`float`]
                Values of the arguments
            *tol*: {``1e-4``} | :class:`float` >= 0
                Default tolerance for all *args*
            *tols*: {``{}``} | :class:`dict`\ [:class:`float` >= 0]
                Dictionary of tolerances specific to arguments
            *kw*: :class:`dict`
                Additional values to use during evaluation
        :Outputs:
            *I*: :class:`np.ndarray`\ [:class:`int`]
                Indices of cases in *db* that match conditions
            *J*: :class:`np.ndarray`\ [:class:`int`]
                Indices of (*a*, *kw*) that have a match in *db*
        :Versions:
            * 2019-03-11 ``@ddalle``: First version
            * 2019-12-26 ``@ddalle``: From :func:`DBCoeff.FindMatches`
        """
       # --- Input Checks ---
        # Find a valid argument
        for arg in args:
            # Check if it's present
            if arg in self:
                # Found at least one valid argument
                break
        else:
            # Loop completed; nothing found
            raise ValueError(
                "Cannot find matches for argument list %s" % args)
        # Overall tolerance default
        tol = kw.pop("tol", 1e-4)
        # Specific tolerances
        tols = kw.pop("tols", {})
        # Number of values
        n = len(self[arg])
       # --- Argument values ---
        # Initialize lookup point
        x = []
        # Loop through arguments
        for i, k in enumerate(args):
            # Get value
            xi = self.get_arg_value(i, k, *a, **kw)
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
        # Loop through entries
        for i in range(nx):
            # Initialize tests for this point (set to ``True``)
            Mi = np.arange(n) > -1
            # Loop through arguments
            for j, k in enumerate(args):
                # Get total set of values
                Xk = self.get_all_values(k)
                # Check if present
                if (k is None) or (Xk is None):
                    continue
                # Check size
                if (i == 0) and (len(Xk) != n):
                    raise ValueError(
                        ("Parameter '%s' has size %i, " % (k, len(Xk))) +
                        ("expecting %i" % n))
                # Get argument value
                xi = X[j][i]
                # Get tolerance for this key
                xtol = tols.get(k, tol)
                # Check tolerance
                Mi = np.logical_and(Mi, np.abs(Xk-xi) <= xtol)
            # Combine point constraints
            MI = np.logical_or(MI, Mi)
            # Check for any matches of this data point
            MJ[i] = np.any(Mi)
        # Convert masks to indices
        I = np.where(MI)[0]
        J = np.where(MJ)[0]
        # Return combined set of matches
        return I, J
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        arg_list = self.get_eval_arg_list(col)
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
            *db*: :class:`attdb.rdbscalar.DBResponseScalar`
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
        arg_list = self.get_eval_arg_list(col)
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