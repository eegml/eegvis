# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import, unicode_literals
import pdb
"""
this set of montage derivations are useful when the channel names are in the simplified format
['EEG FP1',
 'EEG FP2',
 'EEG F3',
 'EEG F4',
 'EEG C3',
 'EEG C4',
 'EEG P3',
 'EEG P4',
 'EEG O1',
 'EEG O2',
 'EEG F7',
 'EEG F8',
 'EEG T3',
 'EEG T4',
 'EEG T5',
 'EEG T6',
 'EEG T1',
 'EEG T2',
 'EEG FZ',
 'EEG CZ',
 'EEG PZ',
 'EEG EKG1',
 'EEG SP1',
 'EEG SP2',
 'EMG',
 'EEG A1',
 'EEG A2',
 'IBI',
 'BURSTS',
 'SUPPR']

Note this does not specify the reference, so is not quite "Standard Text" for edf
so I'll called this the "edf-simplified" form. Hopefully we can get rid of this when things are put into canonical form.

In clinical EEG a montage is what we will call a montage view (MontageView)
here. It is generally a linear combinations of the originnal electrodes chosen to
make it easier to see features. 

Each one will have different advantages and disadvantages. Bipolar
montages are less sensitive to noise. Average or referential montages
may be more sensitive or make it easier to view generalized
discharges. One montage may make localizing temporal events easier
while another focuses on occipital events.  """

# start with a few hard-coded montages:
# [x] double banana, [x] TCP, [x] laplacian
# [x] DB-avg, [x] DB-ref, [ ] sphenoidal [ ] circle

# thoughts: want to have core names for signals which are standard then some
# optional ones which we try to add if possible: EKG, EMG, Resp PG1 or RUC LLC,
# extra leads

import pdb
from collections import OrderedDict
import numpy as np
import xarray
import eegvis.montageview as montageview


def double_banana_set_matrix(V):
    """specify the double banana transformation for raw input labels
    return an xarray-like matrix V ?"""
    # N = len(rec_labels)
    # M = len(DB_LABELS)
    # up_db_labels = DB_LABELS.upcase()
    # up_rec_labels = rec_labels.upcase()
    # V = xarray.DataArray(
    #     np.zeros(shape=(M, N)),
    #     dims=('x', 'y'),
    #     coords={'x': up_db_labels,
    #             'y': up_rec_labels})

    V.loc["Fp1-F7", "EEG FP1"] = 1
    V.loc["Fp1-F7", "EEG F7"] = -1
    V.loc["F7-T3", "EEG F7"] = 1
    V.loc["F7-T3", "EEG T3"] = -1
    V.loc["T3-T5", "EEG T3"] = 1
    V.loc["T3-T5", "EEG T5"] = -1
    V.loc["T5-O1", "EEG T5"] = 1
    V.loc["T5-O1", "EEG O1"] = -1

    V.loc["Fp2-F8", "EEG FP2"] = 1
    V.loc["Fp2-F8", "EEG F8"] = -1
    V.loc["F8-T4", "EEG F8"] = 1
    V.loc["F8-T4", "EEG T4"] = -1
    V.loc["T4-T6", "EEG T4"] = 1
    V.loc["T4-T6", "EEG T6"] = -1
    V.loc["T6-O2", "EEG T6"] = 1
    V.loc["T6-O2", "EEG O2"] = -1

    V.loc["Fp1-F3", "EEG FP1"] = 1
    V.loc["Fp1-F3", "EEG F3"] = -1
    V.loc["F3-C3", "EEG F3"] = 1
    V.loc["F3-C3", "EEG C3"] = -1
    V.loc["C3-P3", "EEG C3"] = 1
    V.loc["C3-P3", "EEG P3"] = -1
    V.loc["P3-O1", "EEG P3"] = 1
    V.loc["P3-O1", "EEG O1"] = -1

    V.loc["Fp2-F4", "EEG FP2"] = 1
    V.loc["Fp2-F4", "EEG F4"] = -1
    V.loc["F4-C4", "EEG F4"] = 1
    V.loc["F4-C4", "EEG C4"] = -1
    V.loc["C4-P4", "EEG C4"] = 1
    V.loc["C4-P4", "EEG P4"] = -1
    V.loc["P4-O2", "EEG P4"] = 1
    V.loc["P4-O2", "EEG O2"] = -1

    V.loc["Fz-Cz", "EEG FZ"] = 1
    V.loc["Fz-Cz", "EEG CZ"] = -1
    V.loc["Cz-Pz", "EEG CZ"] = 1
    V.loc["Cz-Pz", "EEG PZ"] = -1

    return V


