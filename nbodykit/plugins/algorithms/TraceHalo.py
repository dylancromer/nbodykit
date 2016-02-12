import logging

import h5py

from nbodykit import files
from nbodykit import halos

import numpy
import mpsort
from mpi4py import MPI
from nbodykit.extensionpoints import Algorithm

class TraceHaloAlgorithm(Algorithm):

    plugin_name = "TraceHalo"
    
    @classmethod
    def register(kls):
        from nbodykit.extensionpoints import DataSource
        p = kls.parser
        p.description = " Calculate the halo property based on a different set of halo labels."

        p.add_argument("dest", type=DataSource.fromstring,
                help="type: DataSource")
        p.add_argument("source", type=DataSource.fromstring,
                help="type: DataSource")
        p.add_argument("sourcelabel", type=DataSource.fromstring,
                help='DataSource of the source halo label files, the Label column is used.')

    def run(self):
        comm = self.comm

        stats = {}
        [[ID]] = self.source.read(['ID'], stats, full=True)

        start = sum(comm.allgather(len(ID))[:comm.rank])
        end   = sum(comm.allgather(len(ID))[:comm.rank+1])
        data = numpy.empty(end - start, dtype=[
                    ('Label', ('i4')), 
                    ('ID', ('i8')), 
                    ])
        data['ID'] = ID
        del ID
        Ntot = stats['Ntot']
        [[data['Label'][...]]] = self.sourcelabel.read(['Label'], stats, full=True)

        mpsort.sort(data, orderby='ID')

        label = data['Label'].copy()
        del data

        data = numpy.empty(end - start, dtype=[
                    ('ID', ('i8')), 
                    ('Position', ('f4', 3)), 
                    ('Velocity', ('f4', 3)), 
                    ])
        [[data['Position'][...]]] = self.dest.read(['Position'], stats, full=True)
        [[data['Velocity'][...]]] = self.dest.read(['Velocity'], stats, full=True)
        [[data['ID'][...]]] = self.dest.read(['ID'], stats, full=True)
        mpsort.sort(data, orderby='ID')

        data['Position'] /= self.dest.BoxSize
        data['Velocity'] /= self.dest.BoxSize
        
        N = halos.count(label)
        hpos = halos.centerofmass(label, data['Position'], boxsize=1.0)
        hvel = halos.centerofmass(label, data['Velocity'], boxsize=None)
        return hpos, hvel, N, Ntot

    def save(self, output, data): 
        hpos, hvel, N, Ntot = data
        if self.comm.rank == 0:
            logging.info("Total number of halos: %d" % len(N))
            logging.info("N %s" % str(N))
            N[0] = 0
            with h5py.File(output, 'w') as ff:
                data = numpy.empty(shape=(len(N),), 
                    dtype=[
                    ('Position', ('f4', 3)),
                    ('Velocity', ('f4', 3)),
                    ('Length', 'i4')])
                
                data['Position'] = hpos
                data['Velocity'] = hvel
                data['Length'] = N
                
                # do not create dataset then fill because of
                # https://github.com/h5py/h5py/pull/606

                dataset = ff.create_dataset(
                    name='TracedFOFGroups', data=data
                    )
                dataset.attrs['Ntot'] = Ntot
                dataset.attrs['BoxSize'] = self.source.BoxSize
                dataset.attrs['source'] = self.source.string
                dataset.attrs['sourcelabel'] = self.sourcelabel.string
                dataset.attrs['dest'] = self.dest.string

            logging.info("Written %s" % output)
