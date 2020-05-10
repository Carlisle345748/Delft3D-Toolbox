import re

import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS, Transformer


class GrdFile(object):
    """
    Read, modify, visualize, export and write Deflt3D dep file

    Examples
    --------
    >>> import delft3d
    >>> grd = delft3d.GrdFile('river.grd')
    """
    def __init__(self, filename):
        self.filename = filename
        self.x, self.y = None, None
        self.header = {}
        self.load_file()

    def load_file(self):
        """Read dep file"""
        with open(self.filename, 'r') as f:
            data = f.read()
        # read headers
        coordinate_system = re.search(r'Coordinate System = ([\w]+)', data)
        self.header['Coordinate System'] = coordinate_system.group(1) if coordinate_system else None
        missing_value = re.search(r'Missing Value\s+=\s+([\w+-.]+)', data)
        self.header['Missing Value'] = np.float(missing_value.group(1)) if missing_value else 0
        mn = re.search(r'\n\s+([\d]+)\s+([\d]+)\n', data)
        m, n = int(mn.group(1)), int(mn.group(2))
        self.header['MN'] = [m, n]
        # read coordinates
        x, y = [], []
        pattern = r' ETA=\s+\d+(\s+[\d.Ee+]+\n?){' + str(m) + '}'
        matches = re.finditer(pattern, data)
        for index, match in enumerate(matches):
            cor = match[0].split()[2:]
            cor = [np.float(num) for num in cor]
            if index < n:
                x.extend(cor)
            else:
                y.extend(cor)
        x, y = np.array(x), np.array(y)
        # mask invalid value
        x = np.ma.masked_equal(x, self.header['Missing Value'])
        y = np.ma.masked_equal(y, self.header['Missing Value'])
        # reshape to the original format
        self.x = x.reshape(n, m)
        self.y = y.reshape(n, m)

    def spherical_to_cartesian(self, sph_epsg=4326, car_epsg=3857):
        """
        Convert from spherical coordinates to cartesian coordinates.
        Default spherical coordinate system: WGS 84.
        Default cartesian coordinate system: WGS_1984_Web_Mercator_Auxiliary_Sphere.
        Find the EPSG of more coordinate system in the following link.
        https://developers.arcgis.com/javascript/3/jshelp/pcs.htm

        Parameters
        ----------
        sph_epsg : int, optional
            EPSG of the original spherical coordinate system
        car_epsg : int, optional
            EPSG of the objective cartesian coordinate system

        Examples
        ----------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd.spherical_to_cartesian()
        >>> grd.spherical_to_cartesian(sph_epsg=4326, car_epsg=26917)
        """
        # transform from spherical to cartesian
        init_crs = CRS.from_epsg(sph_epsg)
        obj_crs = CRS.from_epsg(car_epsg)
        projection = Transformer.from_crs(init_crs, obj_crs)
        # update x, y
        self.x, self.y = projection.transform(self.x, self.y)
        # update header
        self.header['Coordinate System'] = 'Cartesian'

    def cartesian_to_spherical(self, car_epsg=3857, sph_epsg=4326):
        """
        Convert from cartesian coordinates to spherical coordinates.
        Default spherical coordinate system: WGS 84.
        Default cartesian coordinate system: WGS_1984_Web_Mercator_Auxiliary_Sphere.
        Find the EPSG of more coordinate system in the following link.
        https://developers.arcgis.com/javascript/3/jshelp/pcs.htm

        Parameters
        ----------
        car_epsg : int, optional
            EPSG of the original cartesian coordinate system
        sph_epsg : int, optional
            EPSG of the objective spherical coordinate system
        Examples
        ----------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd.cartesian_to_spherical()
        >>> grd.cartesian_to_spherical(car_epsg=26917, sph_epsg=4326)

        """
        # transform from cartesian to spherical
        init_crs = CRS.from_epsg(car_epsg)
        obj_crs = CRS.from_epsg(sph_epsg)
        projection = Transformer.from_crs(init_crs, obj_crs)
        # update x, y
        self.x, self.y = projection.transform(self.x, self.y)
        # update header
        self.header['Coordinate System'] = 'Spherical'

    def get_nearest_grid(self, x, y, sph_epsg=4326, car_epsg=3857):
        """
        Find the nearest grid for the giving coordinate. If the coordinate system is
        spherical, it will be automatically convert to cartesian coordinate system.
        You can specify the EPSG of coordiante by assigning sph_egsp and car_epsg.
        Find the EPSG of more coordinate system in the following link.
        https://developers.arcgis.com/javascript/3/jshelp/pcs.htm

        Parameters
        ----------
        x : float
            x coordinate.
        y : float
            y coordinate.
        sph_epsg : int, optional
            The EPSG of spherical cooridante.
        car_epsg : int, optional
            The EPSG of carsetian cooridante.
        Returns
        -------
        m, n : tuple
            (m,n) coordinate of grid

        Examples
        --------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> m, n = grd.get_nearest_grid(505944.89, 2497013.47)
        """
        if self.header['Coordinate System'] == 'Spherical':
            # transform from spherical to cartesian
            grd_crs = CRS.from_epsg(sph_epsg)
            plot_crs = CRS.from_epsg(car_epsg)
            projection = Transformer.from_crs(grd_crs, plot_crs)
            grd_x, grd_y = projection.transform(self.x, self.y)
            print("Automatically transform from spherical to cartesian coordinates.\n"
                  "Change the default projection by giving specific grd_epsg and plot_epsg")
        else:
            grd_x, grd_y = self.x, self.y
        # calculate distance
        dis = np.sqrt(
            (x - grd_x.ravel()) ** 2 + (y - grd_y.ravel()) ** 2)
        # find nearest grid
        num = np.argmin(dis)
        n, m = np.unravel_index(num, (self.header['MN'][1], self.header['MN'][0]))
        return m, n

    def plot(self, filename=None, sph_epsg=4326, car_epsg=3857):
        """
        Visualize the grid.If the coordinate system is spherical, it will be automatically
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
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd.plot()
        >>> grd.plot('test.jpg')
        >>> grd.plot(sph_epsg=4326, car_epsg=26917)
        """
        if self.header['Coordinate System'] == 'Spherical':
            # transform from spherical to cartesian
            grd_crs = CRS.from_epsg(sph_epsg)
            plot_crs = CRS.from_epsg(car_epsg)
            projection = Transformer.from_crs(grd_crs, plot_crs)
            x, y = projection.transform(self.x, self.y)

            print("Automatically transform from spherical to cartesian coordinates.\n"
                  "Change the default projection by giving specific grd_epsg and plot_epsg")
        else:
            x, y = self.x, self.y

        # Prepossessing
        x, y = np.array(x.data), np.array(y.data)
        z = np.zeros(np.shape(x))  # generate z for pcolormesh
        # If any of the four corners of each grid is invalid(missing value),
        # the grid is marked invalid. This preprocess make sure that pcolormesh
        # won't generate weired grid because of the missing value
        invlid = self.header['Missing Value']  # Missing Value
        for i in range(x.shape[0] - 1):
            for j in range(x.shape[1] - 1):
                if x[i, j] == invlid or x[i+1, j] == invlid or\
                        x[i, j+1] == invlid or x[i+1, j+1] == invlid:
                    z[i,j] = 1
        # mask the invalid grid to make it transparent in pcolormesh
        z = np.ma.masked_equal(z, 1)

        # interpolate the missing value in grd file
        # otherwise the pcolormesh will inclue the missing value in grid
        for index, arr in enumerate(x):
            x1 = np.argwhere(arr == invlid).ravel()
            x2 = np.argwhere(arr != invlid).ravel()
            y2 = arr[arr != invlid]
            x[index][x[index] == invlid] = np.interp(x1, x2, y2)
        for index, arr in enumerate(y):
            x1 = np.argwhere(arr == invlid).ravel()
            x2 = np.argwhere(arr != invlid).ravel()
            y2 = arr[arr != invlid]
            y[index][y[index] == invlid] = np.interp(x1, x2, y2)
        # plot grid
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111)
        ax.pcolormesh(x, y, z, edgecolor='black',
                            facecolor='none', linewidth=0.005)
        ax.axis('equal')
        if filename:
            plt.savefig(filename)
        fig.show()

    def set_gird(self, x, y, coordinate_system):
        """
        Set new grid.

        Parameters
        ----------
        x : ndarray
            x coordinates of the new grid
        y : ndarray
            y coordinates of the new grid
        coordinate_system : str
            The type of coordinate system. Spherical or Cartesian

        Examples
        -------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd_x = np.loadtxt('grd_x.txt')
        >>> grd_y = np.loadtxt('grd_y.txt')
        >>> grd.set_gird(grd_x, grd_y, 'Cartesian')
        """
        self.x = x
        self.y = y
        self.header['Coordinate System'] = coordinate_system
        self.header['MN'] = [x.shape[1], x.shape[0]]

    def export(self):
        """
        Export the data to a list in the format of Delft3D grd file.

        Examples
        -------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd_file = grd.export()
        >>> grd_file
            ['Coordinate System = Cartesian\\n',
             'Missing Value = -9.9999900e+02\\n',
             '       7     245\\n',
             ' 0 0 0\\n',
             ...]
        """
        grd_file = list()
        # Add header
        grd_file.append("Coordinate System = %s\n" % self.header['Coordinate System'])
        if self.header['Missing Value'] != 0:
            grd_file.append("Missing Value = %.7e\n" % self.header['Missing Value'])
        grd_file.append("%8d%8d\n" % ((self.header['MN'][0]), self.header['MN'][1]))
        grd_file.append(" 0 0 0\n")
        # Add grid data
        grd_file = self.grid_writer(grd_file, self.x)
        grd_file = self.grid_writer(grd_file, self.y)

        return grd_file

    @staticmethod
    def grid_writer(grd_file, coordinates):
        """Helper function of self.export. Formatting grid data as Delft3D grd file"""
        grd_file = grd_file.copy()
        for index, cor in enumerate(coordinates):
            line = " ETA=%5d" % (index + 1)
            counts = 0
            for num in cor:
                if counts == 0:
                    line += "   %.17E" % num
                elif counts % 5 == 4:
                    line += "   %.17E\n" % num
                elif counts % 5 == 0:
                    line += "             %.17E" % num
                else:
                    line += "   %.17E" % num
                if counts == len(cor) - 1 and counts % 5 != 4:
                    line += '\n'
                counts += 1
            grd_file.append(line)
        return grd_file

    def to_file(self, filename):
        """
        Write the data to a Delft3D grd file.

        Parameters
        ----------
        filename : str
            Filename of the grd file.

        Examples
        -------
        >>> import delft3d
        >>> grd = delft3d.GrdFile('river.grd')
        >>> grd.to_file('river.grd')
        """
        grd_file = self.export()
        with open(filename, 'w') as f:
            f.writelines(grd_file)