class DoubleBananaMontageView(montageview.MontageView):
    """
    an example of using the MontageView
    useful, given how common this view

    we already know the montage_labels=DB_LABELS
    we just need to know the input recording labels

    then in the input method we call a function to define the connection matrix V

    *** NOTE this uses the clinical convention and reverses the polarity by default
    so that "up is negative" ***

    """

    DB_LABELS = [
        "Fp1-F7",
        "F7-T3",
        "T3-T5",
        "T5-O1",
        "Fp2-F8",
        "F8-T4",
        "T4-T6",
        "T6-O2",
        "Fp1-F3",
        "F3-C3",
        "C3-P3",
        "P3-O1",
        "Fp2-F4",
        "F4-C4",
        "C4-P4",
        "P4-O2",
        "Fz-Cz",
        "Cz-Pz",
    ]

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.DB_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )
        double_banana_set_matrix(self.V)  # define connection matrix

        if reversed_polarity:
            self.V = (-1) * self.V
        self.full_name = (
            "double banana, up=%s" % montageview.POSCHOICE[reversed_polarity]
        )
        self.name = "double banana"


class DBrefMontageView(montageview.MontageView):
    """This montage derivation uses the same electrodes as double banana but uses the as recorded reference
    so it is very simple
    """

    DBREF_LABELS_DISPLAY = [
        "Fp1-ref",
        "F7-ref",
        "T3-ref",
        "T5-ref",
        "O1-ref",
        "Fp2-ref",
        "F8-ref",
        "T4-ref",
        "T6-ref",
        "O2-ref",
        "F3-ref",
        "C3-ref",
        "P3-ref",
        "F4-ref",
        "C4-ref",
        "P4-ref",
        "Fz-ref",
        "Cz-ref",
        "Pz-ref",
    ]
    DBREF_LABELS = [
        "EEG FP1",
        "EEG F7",
        "EEG T3",
        "EEG T5",
        "EEG O1",
        "EEG FP2",
        "EEG F8",
        "EEG T4",
        "EEG T6",
        "EEG O2",
        "EEG F3",
        "EEG C3",
        "EEG P3",
        "EEG F4",
        "EEG C4",
        "EEG P4",
        "EEG FZ",
        "EEG CZ",
        "EEG PZ",
    ]

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.DBREF_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )
        self.set_matrix()
        if reversed_polarity:
            self.V = (-1) * self.V
        self.full_name = "db-ref, up=%s" % montageview.POSCHOICE[reversed_polarity]

    def set_matrix(self):
        """specify the double banana-inspired reference montage
        transformation for raw input labels
        this is very simple as we are assuming that the list of labels have the same
        name as their corresponding electrode label (self.rec_labels)
        """

        for label in self.montage_labels:
            self.V.loc[label, label] = 1


