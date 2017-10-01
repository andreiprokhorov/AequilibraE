"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       AequilibraE Database
 Purpose:    Implements a class to represent flat databases with an unique id field.
             It is really just a wrapper around numpy recarray memmap

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-06-25
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import numpy as np
import uuid
import tempfile
import os
from numpy.lib.format import open_memmap

# Necessary in case we are no the QGIS world
# try:
#     from common_tools.auxiliary_functions import logger
# except:
#     pass

MEMORY = 1
DISK = 0

class AequilibraEData(object):
    def __init__(self):
        self.data = None
        self.file_path = None
        self.entries = None
        self.fields = None
        self.num_fields = None
        self.data_types = None
        self.aeq_index_type = None
        self.memory_mode = None

    def create_empty(self, file_path=None, entries=1, field_names=None, data_types=None, memory_mode=False):

        if file_path is not None or memory_mode:
            if field_names is None:
                field_names = ['data']

            if data_types is None:
                data_types = [np.float64]

            self.file_path = file_path
            self.entries = entries
            self.fields = field_names
            self.data_types = data_types
            self.aeq_index_type = np.int64

            if memory_mode:
                self.memory_mode = MEMORY
            else:
                self.memory_mode = DISK
                if self.file_path is None:
                    self.file_path = self.random_name()

            # Consistency checks
            if not isinstance(self.fields, list):
                raise ValueError('Titles for fields, "field_names", needs to be a list')

            if not isinstance(self.data_types, list):
                raise ValueError('Data types, "data_types", needs to be a list')
            # The check below is not working properly with the QGIS importer
            # else:
            #     for dt in self.data_types:
            #         if not isinstance(dt, type):
            #             raise ValueError('Data types need to be Python or Numpy data types')

            for field in self.fields:
                if field in object.__dict__:
                    raise Exception(field + ' is a reserved name. You cannot use it as a field name')

            self.num_fields = len(self.fields)

            dtype = [('index', self.aeq_index_type)]
            dtype.extend([(self.fields[i].encode('utf-8'), self.data_types[i]) for i in range(self.num_fields)])

            # the file
            if self.memory_mode:
                self.data = np.recarray((self.entries,), dtype=dtype)
            else:
                self.data = open_memmap(self.file_path, mode='w+', dtype=dtype, shape=(self.entries,))

    def __getattr__(self, field_name):

        if field_name in object.__dict__:
            return self.__dict__[field_name]

        if self.data is not None:
            if field_name in self.fields:
                return self.data[field_name]

            if field_name == 'index':
                return self.data['index']

            raise AttributeError("No such method or data field! --> " + str(field_name))
        else:
            raise AttributeError("Data container is empty")

    def load(self, file_path):
        f = open(file_path)
        self.file_path = os.path.realpath(f.name)
        f.close()

        # Map in memory and load matrix_procedures names plus dimensions
        self.data = open_memmap(self.file_path, mode='r+')

        self.entries = self.data.shape[0]
        self.fields = [x for x in self.data.dtype.fields if x != 'index']
        self.num_fields = len(self.fields)
        self.data_types = [self.data[x].dtype.type for x in self.fields]

    @staticmethod
    def random_name():
        return os.path.join(tempfile.gettempdir(), 'Aequilibrae_data_' + str(uuid.uuid4()) + '.aed')