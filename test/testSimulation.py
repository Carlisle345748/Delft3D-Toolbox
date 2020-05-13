import unittest
import delft3d
from pathlib import Path
import os


class TestSimulation(unittest.TestCase):
    def test_search_delft3d(self):
        gui_path = {'delft3d_path': Path('C:/Program Files/Deltares/Delft3D 4.04.01/x64'),
                    'd_hydro': Path('C:/Program Files/Deltares/Delft3D 4.04.01/x64/dflow2d3d/bin/d_hydro.exe'),
                    'dflow2d3d': Path('C:/Program Files/Deltares/Delft3D 4.04.01/x64/dflow2d3d/bin'),
                    'share': Path('C:/Program Files/Deltares/Delft3D 4.04.01/x64/share/bin')}
        compiled_path = {'delft3d_path': Path('C:/Users/Carlisle/Desktop/62422/src/bin/x64'),
                         'd_hydro': Path('C:/Users/Carlisle/Desktop/62422/src/bin/x64/dflow2d3d/bin/d_hydro.exe'),
                         'dflow2d3d': Path('C:/Users/Carlisle/Desktop/62422/src/bin/x64/dflow2d3d/bin'),
                         'share': Path('C:/Users/Carlisle/Desktop/62422/src/bin/x64/share/bin')}
        gui = r'C:\Program Files\Deltares\Delft3D 4.04.01'
        compiled = r'C:\Users\Carlisle\Desktop\62422\src\bin'
        run_gui = delft3d.Simulation(gui)
        run_compiled = delft3d.Simulation(compiled)
        self.assertDictEqual(run_gui.engine, gui_path)
        self.assertDictEqual(run_compiled.engine, compiled_path)

    def test_create_xml(self):
        gui_path = r'C:\Program Files\Deltares\Delft3D 4.04.01\x64'
        run = delft3d.Simulation(gui_path)
        run.create_xml('dflow1/f34.mdf', 1)
        with open('config_d_hydro_test.xml') as f:
            xml_test = f.readlines()
        with open('dflow1/config_d_hydro_1.xml') as f:
            xml_testcase = f.readlines()
        self.assertListEqual(xml_test, xml_testcase)
        os.remove('dflow1/config_d_hydro_1.xml')

    def test_create_bat(self):
        gui_path = r'C:\Program Files\Deltares\Delft3D 4.04.01\x64'
        run = delft3d.Simulation(gui_path)
        run.create_bat('dflow1/f34.mdf', 1)
        with open('run_test.bat') as f:
            bat_test = f.readlines()
        with open('dflow1/run_1.bat') as f:
            bat_testcase = f.readlines()
        self.assertListEqual(bat_test, bat_testcase)
        os.remove('dflow1/run_1.bat')

    def test_sim_unit(self):
        gui_path = r'C:\Program Files\Deltares\Delft3D 4.04.01\x64'
        run = delft3d.Simulation(gui_path)
        run.sim_unit('dflow1/f34.mdf', disp=False)
        run.sim_unit('dflow1/f34.mdf', disp=False, netcdf=True)

    def test_run(self):
        gui_path = r'C:\Program Files\Deltares\Delft3D 4.04.01\x64'
        run = delft3d.Simulation(gui_path)
        run.run(['dflow1/f34.mdf', 'dflow2/f342.mdf'], disp=False, netcdf=True)
        run.run(['dflow1/f34.mdf', 'dflow2/f342.mdf'], workers=2, disp=False, netcdf=True)


if __name__ == '__main__':
    unittest.main()