class LaplacianMontageView(montageview.MontageView):
    # try it first the way Persyst defines it
    # this ignores some channels (except as neighbors) e.g. Fp1/Fp2
    LAPLACIAN_LABELS = [
        "F7-aF7",
        "T3-aT3",
        "T5-aT5",
        "O1-aO1",
        "F3-aF3",
        "C3-aC3",
        "P3-aP3",
        "Cz-aCz",
        "F4-aF4",
        "C4-aC4",
        "P4-aP4",
        "F8-aF8",
        "T4-aT4",
        "T6-aT6",
        "O2-aO2",
    ]

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.LAPLACIAN_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )
        self.laplacian_set_matrix(self.V)  # define connection matrix

        if reversed_polarity:
            self.V = (-1) * self.V
        self.name = "laplacian"
        self.full_name = "%s, up=%s" % (
            self.name,
            montageview.POSCHOICE[reversed_polarity],
        )

    def laplacian_set_matrix(self, V):
        """expect an xarray-like matrix V"""

        V.loc["F7-aF7", "EEG F7"] = 1  # aF7 = Fp1+F3+C3+T3
        V.loc["F7-aF7", "EEG FP1"] = -1 / 4
        V.loc["F7-aF7", "EEG F3"] = -1 / 4
        V.loc["F7-aF7", "EEG C3"] = -1 / 4
        V.loc["F7-aF7", "EEG T3"] = -1 / 4

        V.loc["T3-aT3", "EEG T3"] = 1  # aT3 = F7+C3+T5
        V.loc["T3-aT3", "EEG F7"] = -1 / 3
        V.loc["T3-aT3", "EEG C3"] = -1 / 3
        V.loc["T3-aT3", "EEG T5"] = -1 / 3

        V.loc["T5-aT5", "EEG T5"] = 1  # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", "EEG T3"] = -1 / 4  # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", "EEG C3"] = -1 / 4  # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", "EEG P3"] = -1 / 4  # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", "EEG O1"] = -1 / 4  # aT5 = T3+C3+P3+O1

        V.loc["O1-aO1", "EEG O1"] = 1  # aO1 = "PZ+P3+T5"
        V.loc["O1-aO1", "EEG PZ"] = -1 / 3
        V.loc["O1-aO1", "EEG P3"] = -1 / 3
        V.loc["O1-aO1", "EEG T5"] = -1 / 3

        V.loc["F3-aF3", "EEG F3"] = 1  # "aF3" Definition="F7+C3+FZ+FP1"/>
        V.loc["F3-aF3", "EEG F7"] = -1 / 4
        V.loc["F3-aF3", "EEG C3"] = -1 / 4
        V.loc["F3-aF3", "EEG FZ"] = -1 / 4
        V.loc["F3-aF3", "EEG FP1"] = -1 / 4

        V.loc["C3-aC3", "EEG C3"] = 1  # <AvgRef Name="aC3" Definition="T3+F3+CZ+P3"/>
        V.loc["C3-aC3", "EEG T3"] = -1 / 4
        V.loc["C3-aC3", "EEG F3"] = -1 / 4
        V.loc["C3-aC3", "EEG CZ"] = -1 / 4
        V.loc["C3-aC3", "EEG P3"] = -1 / 4

        V.loc["P3-aP3", "EEG P3"] = 1.0  # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", "EEG C3"] = (
            -1 / 4
        )  # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", "EEG PZ"] = (
            -1 / 4
        )  # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", "EEG O1"] = (
            -1 / 4
        )  # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", "EEG T5"] = (
            -1 / 4
        )  # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>

        V.loc["Cz-aCz", "EEG CZ"] = 1  # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc["Cz-aCz", "EEG FZ"] = (
            -1 / 4
        )  # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc["Cz-aCz", "EEG C4"] = (
            -1 / 4
        )  # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc["Cz-aCz", "EEG PZ"] = (
            -1 / 4
        )  # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc["Cz-aCz", "EEG C3"] = (
            -1 / 4
        )  # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>

        V.loc["F4-aF4", "EEG F4"] = 1  # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", "EEG FP2"] = (
            -1 / 4
        )  # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", "EEG F8"] = (
            -1 / 4
        )  # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", "EEG C4"] = (
            -1 / 4
        )  # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", "EEG FZ"] = (
            -1 / 4
        )  # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>

        V.loc["C4-aC4", "EEG C4"] = 1.0  # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", "EEG F4"] = (
            -1 / 4
        )  # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", "EEG T4"] = (
            -1 / 4
        )  # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", "EEG P4"] = (
            -1 / 4
        )  # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", "EEG CZ"] = (
            -1 / 4
        )  # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>

        V.loc["P4-aP4", "EEG P4"] = 1
        V.loc["P4-aP4", "EEG C4"] = (
            -1 / 4
        )  # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc["P4-aP4", "EEG T6"] = (
            -1 / 4
        )  # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc["P4-aP4", "EEG O2"] = (
            -1 / 4
        )  # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc["P4-aP4", "EEG PZ"] = (
            -1 / 4
        )  # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>

        V.loc["F8-aF8", "EEG F8"] = 1  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc["F8-aF8", "EEG FP2"] = (
            -1 / 3
        )  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc["F8-aF8", "EEG F4"] = (
            -1 / 3
        )  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc["F8-aF8", "EEG T4"] = (
            -1 / 3
        )  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>

        V.loc["T4-aT4", "EEG T4"] = 1  # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc["T4-aT4", "EEG F8"] = -1 / 3  # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc["T4-aT4", "EEG C4"] = -1 / 3  # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc["T4-aT4", "EEG T6"] = -1 / 3  # <AvgRef Name="aT4" Definition="F8+C4+T6"/>

        V.loc["T6-aT6", "EEG T6"] = 1  # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc["T6-aT6", "EEG T4"] = -1 / 3  # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc["T6-aT6", "EEG P4"] = -1 / 3  # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc["T6-aT6", "EEG O2"] = -1 / 3  # <AvgRef Name="aT6" Definition="T4+P4+O2"/>

        V.loc["O2-aO2", "EEG O2"] = 1  # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc["O2-aO2", "EEG T6"] = -1 / 3  # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc["O2-aO2", "EEG P4"] = -1 / 3  # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc["O2-aO2", "EEG PZ"] = -1 / 3  # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        return V

    # <AvgRef Name="aF7" Definition="FP1+F3+C3+T3"/>
    # <AvgRef Name="aT3" Definition="F7+C3+T5"/>
    # <AvgRef Name="aT5" Definition="T3+C3+P3+O1"/>
    # <AvgRef Name="aF3" Definition="F7+C3+FZ+FP1"/>
    # <AvgRef Name="aC3" Definition="T3+F3+CZ+P3"/>
    # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
    # <AvgRef Name="aFpz" Definition="FP1+FZ+FP2"/>
    # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
    # <AvgRef Name="aOz" Definition="O1+PZ+O2"/>
    # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
    # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
    # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
    # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
    # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
    # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
    # <AvgRef Name="Av17" Definition="F7+F3+FZ+F4+F8+T3+C3+CZ+C4+T4+T5+P3+PZ+P4+T6+O1+O2"/>
    # <AvgRef Name="Av12" Definition="F3+F4+T3+C3+C4+T4+T5+P3+P4+T6+O1+O2"/>
    # <AvgRef Name="aO1" Definition="PZ+P3+T5"/>
    # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>


