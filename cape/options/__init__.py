"""
CAPE generic settings module: :mod:`cape.options`
=================================================

This module provides tools to read, access, modify, and write settings for
:mod:`cape`.  The class is based off of the built-int :class:`dict` class, so
its default behavior, such as ``opts['InputCntl']`` or 
``opts.get('InputCntl')`` are also present.  In addition, many convenience
methods, such as ``opts.set_it_fc(n)``, which sets the number of
:file:`flowCart` iterations,  are provided.

In addition, this module controls default values of each pyCart
parameter in a two-step process.  The precedence used to determine what the
value of a given parameter should be is below.

    *. Values directly specified in the input file, :file:`cape.json`
    
    *. Values specified in the default control file,
       :file:`$CAPE/settings/cape.default.json`
    
    *. Hard-coded defaults from this module
"""

# Import options-specific utilities (loads :mod:`os`, too)
from util import *

# Import more specific modules for controlling subgroups of options
from .pbs        import PBS
from .DataBook   import DataBook, DBTarget
from .Report     import Report
from .Mesh       import Mesh
from .Config     import Config
from .runControl import RunControl

# Class definition
class Options(odict):
    """
    Options structure, subclass of :class:`dict`
    
    :Call:
        >>> opts = Options(fname=None, **kw)
    :Inputs:
        *fname*: :class:`str`
            File to be read as a JSON file with comments
        *kw*: :class:`dict`
            Dictionary to be transformed into :class:`cape.options.Options`
    :Outputs:
        *opts*: :class:`cape.options.Options`
            Options interface
    :Versions:
        * 2014-07-28 ``@ddalle``: First version
    """
    
    # Initialization method
    def __init__(self, fname=None, **kw):
        """Initialization method with optional JSON input"""
        # Check for an input file.
        if fname:
            # Read the JSON file
            d = loadJSONFile(fname)
            # Loop through the keys.
            for k in d:
                kw[k] = d[k]
        # Read the defaults.
        defs = getCapeDefaults()
        # Apply the defaults.
        kw = applyDefaults(kw, defs)
        # Store the data in *this* instance
        for k in kw:
            self[k] = kw[k]
        # Upgrade important groups to their own classes.
        self._PBS()
        self._Mesh()
        self._Report()
        self._DataBook()
        self._Config()
        self._RunControl()
        # Add extra folders to path.
        self.AddPythonPath()
        
    # Function to add to the path.
    def AddPythonPath(self):
        """Add requested locations to the Python path
        
        :Call:
            >>> opts.AddPythonPath()
        :Inputs:
            *opts*: :class:`cape.options.Options`
                Options interface
        :Versions:
            * 2014-10-08 ``@ddalle``: First version
        """
        # Get the "PythonPath" option
        lpath = self.get("PythonPath", [])
        # Quit if empty.
        if (not lpath): return
        # Ensure list.
        if type(lpath).__name__ != "list":
            lpath = [lpath]
        # Loop through elements.
        for fdir in lpath:
            # Add absolute path, not relative.
            os.sys.path.append(os.path.abspath(fdir))
            
    # Make a directory
    def mkdir(self, fdir):
        """Make a directory with the correct permissions
        
        :Call:
            >>> opts.mkdir(fdir)
        :Inputs:
            *opts*: :class:`cape.options.Options`
                Options interface
            *fdir*: :class:`str`
                Directory to create
        :Versions:
            * 2015-09-27 ``@ddalle``: First version
        """
        # Get umask
        umask = self.get_umask()
        # Apply umask
        dmask = 0777 - umask
        # Make the directory.
        os.mkdir(fdir, dmask)
    
    # ============
    # Initializers
    # ============
   # < 
   
    # Initialization method for folder management optoins
    def _RunControl(self):
        """Initialize folder management options if necessary"""
        # Check status.
        if 'RunControl' not in self:
            # Missing entirely.
            self['RunControl'] = RunControl()
        elif type(self['RunControl']).__name__ == 'dict':
            # Convert to special class
            self['RunControl'] = RunControl(**self['RunControl'])
    
    # Initialization and confirmation for Adaptation options
    def _Mesh(self):
        """Initialize mesh options if necessary"""
        # Check status
        if 'Mesh' not in self:
            # Missing entirely
            self['Mesh'] = Mesh()
        elif type(self['Mesh']).__name__ == 'dict':
            # Convert to special class.
            self['Mesh'] = Mesh(**self['Mesh'])
            
    # Initialization and confirmation for PBS options
    def _PBS(self):
        """Initialize PBS options if necessary"""
        # Check status.
        if 'PBS' not in self:
            # Missing entirely
            self['PBS'] = PBS()
        elif type(self['PBS']).__name__ == 'dict':
            # Add prefix to all the keys.
            tmp = {}
            for k in self['PBS']:
                tmp["PBS_"+k] = self['PBS'][k]
            # Convert to special class.
            self['PBS'] = PBS(**tmp)
            
    # Initialization method for databook
    def _DataBook(self):
        """Initialize data book options if necessary"""
        # Check status.
        if 'DataBook' not in self:
            # Missing entirely.
            self['DataBook'] = DataBook()
        elif type(self['DataBook']).__name__ == 'dict':
            # Convert to special class
            self['DataBook'] = DataBook(**self['DataBook'])
            
    # Initialization method for automated report
    def _Report(self):
        """Initialize report options if necessary"""
        # Check status.
        if 'Report' not in self:
            # Missing entirely.
            self['Report'] = Report()
        elif type(self['Report']).__name__ == 'dict':
            # Convert to special class
            self['Report'] = Report(**self['Report'])
            
    # Initialization and confirmation for PBS options
    def _Config(self):
        """Initialize configuration options if necessary"""
        # Check status.
        if 'Config' not in self:
            # Missing entirely
            self['Config'] = Config()
        elif type(self['Config']).__name__ == 'dict':
            # Add prefix to all the keys.
            tmp = {}
            for k in self['Config']:
                # Check for "File"
                if k == 'File':
                    # Add prefix.
                    tmp["Config"+k] = self['Config'][k]
                else:
                    # Use the key as is.
                    tmp[k] = self['Config'][k]
            # Convert to special class.
            self['Config'] = Config(**tmp)
        
   # >
    
    # ==============
    # Global Options
    # ==============
   # <
   
    # Function to get the shell commands
    def get_ShellCmds(self):
        """Get shell commands, if any
        
        :Call:
            >>> cmds = opts.get_ShellCmds()
        :Inputs:
            *opts*: :class:`pyCart.options.Options`
                Options interface
        :Outputs:
            *cmds*: :class:`list` (:class:`str`)
                List of initialization commands
        :Versions:
            * 2015-11-08 ``@ddalle``: Moved to "RunControl"
        """
        # Get the commands.
        cmds = self.get('ShellCmds', [])
        # Turn to a list if not.
        if type(cmds).__name__ != 'list':
            cmds = [cmds]
        # Output
        return cmds
        
    # Function to set the shell commands
    def set_ShellCmds(self, cmds):
        """Set shell commands
        
        :Call:
            >>> opts.set_ChellCmds(cmds=[])
        :Inputs:
            *opts*: :class:`pyCart.options.Options`
                Options interface
            *cmds*: :class:`list` (:class:`str`)
                List of initialization commands
        :Versions:
            * 2015-11-08 ``@ddalle``: First version
        """
        # Set them.
        self['ShellCmds'] = cmds
    
    # Method to get the max number of jobs to submit.
    def get_nSubmit(self):
        """Return the maximum number of jobs to submit at one time
        
        :Call:
            >>> nSub = opts.get_nSubmit()
        :Inputs:
            *opts*: :class:`pyCart.options.Options`
                Options interface
        :Outputs:
            *nSub*: :class:`int`
                Maximum number of jobs to submit
        :Versions:
            * 2015-01-24 ``@ddalle``: First version
        """
        return self.get('nSubmit', rc0('nSubmit'))
        
    # Set the max number of jobs to submit.
    def set_nSubmit(self, nSub=rc0('nSubmit')):
        """Set the maximum number of jobs to submit at one time
        
        :Call:
            >>> opts.set_nSubmit(nSub)
        :Inputs:
            *opts*: :class:`pyCart.options.Options`
                Options interface
            *nSub*: :class:`int`
                Maximum number of jobs to submit
        :Versions:
            * 2015-01-24 ``@ddalle``: First version
        """
        self['nSubmit'] = nSub
    
    # Method to determine if groups have common meshes.
    def get_GroupMesh(self):
        """Determine whether or not groups have common meshes
        
        :Call:
            >>> qGM = opts.get_GroupMesh()
        :Inputs:
            *opts* :class:`pyCart.options.Options`
                Options interface
        :Outputs:
            *qGM*: :class:`bool`
                True all cases in a group use the same (starting) mesh
        :Versions:
            * 2014-10-06 ``@ddalle``: First version
        """
        # Safely get the trajectory.
        x = self.get('Trajectory', {})
        return x.get('GroupMesh', rc0('GroupMesh'))
        
    # Method to specify that meshes do or do not use the same mesh
    def set_GroupMesh(self, qGM=rc0('GroupMesh')):
        """Specify that groups do or do not use common meshes
        
        :Call:
            >>> opts.get_GroupMesh(qGM)
        :Inputs:
            *opts* :class:`pyCart.options.Options`
                Options interface
            *qGM*: :class:`bool`
                True all cases in a group use the same (starting) mesh
        :Versions:
            * 2014-10-06 ``@ddalle``: First version
        """
        self['Trajectory']['GroupMesh'] = qGM
        
    # Get the umask
    def get_umask(self):
        """Get the current file permissions mask
        
        The default value is the read from the system
        
        :Call:
            >>> umask = opts.get_umask(umask=None)
        :Inputs:
            *opts* :class:`pyCart.options.Options`
                Options interface
        :Outputs:
            *umask*: :class:`oct`
                File permissions mask
        :Versions:
            * 2015-09-27 ``@ddalle``: First version
        """
        # Read the option.
        umask = self.get('umask')
        # Check for string
        if type(umask).__name__ in ['unicode', 'str']:
            # Convert to oct
            umask = eval('0o' + umask)
        # Check if we need to use the default.
        if umask is None:
            # Get the value.
            umask = os.popen('umask', 'r', 1).read()
            # Convert to value.
            umask = eval('0o' + umask.strip())
        # Output
        return umask
        
    # Get the directory permissions to use
    def get_dmask(self):
        """Get the permissions to assign to new folders
        
        :Call:
            >>> dmask = opts.get_dmask()
        :Inputs:
            *opts* :class:`pyCart.options.Options`
                Options interface
        :Outputs:
            *umask*: :class:`int`
                File permissions mask
        :Versions:
            * 2015-09-27 ``@ddalle``: First version
        """
        # Get the umask
        umask = self.get_umask()
        # Subtract UMASK from full open permissions
        return 0o0777 - umask
        
    # Apply the umask
    def apply_umask(self):
        """Apply the permissions filter
        
        :Call:
            >>> opts.apply_umask()
        :Inputs:
            *opts* :class:`pyCart.options.Options`
                Options interface
        :Versions:
            * 2015-09-27 ``@ddalle``: First version
        """
        os.umask(self.get_umask())
   # >
    
    
    # ===================
    # Overall run control
    # ===================
   # <
   
    # Get number of inputs
    def get_nSeq(self):
        self._RunControl()
        return self['RunControl'].get_nSeq()
    # Copy documentation
    get_nSeq.__doc__ = RunControl.get_nSeq.__doc__
    
    # Get number of iterations
    def get_nIter(self, i=None):
        self._RunControl()
        return self['RunControl'].get_nIter(i)
        
    # Set number of iterations
    def set_nIter(self, nIter=rc0('nIter'), i=None):
        self._RunControl()
        self['RunControl'].set_nIter(nIter, i)
    
    # Get input sequence
    def get_PhaseSequence(self, i=None):
        self._RunControl()
        return self['RunControl'].get_PhaseSequence(i)
        
    # Set input sequence
    def set_PhaseSequence(self, PhaseSeq=rc0('PhaseSequence'), i=None):
        self._RunControl()
        self['RunControl'].set_PhaseSequence(PhaseSeq, i)
        
    # Get iteration break points
    def get_PhaseIters(self, i=None):
        self._RunControl()
        return self['RunControl'].get_PhaseIters(i)
        
    # Set Iteration break points
    def set_PhaseIters(self, PhaseIters=rc0('PhaseIters'), i=None):
        self._RunControl()
        return self['RunControl'].set_PhaseIters(PhaseIters, i)
        
    # Get environment variable(s)
    def get_Environ(self, i=None):
        self._RunControl()
        return self['RunControl'].get_Environ(i)
    
    # Set environment variable
    def set_Environ(self, key, val, i=None):
        self._RunControl()
        self['RunControl'].set_Environ(key, val, i)
        
    # Get ulimit parameter
    def get_ulimit(self, u='s', i=None):
        self._RunControl()
        return self['RunControl'].get_ulimit(u, i)
        
    # Set ulimit parameter
    def set_ulimit(self, u, l, i=None):
        self._RunControl()
        self['RunControl'].set_ulimit(u, l, i)
        
    # Get MPI status
    def get_MPI(self, i=None):
        self._RunControl()
        return self['RunControl'].get_MPI(i)
        
    # Set MPI status
    def set_MPI(self, MPI=rc0('MPI'), i=None):
        self._RunControl()
        self['RunControl'].set_MPI(MPI, i)
        
    # Get the number of threads for RunControl
    def get_nProc(self, i=None):
        self._RunControl()
        return self['RunControl'].get_nProc(i)
        
    # Set the number of threads for RunControl
    def set_nProc(self, nProc=rc0('nProc'), i=None):
        self._RunControl()
        self['RunControl'].set_nProc(nProc, i)
        
    # Get the MPI system command
    def get_mpicmd(self, i=None):
        self._RunControl()
        return self['RunControl'].get_mpicmd(i)
        
    # Set the MPI system command
    def set_mpicmd(self, mpicmd=rc0('mpicmd'), i=None):
        self._RunControl()
        self['RunControl'].set_mpicmd(mpicmd, i)
        
    # Get the submittable/nonsubmittalbe status
    def get_qsub(self, i=None):
        self._RunControl()
        return self['RunControl'].get_qsub(i)
        
    # Set the submittable/nonsubmittalbe status
    def set_qsub(self, qsub=rc0('qsub'), i=None):
        self._RunControl()
        self['RunControl'].set_qsub(qsub, i)
        
    # Get the resubmittable/nonresubmittalbe status
    def get_Resubmit(self, i=None):
        self._RunControl()
        return self['RunControl'].get_Resubmit(i)
        
    # Set the resubmittable/nonresubmittalbe status
    def set_Resubmit(self, resub=rc0('Resubmit'), i=None):
        self._RunControl()
        self['RunControl'].set_Resubmit(resub, i)
        
    # Get the continuance setting for repeated inputs
    def get_Continue(self, i=None):
        self._RunControl()
        return self['RunControl'].get_Continue(i)
        
    # Set the continuance setting for repeated inputs
    def set_Continue(self, cont=rc0('Continue'), i=None):
        self._RunControl()
        self['RunControl'].set_Continue(cont, i)
        
    # Copy over the documentation.
    for k in ['nIter', 'PhaseSequence', 'PhaseIters', 'Environ', 'ulimit',
            'MPI', 'nProc', 'mpicmd', 'qsub', 'Resubmit', 'Continue']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(RunControl,'get_'+k).__doc__
        eval('set_'+k).__doc__ = getattr(RunControl,'set_'+k).__doc__
   # >
   
        
    # ============
    # PBS settings
    # ============
   # <
    
    # Get number of unique PBS scripts
    def get_nPBS(self):
        self._PBS()
        return self['PBS'].get_nPBS()
    get_nPBS.__doc__ = PBS.get_nPBS.__doc__
    
    # Get PBS *join* setting
    def get_PBS_j(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_j(i)
        
    # Set PBS *join* setting
    def set_PBS_j(self, j=rc0('PBS_j'), i=None):
        self._PBS()
        self['PBS'].set_PBS_j(j, i)
    
    # Get PBS *rerun* setting
    def get_PBS_r(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_r(i)
        
    # Set PBS *rerun* setting
    def set_PBS_r(self, r=rc0('PBS_r'), i=None):
        self._PBS()
        self['PBS'].set_PBS_r(r, i)
    
    # Get PBS shell setting
    def get_PBS_S(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_S(i)
        
    # Set PBS shell setting
    def set_PBS_S(self, S=rc0('PBS_S'), i=None):
        self._PBS()
        self['PBS'].set_PBS_S(S, i)
    
    # Get PBS nNodes setting
    def get_PBS_select(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_select(i)
        
    # Set PBS nNodes setting
    def set_PBS_select(self, n=rc0('PBS_select'), i=None):
        self._PBS()
        self['PBS'].set_PBS_select(n, i)
    
    # Get PBS CPUS/node setting
    def get_PBS_ncpus(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_ncpus(i)
        
    # Set PBS CPUs/node setting
    def set_PBS_ncpus(self, n=rc0('PBS_ncpus'), i=None):
        self._PBS()
        self['PBS'].set_PBS_ncpus(n, i)
    
    # Get PBS MPI procs/node setting
    def get_PBS_mpiprocs(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_mpiprocs(i)
        
    # Set PBS *rerun* setting
    def set_PBS_mpiprocs(self, n=rc0('PBS_mpiprocs'), i=None):
        self._PBS()
        self['PBS'].set_PBS_mpiprocs(n, i)
    
    # Get PBS model or arch setting
    def get_PBS_model(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_model(i)
        
    # Set PBS model or arch setting
    def set_PBS_model(self, s=rc0('PBS_model'), i=None):
        self._PBS()
        self['PBS'].set_PBS_model(s, i)
    
    # Get PBS group setting
    def get_PBS_W(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_W(i)
        
    # Set PBS group setting
    def set_PBS_W(self, W=rc0('PBS_W'), i=None):
        self._PBS()
        self['PBS'].set_PBS_W(W, i)
    
    # Get PBS queue setting
    def get_PBS_q(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_q(i)
        
    # Set PBS queue setting
    def set_PBS_q(self, q=rc0('PBS_q'), i=None):
        self._PBS()
        self['PBS'].set_PBS_q(q, i)
    
    # Get PBS walltime setting
    def get_PBS_walltime(self, i=None):
        self._PBS()
        return self['PBS'].get_PBS_walltime(i)
        
    # Set PBS walltime setting
    def set_PBS_walltime(self, t=rc0('PBS_walltime'), i=None):
        self._PBS()
        self['PBS'].set_PBS_walltime(t, i)
        
    # Copy over the documentation.
    for k in ['PBS_j', 'PBS_r', 'PBS_S', 'PBS_select', 'PBS_mpiprocs',
            'PBS_ncpus', 'PBS_model', 'PBS_W', 'PBS_q', 'PBS_walltime']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(PBS,'get_'+k).__doc__
        eval('set_'+k).__doc__ = getattr(PBS,'set_'+k).__doc__
   # > 
   
    
    # =============
    # Configuration
    # =============
   #<
    
    # Get components
    def get_ConfigComponents(self, i=None):
        self._Config()
        return self['Config'].get_ConfigComponents(i)
        
    # Set components
    def set_ConfigComponents(self, comps, i=None):
        self._Config()
        self['Config'].set_ConfigComponents(comps, i)
        
    # Get config file name
    def get_ConfigFile(self):
        self._Config()
        return self['Config'].get_ConfigFile()
        
    # Set config file name
    def set_ConfigFile(self, fname=rc0('ConfigFile')):
        self._Config()
        self['Config'].set_ConfigFile(fname)
    
    # Get reference area
    def get_RefArea(self, comp=None):
        self._Config()
        return self['Config'].get_RefArea(comp)
        
    # Set config file name
    def set_RefArea(self, A=rc0('RefArea'), comp=None):
        self._Config()
        self['Config'].set_RefArea(A, comp)
    
    # Get reference length
    def get_RefLength(self, comp=None):
        self._Config()
        return self['Config'].get_RefLength(comp)
        
    # Set config file name
    def set_RefLength(self, L=rc0('RefLength'), comp=None):
        self._Config()
        self['Config'].set_RefLength(L, comp)
    
    # Get moment reference point
    def get_RefPoint(self, comp=None):
        self._Config()
        return self['Config'].get_RefPoint(comp)
        
    # Set moment reference point
    def set_RefPoint(self, x=rc0('RefPoint'), comp=None):
        self._Config()
        self['Config'].set_RefPoint(x, comp)
        
    # Get valid point
    def get_Point(self, name=None):
        self._Config()
        return self['Config'].get_Point(name)
        
    # Set valid point
    def set_Point(self, x=rc0('RefPoint'), name=None):
        self._Config()
        self['Config'].set_Point(x, name)
        
    # Expand point/dictionary of points
    def expand_Point(self, x):
        self._Config()
        return self['Config'].expand_Point(x)
    expand_Point.__doc__ = Config.expand_Point.__doc__
        
    # Copy over the documentation.
    for k in ['ConfigComponents', 'ConfigFile', 
    'RefArea', 'RefLength', 'RefPoint', 'Point']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(Config,'get_'+k).__doc__
        eval('set_'+k).__doc__ = getattr(Config,'set_'+k).__doc__
   # >
   
    
    # =================
    # Folder management
    # =================
   # <
    
    # Get the archive folder
    def get_ArchiveFolder(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveFolder()
        
    # Set the archive folder
    def set_ArchiveFolder(self, fdir=rc0('ArchiveFolder')):
        self._RunControl()
        self['RunControl'].set_ArchiveFolder(fdir)
        
    # Get the archive format
    def get_ArchiveFormat(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveFormat()
        
    # Set the archive format
    def set_ArchiveFormat(self, fmt=rc0('ArchiveFormat')):
        self._RunControl()
        self['RunControl'].set_ArchiveFormat(fmt)
        
    # Get the archive type
    def get_ArchiveType(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveType()
        
    # Set the archive type
    def set_ArchiveType(self, atype=rc0('ArchiveType')):
        self._RunControl()
        self['RunControl'].set_ArchiveType(atype)
        
    # Get the archive type
    def get_ArchiveTemplate(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveTemplate()
        
    # Set the archive type
    def set_ArchiveTemplate(self, atype=rc0('ArchiveTemplate')):
        self._RunControl()
        self['RunControl'].set_ArchiveTemplate(atype)
        
    # Get the archive action
    def get_ArchiveAction(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveAction()
        
    # Set the archive action
    def set_ArchiveAction(self, fcmd=rc0('ArchiveAction')):
        self._RunControl()
        self['RunControl'].set_ArchiveAction(fcmd)
        
    # Get the remote copy command
    def get_RemoteCopy(self):
        self._RunControl()
        return self['RunControl'].get_RemoteCopy()
        
    # Set the remote copy command
    def set_RemoteCopy(self, fcmd=rc0('RemoteCopy')):
        self._RunControl()
        self['RunControl'].set_RemoteCopy(fcmd)
        
    # Copy over the documentation.
    for k in ['ArchiveFolder', 'ArchiveFormat', 'ArchiveAction', 'ArchiveType',
            'RemoteCopy', 'ArchiveTemplate']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(RunControl,'get_'+k).__doc__
        eval('set_'+k).__doc__ = getattr(RunControl,'set_'+k).__doc__
        
    # Get the extension
    def get_ArchiveExtension(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveExtension()
        
    # Get the archive command
    def get_ArchiveCmd(self):
        self._RunControl()
        return self['RunControl'].get_ArchiveCmd()
        
    # Get the unarchive command
    def get_UnarchiveCmd(self):
        self._RunControl()
        return self['RunControl'].get_UnarchiveCmd()
        
    # One-way commands
    for k in ['ArchiveExtension', 'ArchiveCmd', 'UnarchiveCmd']:
        # Copy documentation
        eval('get_'+k).__doc__ = getattr(RunControl,'get_'+k).__doc__
        
    # Get the list of files to delete a priori 
    def get_ArchivePreDeleteFiles(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePreDeleteFiles()
    
    # Add to list of files to delete a priori
    def add_ArchivePreDeleteFiles(self, fpre):
        self._RunControl()
        self['RunControl'].add_ArchivePreDeleteFiles(fpre)
        
    # Get the list of folders to delete a priori
    def get_ArchivePreDeleteDirs(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePreDeleteDirs()
    
    # Add to list of folders to delete a priori
    def add_ArchivePreDeleteDirs(self, fpre):
        self._RunControl()
        self['RunControl'].add_ArchivePreDeleteDirs(fpre)
        
    # Get the list of groups to tar a priori
    def get_ArchivePreArchiveGroups(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePreArchiveGroups()
        
    # Add to list of groups to tar a priori
    def add_ArchivePreArchiveGroups(self, fpre):
        self._RunControl()
        self['RunControl'].add_ArchivePreArchiveGroups(fpre)
        
    # Get the list of folders to tar a priori
    def get_ArchivePreArchiveDirs(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePreArchiveDirs()
        
    # Add to list of folders to tar apriori
    def add_ArchivePreArchiveDirs(self, fpre):
        self._RunControl()
        self['RunControl'].add_ArchivePreArchiveDirs(fpre)
    
    # Files to keep only *n*
    def get_ArchivePreUpdateFiles(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePreUpdateFiles()
        
    # Files to keep only *n*
    def add_ArchivePreUpdateFiles(self, fpre):
        self._RunControl()
        self['RunControl'].add_ArchivePreUpdateFiles(fpre)
        
    # Get the list of files to delete a posteriori 
    def get_ArchivePostDeleteFiles(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePostDeleteFiles()
    
    # Add to list of files to delete a posteriori
    def add_ArchivePostDeleteFiles(self, fpost):
        self._RunControl()
        self['RunControl'].add_ArchivePostDeleteFiles(fpost)
        
    # Get the list of folders to delete a posteriori
    def get_ArchivePostDeleteDirs(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePostDeleteDirs()
    
    # Add to list of folders to delete a posteriori
    def add_ArchivePostDeleteDirs(self, fpost):
        self._RunControl()
        self['RunControl'].add_ArchivePostDeleteDirs(fpost)
        
    # Get the list of groups to tar a posteriori
    def get_ArchivePostArchiveGroups(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePostArchiveGroups()
        
    # Add to list of groups to tar a posteriori
    def add_ArchivePostArchiveGroups(self, fpost):
        self._RunControl()
        self['RunControl'].add_ArchivePostArchiveGroups(fpost)
        
    # Get the list of folders to tar a posteriori
    def get_ArchivePostArchiveDirs(self):
        self._RunControl()
        return self['RunControl'].get_ArvhiePostArchiveDirs()
        
    # Add to list of folders to tar aposteriori
    def add_ArchivePostArchiveDirs(self, fpost):
        self._RunControl()
        self['RunControl'].add_ArchivePostArchiveDirs(fpost)
    
    # Files to keep only *n*
    def get_ArchivePostUpdateFiles(self):
        self._RunControl()
        return self['RunControl'].get_ArchivePostUpdateFiles()
        
    # Files to keep only *n*
    def add_ArchivePostUpdateFiles(self, fpost):
        self._RunControl()
        self['RunControl'].add_ArchivePostUpdateFiles(fpost)
        
     # Copy over the documentation.
    for k in [
            'ArchivePreDeleteFiles',    'ArchivePreDeleteDirs',
            'ArchivePreArchiveGroups',  'ArchivePreArchiveDirs',
            'ArchivePreUpdateFiles',
            'ArchivePostDeleteFiles',   'ArchivePostDeleteDirs',
            'ArchivePostArchiveGroups', 'ArchivePostArchiveDirs',
            'ArchivePostUpdateFiles'
        ]:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(RunControl,'get_'+k).__doc__
        eval('add_'+k).__doc__ = getattr(RunControl,'add_'+k).__doc__
   # >
   
    
    # ========
    # Plotting
    # ========
   # <
   
    # Get list of components to plot
    def get_PlotComponents(self):
        self._DataBook()
        return self['DataBook'].get_PlotComponents()
    get_PlotComponents.__doc__ = DataBook.get_PlotComponents.__doc__
        
    # Set list of components to plot
    def set_PlotComponents(self, comps=['entire']):
        self._DataBook()
        self['DataBook'].set_PlotComponents(comps)
    set_PlotComponents.__doc__ = DataBook.set_PlotComponents.__doc__
        
    # Add to list of components to plot
    def add_PlotComponents(self, comp):
        self._DataBook()
        self['DataBook'].add_PlotComponents(comp)
    add_PlotComponents.__doc__ = DataBook.add_PlotComponents.__doc__
    
    # Get the list of coefficients to plot.
    def get_PlotCoeffs(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_PlotCoeffs(comp)
        
    # Get the number of iterations to plot
    def get_nPlotIter(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nPlotIter(comp)
    
    # Get the last iteration to plot
    def get_nPlotLast(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nPlotLast(comp)
        
    # Get the first iteration to plot
    def get_nPlotFirst(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nPlotFirst(comp)
        
    # Get the number of iterations to use for averaging
    def get_nAverage(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nAverage(comp)
        
    # Get number of rows to plot
    def get_nPlotRows(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nPlotRows(comp)
        
    # Get number of columns to plot
    def get_nPlotCols(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nPlotCols(comp)
        
    # Get the plot restriction
    def get_PlotRestriction(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_PlotRestriction(comp)
        
    # Get the delta for a given component and coefficient
    def get_PlotDelta(self, coeff, comp=None):
        self._DataBook()
        return self['DataBook'].get_PlotDelta(coeff, comp)
        
    # Get the plot figure width
    def get_PlotFigWidth(self):
        self._DataBook()
        return self['DataBook'].get_PlotFigWidth()
        
    # Get the plot figure height
    def get_PlotFigHeight(self):
        self._DataBook()
        return self['DataBook'].get_PlotFigHeight()
        
    # Copy over the documentation.
    for k in [
            'PlotCoeffs', 'PlotComponents',
            'PlotCoeffs', 'nPlotIter', 'nAverage', 'nPlotRows',
            'nPlotLast', 'nPlotFirst', 'PlotFigWidth', 'PlotFigHeight',
            'nPlotCols', 'PlotRestriction', 'PlotDelta']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(DataBook,'get_'+k).__doc__
   # >
    
    
    # =========
    # Data book
    # =========
   # <
    
    # Get list of components.
    def get_DataBookComponents(self):
        self._DataBook()
        return self['DataBook'].get_DataBookComponents()
        
    # Get list of line load components.
    def get_DataBookLineLoads(self):
        self._DataBook()
        return self['DataBook'].get_DataBookLineLoads()
        
    # Get component type
    def get_DataBookType(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookType(comp)
        
    # Get component subcomponents
    def get_DataBookPoints(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookPoints(comp)
    
    # Get list of coefficients for a specific component
    def get_DataBookCoeffs(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookCoeffs(comp)
        
    # Get data book targets for a specific coefficient
    def get_CompTargets(self, comp):
        self._DataBook()
        return self['DataBook'].get_CompTargets(comp)
        
    # Get data book transformations for a specific component
    def get_DataBookTransformations(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookTransformations(comp)
        
    # Get data book columns for a specific coefficient
    def get_DataBookCols(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookCols(comp)
        
    # Get data book data columns for a specific coefficient
    def get_DataBookDataCols(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookDataCols(comp)
        
    # Get data book target columns for a specific coefficient
    def get_DataBookTargetCols(self, comp):
        self._DataBook()
        return self['DataBook'].get_DataBookTargetCols(comp)
    
    # Get list of targets
    def get_DataBookTargets(self):
        self._DataBook()
        return self['DataBook'].get_DataBookTargets()
        
    # Get target options
    def get_DataBookTargetByName(self, targ):
        self._DataBook()
        return self['DataBook'].get_DataBookTargetByName(targ)
        
    # Get components for a line load
    def get_LineLoadComponents(self, comp):
        self._DataBook()
        return self['DataBook'].get_LineLoadComponents(comp)
        
    # Get number of cuts for a line load group
    def get_LineLoad_nCut(self, comp):
        self._DataBook()
        return self['DataBook'].get_LineLoad_nCut(comp)
    
    # Group/points
    def get_DBGroupPoints(self, name):
        self._DataBook()
        return self['DataBook'].get_DBGroupPoints(name)
    
    # Copy over the documentation.
    for k in ['DataBookComponents', 'DataBookLineLoads',
            'DataBookType', 'DataBookPoints', 'DBGroupPoints',
            'DataBookCoeffs', 'DataBookTargets',
            'DataBookCols', 'CompTargets', 'DataBookTransformations',
            'DataBookDataCols', 'DataBookTargetCols', 'DataBookTargetByName',
            'LineLoadComponents', 'LineLoad_nCut',
    ]:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(DataBook,'get_'+k).__doc__
    
    # Number of iterations used for statistics
    def get_nStats(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nStats(comp)
    
    # Set number of iterations
    def set_nStats(self, nStats=rc0('db_stats')):
        self._DataBook()
        self['DataBook'].set_nStats(nStats)
    
    # Min iteration used for statistics
    def get_nMin(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nMin(comp)
    
    # Min iterationused for statistics
    def set_nMin(self, nMin=rc0('db_min')):
        self._DataBook()
        self['DataBook'].set_nMin(nMin)
    
    # Max number of iterations used for statistics
    def get_nMaxStats(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nMaxStats(comp)
    
    # Max number of iterations used for statistics
    def set_nMaxStats(self, nMax=rc0('db_max')):
        self._DataBook()
        self['DataBook'].set_nMaxStats(nMax)
    
    # Max iter for statistics
    def get_nLastStats(self, comp=None):
        self._DataBook()
        return self['DataBook'].get_nLastStats(comp)
    
    # Max iter for statistics
    def set_nLastStats(self, nLast=None):
        self._DataBook()
        self['DataBook'].set_nLastStats(nLast)
        
    # Data book directory
    def get_DataBookDir(self):
        self._DataBook()
        return self['DataBook'].get_DataBookDir()
    
    # Set data book directory
    def set_DataBookDir(self, fdir=rc0('db_dir')):
        self._DataBook()
        self['DataBook'].set_DataBookDir(fdir)
        
    # Data book file delimiter
    def get_Delimiter(self):
        self._DataBook()
        return self['DataBook'].get_Delimiter()
        
    # Set data book file delimiter
    def set_Delimiter(self, delim=rc0('Delimiter')):
        self._DataBook()
        self['DataBook'].set_Delimiter(delim)
        
    # Key to use for sorting the data book
    def get_SortKey(self):
        self._DataBook()
        return self['DataBook'].get_SortKey()
    
    # Set key to use for sorting the data book
    def set_SortKey(self, key):
        self._DataBook()
        self['DataBook'].set_SortKey(key)
        
    # Copy over the documentation.
    for k in ['nStats', 'nMin', 'nMaxStats', 'nLastStats', 
            'DataBookDir', 'Delimiter', 'SortKey']:
        # Get the documentation for the "get" and "set" functions
        eval('get_'+k).__doc__ = getattr(DataBook,'get_'+k).__doc__
        eval('set_'+k).__doc__ = getattr(DataBook,'set_'+k).__doc__
   # >
    
    # =======
    # Reports
    # =======
   # <
    
    # Get report list
    def get_ReportList(self):
        self._Report()
        return self['Report'].get_ReportList()
        
    # Get sweep list
    def get_SweepList(self):
        self._Report()
        return self['Report'].get_SweepList()
        
    # Get figure list
    def get_FigList(self):
        self._Report()
        return self['Report'].get_FigList()
    
    # Get subfigure list
    def get_SubfigList(self):
        self._Report()
        return self['Report'].get_SubfigList()
        
    # Get options for a single report
    def get_Report(self, rep):
        self._Report()
        return self['Report'].get_Report(rep)
        
    # Get options for a single figure
    def get_Figure(self, fig):
        self._Report()
        return self['Report'].get_Figure(fig)
        
    # Get options for a single subfigure
    def get_Subfigure(self, sfig):
        self._Report()
        return self['Report'].get_Subfigure(sfig)
        
    # Get options for a single sweep
    def get_Sweep(self, fswp):
        self._Report()
        return self['Report'].get_Sweep(fswp)
        
    # Get list of sweeps in a report
    def get_ReportSweepList(self, rep):
        self._Report()
        return self['Report'].get_ReportSweepList(rep)
        
    # Get list of figures in a report
    def get_ReportFigList(self, rep):
        self._Report()
        return self['Report'].get_ReportFigList(rep)
        
    # Get list of figures in a report
    def get_ReportErrorFigList(self, rep):
        self._Report()
        return self['Report'].get_ReportErrorFigList(rep)
        
    # Get list of figures in a report
    def get_ReportZeroFigList(self, rep):
        self._Report()
        return self['Report'].get_ReportZeroFigList(rep)
        
    # Get list of figures in a sweep
    def get_SweepFigList(self, rep):
        self._Report()
        return self['Report'].get_SweepFigList(rep)
        
    # Get title string for a report
    def get_ReportTitle(self, rep):
        self._Report()
        return self['Report'].get_ReportTitle(rep)
        
    # Get subtitle string for a report
    def get_ReportSubtitle(self, rep):
        self._Report()
        return self['Report'].get_ReportSubtitle(rep)
        
    # Get distribution limitation for a report
    def get_ReportRestriction(self, rep):
        self._Report()
        return self['Report'].get_ReportRestriction(rep)
    
    # Get logo for a report
    def get_ReportLogo(self, rep):
        self._Report()
        return self['Report'].get_ReportLogo(rep)
        
    # Get frontispiece file name for a report
    def get_ReportFrontispiece(self, rep):
        self._Report()
        return self['Report'].get_ReportFrontispiece(rep)
        
    # Get author string for a report
    def get_ReportAuthor(self, rep):
        self._Report()
        return self['Report'].get_ReportAuthor(rep)
        
    # Get author affiliation for a report
    def get_ReportAffiliation(self, rep):
        self._Report()
        return self['Report'].get_ReportAffiliation(rep)
        
    # Get archive option
    def get_ReportArchive(self):
        self._Report()
        return self['Report'].get_ReportArchive()
        
    # Get the list of subfigures in a figure
    def get_FigSubfigList(self, fig):
        self._Report()
        return self['Report'].get_FigSubfigList(fig)
        
    # Get the figure alignment
    def get_FigAlignment(self, fig):
        self._Report()
        return self['Report'].get_FigAlignment(fig)
        
    # Get the figure header
    def get_FigHeader(self, fig):
        self._Report()
        return self['Report'].get_FigHeader(fig)
    
    # Get the subfigure type
    def get_SubfigType(self, sfig):
        self._Report()
        return self['Report'].get_SubfigType(sfig)
        
    # Get the subfigure base type
    def get_SubfigBaseType(self, sfig):
        self._Report()
        return self['Report'].get_SubfigBaseType(sfig)
        
    # Get an option for a subfigure
    def get_SubfigOpt(self, sfig, opt, i=None):
        self._Report()
        return self['Report'].get_SubfigOpt(sfig, opt, i=i)
        
    # Get an option for a subfigure
    def get_SubfigPlotOpt(self, sfig, opt, i=None):
        self._Report()
        return self['Report'].get_SubfigPlotOpt(sfig, opt, i=i)
        
    # Get an option for a sweep
    def get_SweepOpt(self, fswp, opt):
        self._Report()
        return self['Report'].get_SweepOpt(fswp, opt)
    
    # Copy over the documentation
    for k in ['ReportList', 'SweepList', 'FigList', 'SubfigList',
            'Figure', 'Subfigure', 'Report', 'Sweep',
            'ReportFigList', 'ReportErrorFigList', 'ReportZeroFigList', 
            'ReportSweepList', 'SweepFigList',
            'ReportTitle', 'ReportSubtitle', 'ReportAuthor',
            'ReportAffiliation', 'ReportFrontispiece',
            'ReportRestriction', 'ReportLogo',  'ReportArchive',
            'FigSubfigList', 'FigAlignment', 'FigHeader',
            'SubfigType', 'SubfigBaseType', 'SubfigOpt', 'SweepOpt',
            'SubfigPlotOpt'
    ]:
        # Get the documentation from the submodule
        eval('get_'+k).__doc__ = getattr(Report,'get_'+k).__doc__
   # >
   
# class Options

