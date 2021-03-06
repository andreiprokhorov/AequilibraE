"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loads matrix from file/layer
 Purpose:    Loads GUI for loading matrix from differencet sources

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    2017-06-07
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4 import QtGui, uic
from scipy.sparse import coo_matrix
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import numpy as np

import sys
import os
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from get_output_file_name import GetOutputFileName
from load_matrix_class import LoadMatrix

no_omx = False
try:
    import openmatrix as omx
except:
    no_omx = True

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_matrix_loader.ui'))


class LoadMatrixDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, sparse=False):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.sparse = sparse
        self.layer = None
        self.orig = None
        self.dest = None
        self.cells = None
        self.matrix = None
        self.error = None

        self.load.setEnabled(False)
        self.radio_layer_matrix.clicked.connect(self.change_matrix_type)
        self.radio_npy_matrix.clicked.connect(self.change_matrix_type)
        self.radio_omx_matrix.clicked.connect(self.change_matrix_type)

        # For changing the network layer
        self.matrix_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # For adding skims
        self.load.clicked.connect(self.load_the_matrix)

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if 'wkbType' in dir(layer):
                if layer.wkbType() == 100:
                    self.matrix_layer.addItem(layer.name())

        if no_omx:
            self.radio_omx_matrix.setEnabled(False)

    def change_matrix_type(self):
        self.load.setEnabled(True)
        members = [self.lbl_matrix, self.lbl_from, self.matrix_layer, self.field_from]
        all_members = members + [self.lbl_to, self.lbl_flow, self.field_to, self.field_cells]

        # Covers the Numpy option (minimizes the code length this way)
        for member in all_members:
            member.setVisible(False)

        if self.radio_layer_matrix.isChecked():
            self.lbl_matrix.setText('Matrix')
            self.lbl_from.setText('From')
            for member in all_members:
                member.setVisible(True)
            self.load_fields_to_combo_boxes()

        if self.radio_omx_matrix.isChecked():
            self.lbl_matrix.setText('Matrix core')
            self.lbl_from.setText('Indices')
            for member in members:
                member.setVisible(True)

    def load_fields_to_combo_boxes(self):
        self.load.setEnabled(False)
        for combo in [self.field_from, self.field_to, self.field_cells]:
            combo.clear()

        if self.matrix_layer.currentIndex() >= 0:
            self.load.setEnabled(True)
            self.layer = get_vector_layer_by_name(self.matrix_layer.currentText())
            for field in self.layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.field_from.addItem(field.name())
                    self.field_to.addItem(field.name())
                    self.field_cells.addItem(field.name())
                if field.type() in float_types:
                    self.field_cells.addItem(field.name())

    def run_thread(self):

        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.finished_threaded_procedure)

        self.load.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar.setValue(val)

    def finished_threaded_procedure(self, param):
        self.load.setEnabled(True)
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error while loading matrix:", self.worker_thread.error,
                                                      level=1)
        else:
            self.matrix = self.worker_thread.matrix
            self.exit_procedure()

    def load_the_matrix(self):  # CREATING GRAPH
        self.error = None

        if self.radio_layer_matrix.isChecked():
            if self.field_from.currentIndex() < 0 or self.field_from.currentIndex() < 0 or self.field_cells.currentIndex() < 0:
                self.error = 'Invalid field chosen'

            if self.error is None:
                idx1 = self.layer.fieldNameIndex(self.field_from.currentText())
                idx2 = self.layer.fieldNameIndex(self.field_to.currentText())
                idx3 = self.layer.fieldNameIndex(self.field_cells.currentText())
                idx = [idx1, idx2, idx3]

                self.worker_thread = LoadMatrix(qgis.utils.iface.mainWindow(), layer=self.layer, idx=idx,
                                                sparse=self.sparse, mapped_array=self.return_memory_mapped.isChecked())
                self.run_thread()

        if self.radio_npy_matrix.isChecked():

            file_types = ["NumPY array(*.npy)"]
            default_type = '.npy'
            box_name = 'Matrix Loader'
            new_name, type = GetOutputFileName(self, box_name, file_types, default_type, self.path)

            try:
                matrix = np.load(new_name)
                if len(matrix.shape[:]) == 2:
                    if self.sparse:
                        self.matrix = coo_matrix(matrix)
                    else:
                        self.matrix = matrix
                    self.exit_procedure()
                else:
                    self.error = 'Numpy array needs to be 2 dimensional. Matrix provided has ' + str(len(matrix.shape[:]))
            except:
                pass

        if self.radio_omx_matrix.isChecked():
            pass
            # Still not implemented

        if self.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Error:", self.error, level=1)

    def exit_procedure(self):
        self.close()