# EKG
# PG1
# PG2


#### TCP
class TCPMontageView(montageview.MontageView):
    TCP_LABELS = [
        "Fp1-F7",
        "F7-T3",
        "T3-T5",
        "T5-O1",
        "Fp2-F8",
        "F8-T4",
        "T4-T6",
        "T6-O2",
        "A1-T3",
        "T3-C3",
        "C3-Cz",
        "Cz-C4",
        "C4-T4",
        "T4-A2",
        "Fp1-F3",
        "F3-C3",
        "C3-P3",
        "Fp2-F4",
        "F4-C4",
        "C4-P4",
    ]

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.TCP_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )
        self.tcp_set_matrix(self.V)  # define connection matrix

        if reversed_polarity:
            self.V = (-1) * self.V

        self.name = "tcp"
        self.full_name = "%s, up=%s" % (
            self.name,
            montageview.POSCHOICE[reversed_polarity],
        )

    def tcp_set_matrix(self, V):
        V.loc["Fp1-F7", "EEG FP1"] = 1
        V.loc["Fp1-F7", "EEG F7"] = -1

        V.loc["F7-T3", "EEG F7"] = 1
        V.loc["F7-T3", "EEG T3"] = -1

        V.loc["T3-T5", "EEG T3"] = 1
        V.loc["T3-T5", "EEG T5"] = -1

        V.loc["T5-O1", "EEG T5"] = 1
        V.loc["T5-O1", "EEG O1"] = -1

        V.loc["Fp2-F8", "EEG FP2"] = 1
        V.loc["Fp2-F8", "EEG F8"] = -1

        V.loc["F8-T4", "EEG F8"] = 1
        V.loc["F8-T4", "EEG T4"] = -1

        V.loc["T4-T6", "EEG T4"] = 1
        V.loc["T4-T6", "EEG T6"] = -1

        V.loc["T6-O2", "EEG T6"] = 1
        V.loc["T6-O2", "EEG O2"] = -1

        V.loc["A1-T3", "EEG A1"] = 1
        V.loc["A1-T3", "EEG T3"] = -1

        V.loc["T3-C3", "EEG T3"] = 1
        V.loc["T3-C3", "EEG C3"] = -1

        V.loc["C3-Cz", "EEG C3"] = 1
        V.loc["C3-Cz", "EEG CZ"] = -1

        V.loc["Cz-C4", "EEG CZ"] = 1
        V.loc["Cz-C4", "EEG C4"] = -1

        V.loc["C4-T4", "EEG C4"] = 1
        V.loc["C4-T4", "EEG T4"] = -1

        V.loc["T4-A2", "EEG T4"] = 1
        V.loc["T4-A2", "EEG A2"] = -1

        V.loc["Fp1-F3", "EEG FP1"] = 1
        V.loc["Fp1-F3", "EEG F3"] = -1
        V.loc["F3-C3", "EEG F3"] = 1
        V.loc["F3-C3", "EEG C3"] = -1
        V.loc["C3-P3", "EEG C3"] = 1
        V.loc["C3-P3", "EEG P3"] = -1

        V.loc["Fp2-F4", "EEG FP2"] = 1
        V.loc["Fp2-F4", "EEG F4"] = -1
        V.loc["F4-C4", "EEG F4"] = 1
        V.loc["F4-C4", "EEG C4"] = -1
        V.loc["C4-P4", "EEG C4"] = 1
        V.loc["C4-P4", "EEG P4"] = -1


