import numpy as np
from delft3d.GrdFile import GrdFile
import matplotlib.pyplot as plt


class DepFile(object):
    """
    Read, modify, visualize, export and write Delft3D dep file

    Example
    --------
    >>> dep = DepFile('river.dep')
    """
    def __init__(self, filename):
        self.filename = filename
        self.data = self.load_dep()

    def load_dep(self):
        """Read dep file"""
        with open(self.filename, 'r') as f:
            data = f.readlines()
        dep = list()
        for line in data:
            dep.append([float(i) for i in line.split()])
        dep = np.array(dep)
        dep = np.delete(dep, -1, axis=0)
        dep = np.delete(dep, -1, axis=1)

        return dep

    def plot(self, grd_file):
        """
        Visualize dep file

        Parameters
        ----------
        grd_file : GrdFile
            GrdFile instance of the corresponding grd file.

        Examples
        -------
        >>> grd = GrdFile('river.grd')
        >>> dep = DepFile('river.dep')
        >>> dep.plot(grd)
        """
        if type(grd_file) != GrdFile:
            raise ValueError("Please input an GrdFile class instance")
        if grd_file.header['Coordinate System'] == 'Spherical':
            grd_file.spherical_to_cartesian()
            print("Automatically transform from spherical to cartesian coordinates")
        plt.pcolormesh(grd_file.x, grd_file.y, self.data, cmap='Blues',
                       edgecolor=None, linewidth=0.005)
        plt.axis('equal')
        plt.colorbar()
        plt.show()

    def set_dep(self, data):
        """
        set new dep data
        Parameters
        ----------
        data : ndarray
            New dep data.
        Examples
        -------
        >>> dep = DepFile('river.deo')
        >>> dep_data = np.loadtxt('dep_data.txt')
        >>> dep.set_dep(dep_data)
        """
        self.data = data

    def export(self):
        """
        Export the data to a ndarry in the format of Delft3D dep file.

        Examples
        -------
        >>> dep = DepFile('river.dep')
        >>> dep_file = dep.export()
        >>> dep_file
            ['   1.6929708E-01   2.8992051E-01   5.0572435E-01\\n,
             '  -5.0850775E-02   3.1147481E-01   4.6392793E-01\\n,
             ...]
        """
        dep_data = np.append(self.data, np.full((1, self.data.shape[1]), -999.0), axis=0)
        dep_data = np.append(dep_data, np.full((dep_data.shape[0], 1), -999.0), axis=1)
        dep_file = []
        for line in list(dep_data):
            temp = []
            for num in line:
                temp.append("%16.7E" % num)
            temp = ''.join(temp) + '\n'
            dep_file.append(temp)
        return dep_file

    def to_file(self, filename):
        """
        Write the data to a Delft3D dep file.

        Parameters
        ----------
        filename : str
            Filename of Delft3D dep file
        Examples
        -------
        >>> dep = DepFile('river.dep')
        >>> dep.to_file('river.dep')
        """
        dep_file = self.export()
        with open(filename, 'w') as f:
            f.writelines(dep_file)
