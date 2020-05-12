import os
import re

import pandas as pd


class TimeSeriesFile(object):
    """
    Read, modify, export and write Delft3D time series files (bcc/bct/dis).

    Examples
    --------
    >>> import delft3d
    >>> bct = delft3d.TimeSeriesFile('river.bct')
    >>> bcc = TimeSeriesFile('river.bcc')
    >>> dis = TimeSeriesFile('river.dis')
    """
    def __init__(self, filename):
        self.type = os.path.splitext(filename)[1][1:]
        self.filename = filename
        self.data = self.load_file()

    def load_file(self):
        """Read bct/bcc/dis file. The content of the file will be stored in self.data. """
        with open(self.filename) as f:
            data = f.readlines()
        # read each time series and interpret them
        time_series = []
        start_index, end_index = 0, None
        in_table = False
        for index, line in enumerate(data):
            if in_table and index == len(data) - 1:
                # last time series
                time_series.append(TimeSeries(data[start_index:]))
            elif 'table-name' in line:
                end_index = index
                if in_table:
                    # interpret time series
                    time_series.append(TimeSeries(data[start_index: end_index]))
                    start_index = index
                else:
                    in_table = True
        return time_series

    def set_header(self, num, data, unit=False):
        """
        Modify the content of the header. IMPORTANT: This method cannot change the value and
        the unit of a parameter simultaneously. If you want to change the unit of a parameter,
        please set unit=True and only change the unit in one call.

        Parameters
        ----------
        num : int
            the no. of time series. '0' means the first time series in the file.
        data : dict
            a dict contains new content of headers, e.g. {'reference-time': '20200304'}
        unit : bool, optional
            If true, this method change the unit of parameter. Otherwise thsi method
            change the value of parameter.

        Returns
        -------

        Examples
        -------
        >>> import delft3d
        >>> bct = delft3d.TimeSeriesFile('river.bct')
        >>> bct.set_header(0, {'time-unit': 'hours', 'location': '(2,3)..(4,6)'})
        >>> bct.set_header(0, {'parameter': {'time': 'relative-time', 'pollution': 'NH3-N'}})
        >>> bct.set_header(0, {'parameter':{'time': 'hour', 'pollution': 'mg/l'}}, unit=True)

        """
        self.data[num].set_header(data, unit)

    def set_time_series(self, num, reference_time, data1, data2):
        """
        Replace the old time series with the new one.

            Parameters
            ----------
            num : int
                The no. of time series. '0' means the first time series in the file.
            reference_time: str
                new reference time
            data1: pd.DataFrame or pd.Series
                The second column of time series.
                The index of the Series must be DatetimeIndex
            data2 : pd.DataFrame or pd.Series
                The thrid column of time series.
                The index of the Series must be DatetimeIndex


        Example
        ----------
        >>> import delft3d
        >>> bct = delft3d.TimeSeriesFile('river.bct')
        >>> flow_series_A = pd.read_csv('flow_series_A.csv', index_col=0)
        >>> flow_series_A.index = pd.to_datetime(flow_series_A.index)
        >>> flow_series_B = pd.read_csv('flow_series_B.csv', index_col=0)
        >>> flow_series_B.index = pd.to_datetime(flow_series_B.index)
        >>> flow_series_A.head()
                                 total discharge (t)  end A
            2020-03-31 00:00:00                   -5.244540
            2020-03-31 00:10:00                   -5.513570
            2020-03-31 00:20:00                   -5.802258
            2020-03-31 00:30:00                   -6.178733
            2020-03-31 00:40:00                   -6.445315
        >>> bct.set_time_series(0, '2020-03-04', flow_series_A, flow_series_B)

        """
        self.data[num].set_time_series(reference_time, data1, data2)

    def export(self):
        """
        Export the data to a list in the format of Delft3D time series file.

        Example
        -------
        >>> import delft3d
        >>> bct = delft3d.TimeSeriesFile('river.bct')
        >>> bct_file = bct.export()
        >>> bct_file
            ["table-name           'Boundary Section : 1'\\n",
             "contents             'Uniform             '\\n",
             "location             '(2,246)..(7,246)    '\\n",
            ...]

        """
        bct_data = []
        for time_series in self.data:
            bct_data += time_series.export()
        return bct_data

    def to_file(self, filename):
        """
        Write the data to a Delft3D time series file.

        Parameters
        ----------
        filename : str
            Filename of the time series file

        Examples
        ----------
        >>> import delft3d
        >>> bct = delft3d.TimeSeriesFile('river.bct')
        >>> bct.to_file('river.bct')
        """
        bct_data = self.export()
        with open(filename, 'w') as f:
            for line in bct_data:
                f.write(line)


