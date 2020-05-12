import os
from pathlib import Path
import xml.dom.minidom
import numpy as np
from multiprocessing import Pool
from delft3d import MdfFile


class Simulation(object):
    def __init__(self, delft3d_path):
        """
        Delft3D simulation launcher

        Parameters
        ----------
        delft3d_path : str
            The path of the pre-compiled Delft3D source code or GUI installation
            with Delft3D source code.

        Examples
        --------
        >>> Simulation('C:/Users/Carlisle/Desktop/62422/src/bin/x64')
        >>> Simulation('C:/Program Files/Deltares/Delft3D 4.04.01/x64')
        """
        self.engine = self.search_delft3d(delft3d_path)

    def search_delft3d(self, delft3d_path):
        """
        Search for the path of Delft3D source code.

        Parameters
        ----------
        delft3d_path ： str
            The path of the pre-compiled Delft3D source code or GUI installation
            with Delft3D source code.

        """
        delft3d_path = Path(delft3d_path).absolute()
        if delft3d_path.exists():
            # if delft3d_path path is precise, directly set the delft3d_path path
            d_hydro = delft3d_path / 'dflow2d3d/bin/d_hydro.exe'
            dflow2d3d = d_hydro.parents[0]
            share = delft3d_path / 'share/bin'
            if d_hydro.exists() and dflow2d3d.exists() and share.exists():
                pass
            else:
                # delft3d_path path is not precise enough, automatically search for delft3d_path path
                search_result = self.recursive_search(
                    delft3d_path, ['dflow2d3d/bin', 'share/bin'])
                d_hydro = search_result['dflow2d3d/bin'] / 'd_hydro.exe'
                dflow2d3d = search_result['dflow2d3d/bin']
                share = search_result['share/bin']
                delft3d_path = dflow2d3d.parents[1]
                print("'delft3d_path' is not precise. Automatically search for the delft3d_path.\n"
                      "Please supply the 'delft3d_path' as '.../x64' to avoid the extra searching.")
        else:
            raise FileNotFoundError("Delft3D path not exist")
        delft3d_path = {'delft3d_path': delft3d_path, 'd_hydro': d_hydro,
                        'dflow2d3d': dflow2d3d, 'share': share}
        return delft3d_path

    def recursive_search(self, root, target, result=None):
        """
        Recursively search for files or directories. Used by self.search_delft3d
        Parameters
        ----------
        root : str or Path
            The path where the search start.
        target : list or tuple
            Files or directories to find.
        result : dict
            Memory dict. When searching for multiple files or directories,
            this dict will memorize the result in searching.
        Returns
        -------
        result : dict
            The path of the target file.
        """
        if result is None:
            result = {}
        root = Path(root)
        for path in root.iterdir():
            if len(result) == len(target):
                return result
            elif '/'.join(path.parts[-2:]) in target:
                result['/'.join(path.parts[-2:])] = path
            elif path.is_dir():
                self.recursive_search(path, target, result)
        if len(result) == len(target):
            return result

    def run(self, mdf_path, disp=True, netcdf=False, workers=1):
        """
        Run Delft3D simulations. Parallelization is supported by multiprocessing.

        Parameters
        ----------
        mdf_path : list or tuple or str
            The path of the mdf files to run.
        disp : bool, optional
            Show simulation progress.
        netcdf : bool, optional
            Save simulation result as netcdf file.
        workers : int, optional
            Number of workers. If workers = 1, the simulations will run
            one by one. If workers > 1, the simulation will run in parallel
            and workers equal to the number of processes. If workers = -1,
            all cpu cores will be uesed.

        Examples
        ---------
        >>> import delft3d
        >>> sim = delft3d.Simulation('C:/Users/Carlisle/Desktop/62422/src/bin/x64')
        >>> sim.run('example/dflow1/f34.mdf')
        >>> sim.run('example/dflow1/f34.mdf', disp=True, netcdf=True)
        >>> sim.run(['example/dflow1/f34.mdf', 'example/dflow2/f342.mdf'])
        >>> sim.run(['example/dflow1/f34.mdf', 'example/dflow2/f342.mdf'], workers=2)

        """
        _run = FunctionWrapper(self.sim_unit, (disp, netcdf))
        if type(mdf_path) == str:
            mdf_path = [mdf_path]

        if workers == 1:
            # run one by one
            for sim in mdf_path:
                _run(sim)
        else:
            # run in parallel
            if workers == -1:
                pool = Pool()
            elif workers > 1:
                pool = Pool(workers)
            else:
                raise ValueError('workers number cannot be negative')
            pool.map(_run, mdf_path)

    def sim_unit(self, mdf_path, disp=True, netcdf=False):
        """
        Run Delft3D simulation. This is the base method of self.run.

        Parameters
        ----------
        mdf_path : str
            The path of the mdf file to run.
        disp : bool, optional
            Show simulation progress.
        netcdf : bool. optional
            Save simulation as netcdf file.

        """
        mdf_path = Path(mdf_path).absolute()
        run_id = np.random.randint(1, 10000,  size=1)
        # modify mdf to save result as netcdf file
        if netcdf:
            self.output_nc(mdf_path)
        # create xml
        self.create_xml(mdf_path, run_id)
        # create bat
        self.create_bat(mdf_path, run_id, disp=disp)
        # execute simulation
        switch_cwd = "cd %s" % mdf_path.parents[0]
        run = "run_%d.bat" % run_id
        command = " && ".join([switch_cwd, run])
        status = os.system(command)
        if status != 0:
            raise RuntimeError("Simulation failed")
        # remove xml file and bat file
        os.remove(mdf_path.parents[0] / ('config_d_hydro_%d.xml' % run_id))
        os.remove(mdf_path.parents[0] / ("run_%d.bat" % run_id))
        # restore mdf file
        if netcdf:
            mdf = MdfFile(mdf_path)
            del mdf.data['FlNcdf']
            mdf.to_file(mdf_path)

    @staticmethod
    def create_xml(mdf_path, run_id):
        """Create xml file for d_hydro.exe"""
        mdf_path = Path(mdf_path).absolute()
        # get xml template path
        module_path = Path(os.path.dirname(__file__))
        xml_path = module_path / 'config_d_hydro.xml'
        # edit xml
        delft3d_xml = xml.dom.minidom.parse("%s" % xml_path)
        mdf_file = delft3d_xml.getElementsByTagName('mdfFile')[0]
        mdf_file.childNodes[0].data = mdf_path.name
        url_file = delft3d_xml.getElementsByTagName('urlFile')[0]
        url_file.childNodes[0].data = mdf_path.name.replace('.mdf', '.url')
        # write xml
        project_xml_path = mdf_path.parents[0] / ('config_d_hydro_%d.xml' % run_id)
        with project_xml_path.open('w') as f:
            delft3d_xml.writexml(f)

    def create_bat(self, mdf_path, run_id, disp=True):
        """Create bat file to call d_hydro.exe to execute simulation"""
        mdf_path = Path(mdf_path).absolute()
        # create command
        echo_off = "@echo off"
        set_path = "set PATH=%s;%s" % (self.engine['dflow2d3d'], self.engine['share'])
        execute = "\"%s\" config_d_hydro_%d.xml" % (self.engine['d_hydro'], run_id)
        if not disp:
            # show simulation or not
            execute += ' > nul'
        bat = '\n'.join([echo_off, set_path, execute])
        # write bat
        bat_path = mdf_path.parents[0] / ("run_%d.bat" % run_id)
        with bat_path.open('w') as f:
            f.writelines(bat)

    @staticmethod
    def output_nc(mdf_path):
        """Modify mdf file to save simulation as netcdf file"""
        mdf = MdfFile(mdf_path)
        mdf.add_parm({'FlNcdf': 'map his dro fou'})
        mdf.to_file(mdf_path)


class FunctionWrapper(object):
    """
    Function wrapper for self.run method, allowing picklability.
    """
    def __init__(self, f, args):
        self.f = f
        self.args = [] if args is None else args

    def __call__(self, x):
        return self.f(x, *self.args)