### A Neonatal montage (modified 10-20)
class NeonatalMontageView(montageview.MontageView):
    """
    10-20 montage modified for neonatal head sizes
    This is more or less Montage 1 in Shellhaas (2011) table 3 of
    https://www.acns.org/pdf/guidelines/Guideline-13.pdf plus it adds
    the [ 'T3-O1','O1-O2','O2-T4'] chain to visualize the occipital
    region a bit better. It is used at Stanford/LPCH for neonates around PMA ~24-44 weeks

       https://journals.lww.com/clinicalneurophys/fulltext/2011/12000/The_American_Clinical_Neurophysiology_Society_s.12.aspx?casa_token=_R8Fm9J6mp8AAAAA:OdoEUvYFNLVLg0Kr7WGN-j1sj5bHRvSsNf7EJP9NAFXLqbmCwGygbD9XQKEnIo2uU_PkzgInlBdfIZhlT4-UoLI

    """

    NEONATAL_LABELS = [
        "Fp1-T3",
        "T3-O1",
        "Fp2-T4",
        "T4-O2",
        "Fp1-C3",
        "C3-O1",
        "Fp2-C4",
        "C4-O2",
        "T3-C3",
        "C3-Cz",
        "Cz-C4",
        "C4-T4",
        "Fz-Cz",
        "Cz-Pz",
        "T3-O1",
        "O1-O2",
        "O2-T4",
    ]
    #'PG1-A1' # LLC
    #'PG2-A2'
    #'X3-X4' # EMG-CHIN
    #'X5-E'  # RESP
    #'X1-A1' # EKG

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.NEONATAL_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )
        self.neonatal_set_matrix(self.V)  # define connection matrix

        if reversed_polarity:
            self.V = (-1) * self.V

        self.name = "neonatal"
        self.full_name = "%s, up=%s" % (
            self.name,
            montageview.POSCHOICE[reversed_polarity],
        )

    def neonatal_set_matrix(self, V):
        # pdb.set_trace()
        V.loc["Fp1-T3", "EEG FP1"] = 1
        V.loc["Fp1-T3", "EEG T3"] = -1

        V.loc["T3-O1", "EEG T3"] = 1
        V.loc["T3-O1", "EEG O1"] = -1

        V.loc["Fp2-T4", "EEG FP2"] = 1
        V.loc["Fp2-T4", "EEG T4"] = -1

        V.loc["T4-O2", "EEG T4"] = 1
        V.loc["T4-O2", "EEG O2"] = -1

        V.loc["Fp1-C3", "EEG FP1"] = 1
        V.loc["Fp1-C3", "EEG C3"] = -1

        V.loc["C3-O1", "EEG C3"] = 1
        V.loc["C3-O1", "EEG O1"] = -1

        V.loc["Fp2-C4", "EEG FP2"] = 1
        V.loc["Fp2-C4", "EEG C4"] = -1

        V.loc["C4-O2", "EEG C4"] = 1
        V.loc["C4-O2", "EEG O2"] = -1

        V.loc["T3-C3", "EEG T3"] = 1
        V.loc["T3-C3", "EEG C3"] = -1

        V.loc["C3-Cz", "EEG C3"] = 1
        V.loc["C3-Cz", "EEG CZ"] = -1

        V.loc["Cz-C4", "EEG CZ"] = 1
        V.loc["Cz-C4", "EEG C4"] = -1

        V.loc["C4-T4", "EEG CZ"] = 1
        V.loc["C4-T4", "EEG T4"] = -1

        V.loc["C4-T4", "EEG C4"] = 1
        V.loc["C4-T4", "EEG T4"] = -1

        V.loc["Fz-Cz", "EEG FZ"] = 1
        V.loc["Fz-Cz", "EEG CZ"] = -1

        V.loc["T3-O1", "EEG T3"] = 1
        V.loc["T3-O1", "EEG O1"] = -1

        V.loc["O1-O2", "EEG O1"] = 1
        V.loc["O1-O2", "EEG O2"] = -1

        V.loc["O2-T4", "EEG O2"] = 1
        V.loc["O2-T4", "EEG T4"] = -1