class TimeSeries(object):
    """Read, modify and export Delft3D time series."""
    def __init__(self, time_series: list):
        self.time_series = None
        self.header = None
        self.load_header(time_series)
        self.load_time_series(time_series)

    def load_header(self, time_series: list):
        """Read and interpret the header of a time series."""
        header_dict = {}
        parameter = {}
        records_in_table = None
        header_re = re.compile(r"^([^-][\w-]+)\s+('?[\w\d (),./:-]+'?)")
        unit_re = re.compile(r"([\s]+unit '\[[\w/]+\]')")
        for line in time_series:
            matches = header_re.search(line)  # search for header
            if matches:
                if matches[1] == 'parameter':
                    # parameters have the same header name. So store all parameters
                    # in one dict
                    unit_match = unit_re.search(line)  # search for unit
                    key_name = matches[2].strip('\'')  # reformat unit
                    key_name = key_name.strip(' ')
                    parameter[key_name] = Parameter(matches[2], unit_match[1])
                elif matches[1] == 'records-in-table':
                    # records-in-table should be the last header. Store it hera and
                    # then put it at the end of headers by the end.
                    records_in_table = Parameter(matches[2])
                else:
                    # regular header
                    header_dict[matches[1]] = Parameter(matches[2])
            else:  # end of the header
                header_dict['parameter'] = parameter
                header_dict['records-in-table'] = records_in_table
                break
        self.header = header_dict

    def load_time_series(self, time_series: list):
        """Read and interpret time series"""
        is_header = True  # whether the pointer at the header
        reference_time = pd.to_datetime(self.header['reference-time'].value)
        # read the time series data
        time, relative_time, parm1, parm2 = [], [], [], []
        for line in time_series:
            if not is_header:
                # prepossess
                data = [float(i) for i in line.split()]
                time.append(reference_time + pd.to_timedelta(data[0], unit="minutes"))
                # store the data
                relative_time.append(data[0])
                parm1.append(data[1])
                parm2.append(data[2])
            if 'records-in-table' in line:
                is_header = False
        else:
            # converts lists to DataFrame
            colname = list(self.header['parameter'].keys())
            time_series = pd.DataFrame(
                {colname[0]: relative_time, colname[1]: parm1, colname[2]: parm2}, index=time)
        self.time_series = time_series

    def set_header(self, data: dict, unit=False) -> None:
        """Set new content of header. Called by TimeSeriesFile.set_header()"""
        header = self.header.copy()
        for key, new_parm in data.items():
            if key not in ['parameter', 'reference-time', 'records-in-table']:
                # regular header
                header[key].value = str(new_parm)
            elif key in ['reference-time', 'records-in-table']:
                # raise warning when reference-time and records-in-table are changed
                header[key].value = str(new_parm)
                print("'reference-time' and 'records-in-table' have been changed."
                      " Please check time series data")
            else:
                # change parameter
                for key_, new_parm_ in new_parm.items():
                    if unit:
                        header[key][key_].unit = str(new_parm_)
                    else:
                        header[key][key_].value = str(new_parm_)
        self.header = header

    def set_time_series(self, reference_time: str,
                        data1: pd.core.frame.Series,
                        data2: pd.core.frame.Series):
        """
        Replace the old time series with the new one. Called by TimeSeriesFile.set_time_series()
        """
        time_series = pd.concat([data1, data2], axis=1)
        # calculate the absolute time and  relative time
        reference_time = pd.to_datetime(reference_time)
        relative_time = time_series.index - reference_time
        relative_time = [time.total_seconds() / 60 for time in relative_time]  # 单位：minute
        relative_time = pd.Series(relative_time, index=time_series.index, name='time')
        # combine time absolute time, relative time and data
        time_series = pd.concat([relative_time, time_series], axis=1)
        # store new time series
        self.time_series = time_series.copy()
        # change the 'reference time' and 'records-in-table' in the header
        reference_time = reference_time.strftime("%Y%m%d")
        self.set_header({'records-in-table': len(time_series), "reference-time": reference_time})

    def export_header(self):
        """Export the header as a list in the format of Delft3D time series file"""
        header = []
        for key, parm in self.header.items():

            if key != 'parameter':
                # parameter header
                head = key.ljust(21) + parm.export() + '\n'
                header.append(head)
            else:
                # regular header
                for i in parm:
                    head = key.ljust(21) + parm[i].export() + '\n'
                    header.append(head)
        return header

    def export_time_series(self):
        """Export the time series as a list in the format of Delft3D time series files"""
        time_series = []
        for index, row in self.time_series.iterrows():
            time_series.append(" {:.7e} {:.7e} {:.7e}\n".format(row[0], row[1], row[2]))
            pass
        return time_series

    def export(self):
        """Export all data as a list in the format of Delft3D time series files"""
        return self.export_header() + self.export_time_series()


class Parameter(object):
    """
    Read and export the content of header in Delft3D Time Series. The function of this class
    is to keep the original format of Delft3D Time Series in order to prevent unexpected errors.
    """
    def __init__(self, value, unit=None):
        """Read the store the format, type and unit of a header"""
        value_re = re.compile(r'[\w() /:,.-]+\b\)?')  # search for the value
        value_match = value_re.search(value)
        self.value = value_match[0]
        if '\'' in value:
            # string type
            self.value_length = len(value) - 2  # length of the string
            self.type = 'str'
        else:
            # number type
            self.value_length = len(value)  # length of the number
            self.type = 'num'

        self.unit = None
        # store the unit
        if unit:
            # search for unit
            unit_re = re.compile(r"unit '\[([\w/]+)\]'")
            unit_match = unit_re.search(unit)
            # store the unit
            self.unit = unit_match[1]
            self.unit_length = len(unit)

    def export(self):
        """export the header in its original format"""
        if self.type == 'str':
            content = "'{}'".format(self.value.ljust(self.value_length))
            if self.unit:
                content += ("unit '[{}]'".format(self.unit)).rjust(self.unit_length)
        else:
            content = "{}".format(self.value.ljust(self.value_length))

        return content

    def __repr__(self):
        if self.unit:
            return "{} unit={}".format(self.value, self.unit)
        else:
            return "{}".format(self.value)
