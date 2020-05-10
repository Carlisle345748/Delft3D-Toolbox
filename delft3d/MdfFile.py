import re

import numpy as np


class MdfFile(object):
    """
    Read, modify, export and write the Delft3D mdf file

    Examples
    --------
    >>> import delft3d
    >>> mdf = delft3d.MdfFile('river.mdf')
    """
    def __init__(self, filename):
        self.filename = filename
        self.data = self.load_file()

    def load_file(self):
        """Read mdf file and store it in self.data as a dict"""
        with open(self.filename, 'r') as f:
            mdf_data = f.readlines()
        # read MDF File and store it in a dict
        mdf_dict = {}
        parm_name = None  # name of the parameter
        for line in mdf_data:
            # search for the name and value of parameters
            matches = re.search(r'^([\w]+)\s*=\s*([\w .#+-:\[\]]*)$', line)
            if matches is not None and matches[1] != 'Commnt':
                # single-line parameter
                # ignore the Comment which are unused by the model
                parm_name = matches[1]  # name of the parameter
                if '#' in matches[2] and '[' not in matches[2]:
                    # character parameter 1
                    mdf_dict[matches[1]] = matches[2].rstrip(' ')
                    mdf_dict[matches[1]] = mdf_dict[matches[1]].replace('#', '')
                elif '[' in matches[2]:
                    # character parameter 2
                    mdf_dict[matches[1]] = matches[2]
                else:
                    # single number parameter
                    num = [float(x) for x in matches[2].split()]
                    # array parameter
                    mdf_dict[matches[1]] = np.array(num) if len(num) > 1 else num[0]
            elif matches is None:
                # multiple-line parameter
                matches = re.search(r'^\s+(.*)$', line)  # search for the value
                parm = mdf_dict.get(parm_name)  # find the name in the last recorded parameter
                if '#' in line:
                    # multiple-line character parameter
                    parm = parm if type(parm) == list else [parm]
                    parm.append(matches[1].replace('#', ''))
                else:
                    # multiple-line array parameter
                    parm = np.array(parm).reshape(-1, 1)
                    parm = np.append(parm, np.array(float(matches[1])).reshape(1, 1), axis=0)
                # store multiple-line parameter
                mdf_dict[parm_name] = parm

        return mdf_dict

    def set_parm(self, data):
        """
        Set new value for a parameter. When setting new values for parameters with multiple
        values (single-line or multiple-line array parameter e.g. Flmap), please input iterable
        data type such as list, tuple and ndarray.

        Parameters
        ----------
        data : dict
            A dict contains names and new values of parameters e.g. {'Fildep': 'river.dep'}.
            Each key and value are corespond to the name and value of one parameter.

        Examples
        ----------
        >>> import delft3d
        >>> mdf = delft3d.MdfFile('river.mdf')
        >>> mdf.set_parm({'Fildep': 'river.dep', 'Dt': 0.5, 'Flmap':[0, 10, 4320]})

        """
        for key, value in data.items():
            if type(self.data[key]) in [float, int]:
                # single number parameter
                self.data[key] = float(value)
            elif type(self.data[key]) == np.ndarray:
                # array parameter
                if len(self.data[key].shape) == 1:
                    # single-line array parameter
                    self.data[key] = np.array(value)
                else:
                    # multiple-line array parameter
                    self.data[key] = np.array(value).reshape(-1, 1)
            elif key == 'Runtxt':
                # multiple-line character parameter
                self.data[key] = value
            else:
                # character parameter
                self.data[key] = str(value)

    def export(self):
        """
        Export the data to a list in the format of Delft3D mdf file

        Examples:
        ---------
        >>> import delft3d
        >>> mdf = delft3d.MdfFile('river.mdf')
        >>> mdf_file = mdf.export()
        >>> mdf_file
            ['Ident  = #Delft3D-FLOW 3.59.01.57433#\\n',
             'Filcco = #river.grd#\\n',
             'Anglat = 2.2560000e+01\\n',
             'Grdang = 2.2830000e+02\\n',
             ...]
        """
        mdf_file = []
        int_key = ['MNKmax', 'Ktemp', 'Ivapop', 'Irov', 'Iter']  # integer parameters
        for key, content in self.data.items():
            if type(content) == np.ndarray and len(content.shape) > 1:
                # multiple-line array parameter
                formatter = "%-6s = %d\n" if key in int_key else "%-6s = %.7e\n"
                mdf_file.append(formatter % (key, content[0]))  # first line
                for arr in content[1:]:  # the rest lines
                    formatter = "          %d\n" if key in int_key else "          %.7e\n"
                    mdf_file.append(formatter % arr)

            elif type(content) == np.ndarray and len(content.shape) == 1:
                # array parameter
                line = "%-6s =" % key
                for arr in content:
                    line += " %d" % arr if key in int_key else " %.7e" % arr
                mdf_file.append(line + '\n')

            elif type(content) == list:
                # multiple-line character parameter
                mdf_file.append("%-6s = #%s#\n" % (key, content[0]))
                for line in content[1:]:
                    mdf_file.append("         #%s#\n" % line)

            else:
                if type(content) == float:
                    # single number parameter
                    formatter = "%-6s = %d" if key in int_key else "%-6s = %.7e"
                    line = formatter % (key, content)
                elif type(content) == str and '[' not in content:
                    # single character parameter 1
                    line = "%-6s = #%s#" % (key, content)
                elif type(content) == str and '[' in content:
                    # single character parameter 2
                    line = "%-6s = %s" % (key, content)
                else:
                    raise ValueError("invalid key")
                mdf_file.append(line + '\n')

        return mdf_file

    def to_file(self, filename):
        """
        Write the data to a Delft3D mdf file

        Parameters
        ----------
        filename : str
            Filename of the mdf file

        Examples
        --------
        >>> import delft3d
        >>> mdf = delft3d.MdfFile('river.mdf')
        >>> mdf.to_file('river.mdf')
        """
        mdf_file = self.export()
        with open(filename, 'w') as f:
            f.writelines(mdf_file)