####################

laplacian_xml = """
<Template Name="Laplacian" ClsId="{7B1FC068-2A13-11D3-809D-006008184043}">
<Defn ClassName="Montage">
<Channel Name="F7-aF7" Definition="F7-aF7" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="T3-aT3" Definition="T3-aT3" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="T5-aT5" Definition="T5-aT5" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="O1-aO1" Definition="O1-aO1" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="F3-aF3" Definition="F3-aF3" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="C3-aC3" Definition="C3-aC3" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="P3-aP3" Definition="P3-aP3" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="CZ-aCz" Definition="CZ-aCz" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="F4-aF4" Definition="F4-aF4" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="C4-aC4" Definition="C4-aC4" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="P4-aP4" Definition="P4-aP4" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="F8-aF8" Definition="F8-aF8" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="T4-aT4" Definition="T4-aT4" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="T6-aT6" Definition="T6-aT6" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<Channel Name="O2-aO2" Definition="O2-aO2" MasterControl="1" PenColor="0" OverlapPrevious="0"/>
<AvgRef Name="aF7" Definition="FP1+F3+C3+T3"/>
<AvgRef Name="aT3" Definition="F7+C3+T5"/>
<AvgRef Name="aT5" Definition="T3+C3+P3+O1"/>
<AvgRef Name="aF3" Definition="F7+C3+FZ+FP1"/>
<AvgRef Name="aC3" Definition="T3+F3+CZ+P3"/>
<AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
<AvgRef Name="aFpz" Definition="FP1+FZ+FP2"/>
<AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
<AvgRef Name="aOz" Definition="O1+PZ+O2"/>
<AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
<AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
<AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
<AvgRef Name="aF8" Definition="FP2+F4+T4"/>
<AvgRef Name="aT4" Definition="F8+C4+T6"/>
<AvgRef Name="aT6" Definition="T4+P4+O2"/>
<AvgRef Name="Av17" Definition="F7+F3+FZ+F4+F8+T3+C3+CZ+C4+T4+T5+P3+PZ+P4+T6+O1+O2"/>
<AvgRef Name="Av12" Definition="F3+F4+T3+C3+C4+T4+T5+P3+P4+T6+O1+O2"/>
<AvgRef Name="aO1" Definition="PZ+P3+T5"/>
<AvgRef Name="aO2" Definition="T6+P4+PZ"/>
"""


