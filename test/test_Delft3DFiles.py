from unittest import TestCase, main
import delft3d
import pandas as pd
import numpy as np


class TestTimeSeriesFile(TestCase):

    def test_bct_export(self):
        with open("bct_test.bct", 'r') as f:
            bct_test = f.readlines()
        bct_data = delft3d.TimeSeriesFile("bct_test.bct")
        self.assertListEqual(bct_test, bct_data.export())

    def test_bcc_export(self):
        with open("bcc_test.bcc", 'r') as f:
            bcc_test = f.readlines()
        bcc_data = delft3d.TimeSeriesFile("bcc_test.bcc")
        self.assertListEqual(bcc_test, bcc_data.export())

    def test_dis_export(self):
        with open("dis_test.dis", 'r') as f:
            dis_test = f.readlines()
        dis_data = delft3d.TimeSeriesFile("dis_test.dis")
        self.assertListEqual(dis_test, dis_data.export())

    def test_set_header(self):
        bct_data = delft3d.TimeSeriesFile("bct_test.bct")
        bct_data.set_header(0, {'location': '(1,1)..(1,1)'})
        bct_data.set_header(0, {'reference-time': '20200120'})
        bct_data.set_header(0, {'parameter': {'time': 'relative time'}})
        bct_data.set_header(0, {'parameter': {'time': 'hour'}}, unit=True)
        self.assertEqual(bct_data.data[0].header['location'].value, '(1,1)..(1,1)')
        self.assertEqual(bct_data.data[0].header['reference-time'].value, '20200120')
        self.assertEqual(bct_data.data[0].header['parameter']['time'].value, 'relative time')
        self.assertEqual(bct_data.data[0].header['parameter']['time'].unit, 'hour')

        self.assertEqual(bct_data.data[0].header['location'].export(), "'(1,1)..(1,1)        '")
        self.assertEqual(bct_data.data[0].header['reference-time'].export(), "20200120")
        self.assertEqual(bct_data.data[0].header['parameter']['time'].export(),
                         "'relative time       '                    unit '[hour]'")

    def test_set_time_series(self):

        reference_time = pd.to_datetime("2020-04-15")
        time_index = pd.to_timedelta(np.arange(10)*10, unit="min") + reference_time
        data1 = pd.Series(np.ones(10) * 100, index=time_index)
        data2 = pd.Series(np.ones(10) * 200, index=time_index)

        relative_time = pd.to_timedelta(np.arange(10)*10, unit="min")
        relative_time = [time.total_seconds() / 60 for time in relative_time]
        test_table = pd.DataFrame({'time': relative_time, '1': np.ones(10) * 100,
                                   '2': np.ones(10) * 200}, index=time_index)

        bct_data = delft3d.TimeSeriesFile("bct_test.bct")
        bct_data.set_time_series(0, "2020-04-15", data1, data2)

        self.assertTrue(np.array((bct_data.data[0].time_series.index == time_index)).all())
        self.assertTrue((bct_data.data[0].time_series.values == test_table.values).all())
        self.assertEqual(bct_data.data[0].header['records-in-table'].value, str(len(time_index)))
        self.assertEqual(bct_data.data[0].header['reference-time'].value, reference_time.strftime("%Y%m%d"))

    def test_MdfFile(self):
        mdf = delft3d.MdfFile('mdf_test.mdf')
        Runtxt = ['test', 'for', 'multiple-line', 'character', 'parameter']
        mdf.set_parm({'Ag': 10.0, 'Rhow': 2000, 'Wndint': 'Y'})
        mdf.set_parm({'Runtxt': Runtxt})
        mdf.set_parm({'MNKmax': [1, 2, 3], 'Rettis': [1, 1]})
        mdf.add_parm({'FlNcdf': 'map his dro fou'})
        self.assertEqual(mdf.data['Ag'], 10.0)
        self.assertEqual(mdf.data['Rhow'], 2000.0)
        self.assertEqual(mdf.data['Wndint'], 'Y')
        self.assertEqual(mdf.data['Runtxt'], Runtxt)
        self.assertTrue((mdf.data['MNKmax'] == np.array([1, 2, 3])).all())
        self.assertTrue((mdf.data['Rettis'] == np.array([[1], [1]])).all())
        self.assertEqual(mdf.data['FlNcdf'], 'map his dro fou')

    def test_GrdFile_export(self):
        grd1 = delft3d.GrdFile('grd_test1.grd').export()
        grd2 = delft3d.GrdFile('grd_test2.grd').export()
        with open('grd_test1.grd', 'r') as f:
            test_grd1 = f.readlines()
        with open('grd_test2.grd', 'r') as f:
            test_grd2 = f.readlines()
        self.assertEqual(''.join(grd1), ''.join(test_grd1))
        self.assertEqual(''.join(grd2), ''.join(test_grd2))

    def test_GrdFile_coordinates(self):
        grd1 = delft3d.GrdFile('grd_test1.grd')
        grd1_sphX = np.loadtxt('grd_test1_sphX.txt')
        grd1_sphY = np.loadtxt('grd_test1_sphY.txt')
        grd1_carX = np.loadtxt('grd_test1_carX.txt')
        grd1_carY = np.loadtxt('grd_test1_carY.txt')

        grd1.cartesian_to_spherical()
        self.assertTrue((grd1.x == grd1_sphX).all())
        self.assertTrue((grd1.y == grd1_sphY).all())
        grd1.spherical_to_cartesian()
        self.assertTrue((grd1.x - grd1_carX < 1e-8).all())
        self.assertTrue((grd1.y - grd1_carY < 1e-8).all())

    def test_GrdFile_get_nearest_grid(self):
        grd1 = delft3d.GrdFile('grd_test1.grd')
        m, n = grd1.get_nearest_grid(grd1.x[5, 4], grd1.y[5, 4])
        self.assertEqual(m, 4)
        self.assertEqual(n, 5)

    def test_DepFile(self):
        dep_data1 = delft3d.DepFile('dep_test1.dep', 'grd_test1.grd').export()
        dep_data2 = delft3d.DepFile('dep_test2.dep', 'grd_test2.grd').export()
        with open('dep_test1.dep', 'r') as f:
            dep_file1 = f.readlines()
        with open('dep_test2.dep', 'r') as f:
            dep_file2 = f.readlines()

        self.assertListEqual(dep_data1, dep_file1)
        self.assertListEqual(dep_data2, dep_file2)


if __name__ == '__main__':
    main()
