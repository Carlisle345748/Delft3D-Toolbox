import re
import numpy as np
from delft3d.GrdFile import GrdFile
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import ListedColormap


class DepFile(object):
    """
    Read, modify, visualize, export and write Delft3D dep file

    Example
    --------
    >>> dep1 = DepFile('river.dep', 'river.grd')
    >>> grd_file = GrdFile('river.grd')
    >>> dep2 = DepFile('river.dep', grd_file)
    """
    def __init__(self, filename, grd_file):
        self.filename = filename
        if type(grd_file) == str:
            self.grd_file = GrdFile(grd_file)
        elif type(grd_file) == GrdFile:
            self.grd_file = grd_file
        else:
            raise ValueError("Please supply the GrdFile instance or grd file's filename")
        self.data = self.load_dep()

    def load_dep(self):
        """Read dep file"""
        with open(self.filename, 'r') as f:
            data = f.read()
        pattern = r'(\s+[\d.E+-]+\n?){' + str(self.grd_file.header['MN'][0] + 1) + '}'
        matches = re.finditer(pattern, data)
        dep = list()
        for matche in matches:
            dep.append([float(i) for i in matche[0].split()])
        dep = np.array(dep)
        dep = np.delete(dep, -1, axis=0)
        dep = np.delete(dep, -1, axis=1)

        return dep

    def plot(self):
        """
        Visualize dep file

        Examples
        -------
        >>> grd = GrdFile('river.grd')
        >>> dep = DepFile('river.dep')
        >>> dep.plot(grd)
        """
        if self.grd_file.header['Coordinate System'] == 'Spherical':
            self.grd_file.spherical_to_cartesian()
            print("Automatically transform from spherical to cartesian coordinates")

        # Preprocessing
        x, y = np.array(self.grd_file.x), np.array(self.grd_file.y)
        z = self.data.copy()  # generate z for pcolormesh
        # if any of the four corners of each grid is invalid(missing value), the grid is marked invalid
        # this preprocess make sure that pcolormesh won't generate weired grid because of missing value
        for i in range(x.shape[0] - 1):
            for j in range(x.shape[1] - 1):
                if x[i, j] == 0 or x[i+1, j] == 0 or x[i, j+1] == 0 or x[i+1, j+1] == 0:
                    z[i, j] = -999
        # mask the invalid grid to make it transparent in pcolormesh
        z = np.ma.masked_equal(z, -999)

        # interpolate the missing value in grd file
        # otherwise the pcolormesh will inclue the missing value in grid
        missing_value = self.grd_file.header['Missing Value']
        for index, arr in enumerate(x):
            x1 = np.argwhere(arr == missing_value).ravel()
            x2 = np.argwhere(arr != missing_value).ravel()
            y2 = arr[arr != missing_value]
            x[index][x[index] == missing_value] = np.interp(x1, x2, y2)
        for index, arr in enumerate(y):
            x1 = np.argwhere(arr == missing_value).ravel()
            x2 = np.argwhere(arr != missing_value).ravel()
            y2 = arr[arr != missing_value]
            y[index][y[index] == missing_value] = np.interp(x1, x2, y2)

        # Define colormap
        Blues = cm.get_cmap('Blues', 12)
        newcolors = Blues(np.linspace(0.2, 1, 256))
        newcmp = ListedColormap(newcolors)
        # plot depth
        plt.pcolormesh(x, y, z, cmap=newcmp,
                       linewidth=0.005, edgecolor=None)
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
