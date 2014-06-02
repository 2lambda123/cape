

# Required modules
# Numerics
import numpy as np
# File system and operating system management
import os

# Triangulation class
class Tri:
    # Initialization method
    def __init__(self, fname=None, uh3d=None,
        nNode=None, Nodes=None, nTri=None, Tris=None, iComp=None):
        """
        pyCart triangulation class
        
        This class provides an interface for a basic triangulation without
        surface data.  It can be created either by reading an ASCII file or
        specifying the data directly.
        
        :Call:
            >>> tri = pyCart.Tri(fname=None)
            >>> tri = pyCart.Tri(Nodes=Nodes, Tris=Tris, iComp=iComp)
            
        :Inputs:
            *fname*: :class:`str`
                Name of triangulation file to read (Cart3D format)
            *uh3d*: :class:`str`
                Name of triangulation file (UH3D format)
            *nNode*: :class:`int`
                Number of nodes in triangulation
            *Nodes*: :class:`numpy.array(dtype=float)`, (*nNode*, 3)
                Matrix of *x,y,z*-coordinates of each node
            *nTri*: :class:`int`
                Number of triangles in triangulation
            *Tris*: :class:`numpy.array(dtype=int)`, (*nTri*, 3)
                Indices of triangle vertex nodes
            *iComp*: :class:`numpy.array(dtype=int)`, (*nTri*)
                Component number for each triangle
                
        :Data members:
            *nNode*: :class:`int`
                Number of nodes in triangulation
            *Nodes*: :class:`numpy.array(dtype=float)`, (*nNode*, 3)
                Matrix of *x,y,z*-coordinates of each node
            *nTri*: :class:`int`
                Number of triangles in triangulation
            *Tris*: :class:`numpy.array(dtype=int)`, (*nTri*, 3)
                Indices of triangle vertex nodes
            *iComp*: :class:`numpy.array(dtype=int)`, (*nTri*)
                Component number for each triangle
        
        When no component numbers are specified, the object created will label
        all triangles ``1``.
        """
        # Versions:
        #  2014.05.23 @ddalle  : First version
        #  2014.06.02 @ddalle  : Added UH3D reading capability
        
        # Check if file is specified.
        if fname is not None:
            # Read from file.
            self.Read(fname)
        
        elif uh3d is not None:
            # Read from the other format.
            self.ReadUH3D(uh3d)
            
        else:
            # Process inputs.
            # Check counts.
            if nNode is None:
                # Get dimensions if possible.
                if Nodes is not None:
                    # Use the shape.
                    nNode = Nodes.shape[0]
                else:
                    # No nodes
                    nNode = 0
            # Check counts.
            if nTri is None:
                # Get dimensions if possible.
                if Tris is not None:
                    # Use the shape.
                    nTri = Tris.shape[0]
                else:
                    # No nodes
                    nTri = 0
            # Save the components.
            self.nNode = nNode
            self.Nodes = Nodes
            self.nTri = nTri
            self.Tris = Tris
            self.iComp = iComp
            
        # End
        return None
        
        
    # Function to read a .tri file
    def Read(self, fname):
        """
        Read a triangulation file (from '*.tri')
        
        :Call:
            >>> tri.Read(fname)
            
        :Inputs:
            *tri*: :class:`pyCart.tri.Tri`
                Triangulation instance
            *fname*: :class:`str`
                Name of triangulation file to read
        
        :Outputs:
            ``None``
        """
        # Versions:
        #  2014.06.02 @ddalle  : Split from initialization method.
        
        # Open the file
        fid = open(fname, 'r')
        # Read the first line.
        line = fid.readline()
        # Process the line into two integers.
        nNode, nTri = (int(v) for v in line.strip().split())
        # Save the statistics.
        self.nNode = nNode
        self.nTri = nTri
        
        # Read the nodes.
        Nodes = np.fromfile(fid, dtype=float, count=nNode*3, sep=" ")
        # Reshape into a matrix.
        self.Nodes = Nodes.reshape((nNode,3))
        
        # Read the Tris
        Tris = np.fromfile(fid, dtype=int, count=nTri*3, sep=" ")
        # Reshape into a matrix.
        self.Tris = Tris.reshape((nTri,3))
        
        # Check for end of file.
        if fid.tell() == os.fstat(fid.fileno()).st_size:
            # Use default component ids.
            self.iComp = None
        else:
            # Read from file.
            self.iComp = np.fromfile(fid, dtype=int, count=nTri, sep=" ")
        # Close the file.
        fid.close()
        
    
    # Function to write a triangulation to file.
    def Write(self, fname):
        """
        Write a triangulation to file
        
        :Call:
            >>> tri.Write(fname)
        
        :Inputs:
            *tri*: :class:`pyCart.tri.Tri`
                Triangulation instance to be translated
            *fname*: :class:`str`
                Name of triangulation file to create
                
        :Outputs:
            ``None``
            
        :Examples:
            >>> tri = pyCart.ReadTri('bJet.i.tri')
            >>> tri.Write('bjet2.tri')
        """
        # Versions:
        #  2014.05.23 @ddalle  : First version
        
        # Open the file for creation.
        fid = open(fname, 'w')
        # Write the number of nodes and triangles.
        fid.write('%i  %i\n' % (self.nNode, self.nTri))
        # Write the nodal coordinates, tris, and component ids.
        np.savetxt(fid, self.Nodes, fmt="%+15.8e", delimiter=' ')
        np.savetxt(fid, self.Tris,  fmt="%i",      delimiter=' ')
        np.savetxt(fid, self.iComp, fmt="%i",      delimiter=' ')
        # Close the file.
        fid.close()
        # End
        return None
        
        
    # Read from a .uh3d file.
    def ReadUH3D(self, fname):
        """
        Read a triangulation file (from '*.uh3d')
        
        :Call:
            >>> tri.ReadUH3D(fname)
            
        :Inputs:
            *tri*: :class:`pyCart.tri.Tri`
                Triangulation instance
            *fname*: :class:`str`
                Name of triangulation file to read
        
        :Outputs:
            ``None``
        """
        # Versions:
        #  2014.06.02 @ddalle  : First version
        
        # Open the file
        fid = open(fname, 'r')
        # Read the first line and discard.
        line = fid.readline()
        # Read the second line and split by commas.
        data = fid.readline().split(',')
        # Process the number of nodes and tris
        nNode = int(data[0])
        nTri = int(data[2])
        # Save the statistics.
        self.nNode = nNode
        self.nTri = nTri
        
        # Initialize the nodes.
        Nodes = np.zeros((nNode, 3))
        # Loop through the nodes.
        for i in range(nNode):
            # Read the next line.
            Nodes[i] = np.fromfile(fid, dtype=float, count=4, sep=",")[1:4]
        # Save
        self.Nodes = Nodes
        
        # Initialize the Tris and component numbers
        Tris = np.zeros((nTri, 3))
        iComp = np.ones(nTri)
        # Loop through the lines.
        for i in range(nTri):
            # Read the line.
            d = np.fromfile(fid, dtype=int, count=5, sep=",")
            # Save the indices.
            Tris[i] = d[1:4]
            # Save the component number.
            iComp[i] = d[4]
        # Save.
        self.Tris = Tris
        self.iComp = iComp
        
        # Close the file.
        fid.close()
        
    
    # Function to translate the triangulation
    def Translate(self, dx=None, dy=None, dz=None):
        """
        Translate the nodes of a triangulation object.
        
        :Call:
            >>> tri.Translate(dR)
            >>> tri.Translate(dx, dy, dz)
            >>> tri.Translate(dy=dy)
        
        :Inputs:
            *tri*: :class:`pyCart.tri.Tri`
                Triangulation instance to be translated
            *dR*: :class:`numpy.array` or `list`
                List of three coordinates to use for translation
            *dx*: :class:`float`
                *x*-coordinate offset
            *dy*: :class:`float`
                *y*-coordinate offset
            *dz*: :class:`float`
                *z*-coordinate offset
        
        :Outputs:
            ``None``
            
        This function translates a triangulation.  The offset coordinates may be
        specified as individual inputs or a single vector of three coordinates.
        """
        # Versions:
        #  2014.05.23 @ddalle  : First version
        
        # Check the first input type.
        if type(dx).__name__ == 'ndarray':
            # Vector
            dy = dx[1]
            dz = dx[2]
            dx = dx[0]
        else:
            # Check for unspecified inputs.
            if dx is None: dx = 0.0
            if dy is None: dy = 0.0
            if dz is None: dz = 0.0
        # Offset each coordinate.
        self.Nodes[:,0] += dx
        self.Nodes[:,1] += dy
        self.Nodes[:,2] += dz
        # End
        return None
        
    # Function to rotate a triangulation about an arbitrary vector
    def Rotate(self, v1, v2, theta):
        """
        Rotate the nodes of a triangulation object.
        
        :Call:
            >>> tri.Rotate(v1, v2, theta)
        
        :Inputs:
            *tri*: :class:`pyCart.tri.Tri`
                Triangulation instance to be rotated
            *v1*: :class:`numpy.ndarray` (*shape*=(3,))
                Start point of rotation vector
            *v2*: :class:`numpy.ndarray` (*shape*=(3,))
                End point of rotation vector
            *theta*: :class:`float`
                Rotation angle in degrees
            
        :Outputs:
            ``None``
        """
        # Versions:
        #  2014.05.27 @ddalle  : First version
        
        # Convert points to NumPy.
        v1 = np.array(v1)
        v2 = np.array(v2)
        # Extract the coordinates and shift origin.
        x = self.Nodes[:,0] - v1[0]
        y = self.Nodes[:,1] - v1[1]
        z = self.Nodes[:,2] - v1[2]
        # Make the rotation vector
        v = (v2-v1) / np.linalg.linalg.norm(v2-v1)
        # Dot product of points with rotation vector
        k1 = v[0]*x + v[1]*y + v[2]*z
        # Trig functions
        c_th = np.cos(theta*np.pi/180.)
        s_th = np.sin(theta*np.pi/180.)
        # Apply Rodrigues' rotation formula to get the rotated coordinates.
        self.Nodes[:,0] = x*c_th+(v[1]*z-v[2]*y)*s_th+v[0]*k1*(1-c_th)+v1[0]
        self.Nodes[:,1] = y*c_th+(v[2]*x-v[0]*z)*s_th+v[1]*k1*(1-c_th)+v1[1]
        self.Nodes[:,2] = z*c_th+(v[0]*y-v[1]*x)*s_th+v[2]*k1*(1-c_th)+v1[2]
        # Return the rotated coordinates.
        return None
        
    # Method that shows the representation of a triangulation
    def __repr__(self):
        """
        Return the string representation of a triangulation.
        
        This looks like ``<pyCart.tri.Tri(nNode=M, nTri=N)>``
        """
        # Versions:
        #  2014.05.27 @ddalle  : First version
        return '<pyCart.tri.Tri(nNode=%i, nTri=%i)>' % (self.nNode, self.nTri)
        
    # String representation is the same
    __str__ = __repr__


