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
    >>> import delft3d
    >>> dep1 = delft3d.DepFile('example/example1.dep', 'example/example1.grd')
    >>> grd_file = delft3d.GrdFile('example/example1.grd')
    >>> dep2 = delft3d.DepFile('example/example1.dep', grd_file)
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

    def plot(self, filename=None, sph_epsg=4326, car_epsg=3857):
        """
        Visualize the depth. If the coordinate system is spherical, it will be automatically
        convert to cartesian coordinate system. You can specify the EPSG of coordiante
        by assigning sph_egsp and car_epsg. Find the EPSG of more coordinate system in
        the following link. https://developers.arcgis.com/javascript/3/jshelp/pcs.htm

        Parameters
        ----------
        filename : str, optional
            If filename is given, the figure will be saved with the filename.
        sph_epsg : int, optional
            The EPSG of spherical cooridante.
        car_epsg : int, optional
            The EPSG of carsetian cooridante.

        Examples
        -------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('example/example1.grd')
        >>> dep = delft3d.DepFile('example/example1.dep', grd)
        >>> dep.plot()
        >>> dep.plot('test.jpg')
        >>> dep.plot(sph_epsg=4326, car_epsg=26917)
        """
        if self.grd_file.header['Coordinate System'] == 'Spherical':
            self.grd_file.spherical_to_cartesian(sph_epsg, car_epsg)
            print("Automatically transform from spherical to cartesian coordinates")

        # Prepossessing
        x, y = np.array(self.grd_file.x), np.array(self.grd_file.y)
        z = self.data.copy()  # generate z for pcolormesh
        # if any of the four corners of each grid is invalid(missing value), the grid is marked invalid
        # this prepossess make sure that pcolormesh won't generate weired grid because of missing value
        for i in range(x.shape[0] - 1):
            for j in range(x.shape[1] - 1):
                if x[i, j] == 0 or x[i+1, j] == 0 or x[i, j+1] == 0 or x[i+1, j+1] == 0:
                    z[i, j] = -999
        # mask the invalid grid to make it transparent in pcolormesh
        z = np.ma.masked_equal(z, -999)

        # interpolate the missing value in grd file
        # otherwise the pcolormesh will include the missing value in grid
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
        blues = cm.get_cmap('Blues', 12)
        newcolors = blues(np.linspace(0.2, 1, 256))
        newcmp = ListedColormap(newcolors)
        # plot depth
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111)
        ax0 = ax.pcolormesh(x, y, z, cmap=newcmp,
                            linewidth=0.005, edgecolor=None)
        ax.axis('equal')
        fig.colorbar(ax0)
        if filename:
            plt.savefig(filename)
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
        >>> import delft3d
        >>> dep = delft3d.DepFile('example/example1.dep', 'example/example1.grd')
        >>> dep_data = np.loadtxt('example/dep_data.txt')
        >>> dep.set_dep(dep_data)
        """
        self.data = data

    def export(self):
        """
        Export the data to a ndarry in the format of Delft3D dep file.

        Examples
        -------
        >>> import delft3d
        >>> dep = delft3d.DepFile('example/example1.dep', 'example/example1.grd')
        >>> dep_file = dep.export()
        >>> dep_file
            ['   1.6929708E-01   2.8992051E-01   5.0572435E-01\\n,
             '  -5.0850775E-02   3.1147481E-01   4.6392793E-01\\n,
             ...]
        """
        dep_data = np.append(self.data, np.full((1, self.data.shape[1]), -999.0), axis=0)
        dep_data = np.append(dep_data, np.full((dep_data.shape[0], 1), -999.0), axis=1)

        dep_file = []
        for index, depth in enumerate(dep_data):
            line = ""
            counts = 0
            for num in depth:
                if counts == 0:
                    line += "%16.7E" % num
                elif counts % 12 == 11:
                    line += "%16.7E\n" % num
                elif counts % 12 == 0:
                    line += "%16.7E" % num
                else:
                    line += "%16.7E" % num
                if counts == len(depth) - 1 and counts % 12 != 11:
                    line += '\n'
                counts += 1
            # grd_file.append(line)
            line = line.splitlines()
            line = [x + '\n' for x in line]
            dep_file.extend(line)

        # dep_file = []
        # for line in list(dep_data):
        #     temp = []
        #     for num in line:
        #         temp.append("%16.7E" % num)
        #     temp = ''.join(temp) + '\n'
        #     dep_file.append(temp)
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
        >>> import delft3d
        >>> dep = delft3d.DepFile('example/example1.dep', 'example/example1.grd')
        >>> dep.to_file('example1.dep')
        """
        dep_file = self.export()
        with open(filename, 'w') as f:
            f.writelines(dep_file)