class CommonAvgRefMontageView(montageview.MontageView):
    """
    I can think of various ways to define this. For starters
    will have one which uses a specific set of 10-20 channels that are common

    and another "generic one" which uses all the identified channels by default
    """

    CAR_LABELS = [
        "Fp1-AVG",
        "F7-AVG",
        "T3-AVG",
        "T5-AVG",
        # spacer
        "Fp2-AVG",
        "F8-AVG",
        "T4-AVG",
        "T6-AVG",
        #
        "Fp1-AVG",
        "F3-AVG",
        "C3-AVG",
        "P3-AVG",
        "O1-AVG",
        #
        "Fp2-AVG",
        "F4-AVG",
        "C4-AVG",
        "P4-AVG",
        "O2-AVG",
        #
        "Fz-AVG",
        "Cz-AVG",
        "Pz-AVG",
    ]
    AVG_REFERENCE_LABELS = list(
        set(
            [  # electrodes used to calculate the average reference
                "EEG FP1",
                "EEG F7",
                "EEG T3",
                "EEG T5",
                # spacer
                "EEG FP2",
                "EEG F8",
                "EEG T4",
                "EEG T6",
                #
                "EEG FP1",
                "EEG F3",
                "EEG C3",
                "EEG P3",
                "EEG O1",
                #
                "EEG FP2",
                "EEG F4",
                "EEG C4",
                "EEG P4",
                "EEG O2",
                #
                "EEG FZ",
                "EEG CZ",
                "EEG PZ",
            ]
        )
    )
    # should I include A1 and A2? sometimes T1/T2 (FT9/FT10)

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(
            self.CAR_LABELS, rec_labels, reversed_polarity=reversed_polarity
        )

        self.set_matrix(self.V)
        if reversed_polarity:
            self.V = (-1) * self.V

        self.name = "avg"  # or common average reference ?
        self.full_name = "%s, up=%s" % (
            self.name,
            montageview.POSCHOICE[reversed_polarity],
        )

    def setall_to_avg(self, V):
        """note this overwrites all values of matrix, so do this first"""
        N = (
            len(self.AVG_REFERENCE_LABELS) - 1
        )  # is this right ? or should it be the full N, as it is it is the avg of all the other electrodes
        avg = 1.0 / N
        for label in self.CAR_LABELS:
            V.loc[label, :] = -avg

    def set_matrix(self, V):
        self.setall_to_avg(V)

        V.loc["Fp1-AVG", "EEG FP1"] = 1
        V.loc["F7-AVG", "EEG F7"] = 1
        V.loc["T3-AVG", "EEG T3"] = 1
        V.loc["T5-AVG", "EEG T5"] = 1
        V.loc["O1-AVG", "EEG O1"] = 1

        V.loc["Fp2-AVG", "EEG FP2"] = 1
        V.loc["F8-AVG", "EEG F8"] = 1
        V.loc["T4-AVG", "EEG T4"] = 1
        V.loc["T6-AVG", "EEG T6"] = 1
        V.loc["O2-AVG", "EEG O2"] = 1

        V.loc["F3-AVG", "EEG F3"] = 1
        V.loc["C3-AVG", "EEG C3"] = 1
        V.loc["P3-AVG", "EEG P3"] = 1

        V.loc["F4-AVG", "EEG F4"] = 1
        V.loc["C4-AVG", "EEG C4"] = 1
        V.loc["P4-AVG", "EEG P4"] = 1

        V.loc["Fz-AVG", "EEG FZ"] = 1
        V.loc["Cz-AVG", "EEG CZ"] = 1
        V.loc["Pz-AVG", "EEG PZ"] = 1


# these are montageview factor functions which require a spcific channel label list
EDF_SIMPLIFIED_MONTAGE_BUILTINS = OrderedDict(
    [
        ("trace", montageview.TraceMontageView),
        ("tcp", TCPMontageView),
        ("double banana", DoubleBananaMontageView),
        ("laplacian", LaplacianMontageView),
        ("neonatal", NeonatalMontageView),
        ("DBref", DBrefMontageView),
    ]
)


if __name__ == "__main__":
    pass
    # print("with ipython 0.10 run this with ipython -wthread")
    # print("with ipython 0.11 run with ipython --pylab=wx")
    # print("run montages.py")
    # print("display_10_10_on_sphere()")
    # print("mlab.show()")
    # print("""might also want to try: nx.draw_spectral(G20)""")

    # import mayavi.mlab as mlab
    # display_10_10_on_sphere()
    # display_10_5_on_sphere()
    # mlab.show()