# Function to read .tri files
def ReadTri(fname):
    """
    Read a basic triangulation file
    
    :Call:
        >>> tri = pyCart.ReadTri(fname)
        
    :Inputs:
        *fname*: :class:`str`
            Name of `.tri` file to read
    
    :Outputs:
        *tri*: :class:`pyCart.tri.Tri`
            Triangulation instance
    
    :Examples:
        >>> (nNode, Nodes,  = pyCart.ReadTri('bJet.i.tri')
        >>> tri.nNode
        92852
    """
    # Versions:
    #  2014.05.27 @ddalle  : First version
       
    # Create the tri object and return it.
    return Tri(fname)
    
    
# Global function to write a triangulation (just calls tri method)
def WriteTri(fname, tri):
    """
    Write a triangulation instance to file
    
    :Call:
        >>> pyCart.WriteTri(fname, tri)
    
    :Inputs:
        *fname*: :class:`str`
            Name of `.tri` file to read
        *tri*: :class:`pyCart.tri.Tri`
            Triangulation instance
    
    :Ooutputs:
        ``None``
    
    :Examples:
        >>> tri = pyCart.ReadTri('bJet.i.tri')
        >>> pyCart.WriteTri('bjet2.tri', tri)
    """
    # Versions:
    #  2014.05.23 @ddalle  : First version
    
    # Call the triangulation's write method.
    tri.Write(fname)
    return None
    
