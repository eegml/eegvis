# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import, unicode_literals
"""
In clinical EEG a montage is what we will call a montage view (MontageView)
here. It is generally a linear combinations of the originnal electrodes chosen to
OPmake it easier to see clinear features. Each one will have different advantages
and disadvantages. Bipolar montages are less sensitive to noise. Average or
referential montages may be more sensitive or make it easier to view generalized
discharges. One montage may make localizing temporal events easier while another
focuses on occipital events.
"""
import numpy as np
import xarray

# Anyone may wish to define a montageview, but there are quite a few standard ones
# to define these we need a standard ordering of electrodes in which to define them.

DOUBLE_BANANA = """
Fp1-F7
F7-T3
T3-T5
T5-O1

Fp2-F8
F8-T4
T4-T6
T6-O2

Fp1-F3
F3-C3
C3-P3
P3-O1

Fp2-F4
F4-C4
C4-P4
P4-O2

Fz-Cz
Cz-Pz
"""
DB_LABELS = [
    'Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2',
    'Fp1-F3', 'F3-C3', 'C3-P3', 'P3-O1', 'Fp2-F4', 'F4-C4', 'C4-P4', 'P4-O2',
    'Fz-Cz', 'Cz-Pz'
]

eye_leads_ekg = """
PG1
PG2
EKG
"""

TCP = """
Fp1-F7
F7-T3
T3-T5
T5-O1

Fp2-F8
F8-T4
T4-T6
T6-O2

A1-T3
T3-C3
C3-Cz
Cz-C4
C4-T4
T4-A2

Fp1-F3
F3-C3
C3-P3

Fp2-F4
F4-C4
C4-P4
"""
TCP_LABELS = [
    'Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2',
    'A1-T3', 'T3-C3', 'C3-Cz', 'Cz-C4', 'C4-T4', 'T4-A2', 'Fp1-F3', 'F3-C3',
    'C3-P3', 'Fp2-F4', 'F4-C4', 'C4-P4'
]


#---------------------------------------------------------------
# raw_labels -> montage_labels
# N=len(raw_labels) >= M = len(montage_labels)

def standard2shortname(labels):
    """
    @labels list of strings labeling the electrodes
    change the standard EDF text names for EEG to their shorter names
    "EEG Fp1" -> "Fp1"
    """
    return [ss.replace('EEG ','') for ss in labels]

class MontageView(object):
    """
    MontageView
    allows for definition of a linear transformation between a set of coordinates
    which are the electrodes of an EEG, say for example in an ECOG or in the
    10-20 or 10-5 systems. These usually represent a signal as recorded (vs some
    reference) @rec_label

    These are then mapped via linear combinations into the montage view @montage_labels

    This linear transformation is defined in the xarray matrix V

    For example in the bipolar double banana montage the electrodes 
    Fp1 and F7 are combined into (Fp1 - F7)

    """
    def __init__(self, montage_labels, rec_labels, **kwargs):
        self.rec_labels = rec_labels
        self.montage_labels = montage_labels
        self.name = kwargs['name'] if 'name' in kwargs else ''
        N = len(rec_labels)
        M = len(montage_labels)
        self.shape = (M,N)
        V = xarray.DataArray(
            np.zeros(shape=(M, N)),
            dims=('x', 'y'),
            coords={'x': montage_labels,
                    'y': rec_labels})
        
        self.V = V
        #  standard text (i.e. with
        # label-2-standard-index enumerate them
        # l2si = {elabels[ii]: ii for ii in range(len(elabels))}

    # alternatively it may make sense to simply use xarray to define the x,y coordinates
    def __call__(self, sx, sy):
        """
        matrix access via labels translate from label s1 (basis) to s2 (basis)
        """
        #sx = sx.upcase() # maybe, maybe not
        #sy = sy.upcase()
        return self.V.loc[sx, sy]


# V defaults  to 0, using clinical 10-20 system


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

    V.loc['Fp1-F7', 'Fp1'] = 1
    V.loc['Fp1-F7', 'F7'] = -1
    V.loc['F7-T3', 'F7'] = 1
    V.loc['F7-T3', 'T3'] = -1
    V.loc['T3-T5', 'T3'] = 1
    V.loc['T3-T5', 'T5'] = -1
    V.loc['T5-O1', 'T5'] = 1
    V.loc['T5-O1', 'O1'] = -1

    V.loc['Fp2-F8', 'Fp2'] = 1
    V.loc['Fp2-F8', 'F8'] = -1
    V.loc['F8-T4', 'F8'] = 1
    V.loc['F8-T4', 'T4'] = -1
    V.loc['T4-T6', 'T4'] = 1
    V.loc['T4-T6', 'T6'] = -1
    V.loc['T6-O2', 'T6'] = 1
    V.loc['T6-O2', 'O2'] = -1

    V.loc['Fp1-F3', 'Fp1'] = 1
    V.loc['Fp1-F3', 'F3'] = -1
    V.loc['F3-C3', 'F3'] = 1
    V.loc['F3-C3', 'C3'] = -1
    V.loc['C3-P3', 'C3'] = 1
    V.loc['C3-P3', 'P3'] = -1
    V.loc['P3-O1', 'P3'] = 1
    V.loc['P3-O1', 'O1'] = -1

    V.loc['Fp2-F4', 'Fp2'] = 1
    V.loc['Fp2-F4', 'F4'] = -1
    V.loc['F4-C4', 'F4'] = 1
    V.loc['F4-C4', 'C4'] = -1
    V.loc['C4-P4', 'C4'] = 1
    V.loc['C4-P4', 'P4'] = -1
    V.loc['P4-O2', 'P4'] = 1
    V.loc['P4-O2', 'O2'] = -1

    V.loc['Fz-Cz', 'Fz'] = 1
    V.loc['Fz-Cz', 'Cz'] = -1
    V.loc['Cz-Pz', 'Cz'] = 1
    V.loc['Cz-Pz', 'Pz'] = -1

    return V

class DoubleBananaMontageView(MontageView):
    """
    an example of using the MontageView
    useful, given how common this view

    we already know the montage_labels=DB_LABELS
    we just need to know the input recording labels

    then in the input method we call a function to define the connection matrix V

    *** NOTE this uses the clinical convention and reverses the polarity by default
    so that "up is negative" ***
    
    """
    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(DB_LABELS, rec_labels)
        double_banana_set_matrix(self.V) # define connection matrix
        poschoice = {
            False : 'pos',
            True : 'neg'}
        if reversed_polarity:
            self.V = (-1) * self.V
        self.name = 'double banana, up=%s' % poschoice[reversed_polarity]


class LaplacianMontageView(MontageView):
    # try it first the way Persyst defines it
    # this ignores some channels (except as neighbors) e.g. Fp1/Fp2
    LAPLACIAN_LABELS = [
        'F7-aF7',
        'T3-aT3',
        'T5-aT5',
        "O1-aO1",
        'F3-aF3',
        'C3-aC3',
        'P3-aP3',
        'Cz-aCz',
        'F4-aF4',
        'C4-aC4',
        'P4-aP4',
        'F8-aF8',
        'T4-aT4',
        'T6-aT6',
        'O2-aO2' ]

    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(self.LAPLACIAN_LABELS, rec_labels)
        self.laplacian_set_matrix(self.V) # define connection matrix
        
        poschoice = {
            False : 'pos',
            True : 'neg'}
        if reversed_polarity:
            self.V = (-1) * self.V

        self.name = 'laplacian, up=%s' % poschoice[reversed_polarity]


    def laplacian_set_matrix(self,V):
        """expect an xarray-like matrix V"""

        V.loc['F7-aF7', 'F7'] = 1 # aF7 = Fp1+F3+C3+T3
        V.loc['F7-aF7', 'Fp1'] = -1/4
        V.loc['F7-aF7', 'F3'] = -1/4
        V.loc['F7-aF7', 'C3'] = -1/4
        V.loc['F7-aF7', 'T3'] = -1/4

        V.loc['T3-aT3', 'T3'] = 1 # aT3 = F7+C3+T5
        V.loc['T3-aT3', 'F7'] = -1/3
        V.loc['T3-aT3', 'C3'] = -1/3
        V.loc['T3-aT3', 'T5'] = -1/3

        V.loc['T5-aT5', 'T5'] = 1 # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", 'T3'] = -1/4 # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", 'C3'] = -1/4 # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", 'P3'] = -1/4 # aT5 = T3+C3+P3+O1
        V.loc["T5-aT5", 'O1'] = -1/4 # aT5 = T3+C3+P3+O1

        V.loc["O1-aO1", 'O1'] = 1 # aO1 = "PZ+P3+T5"
        V.loc['O1-aO1', 'Pz'] = -1/3
        V.loc['O1-aO1', 'P3'] = -1/3
        V.loc['O1-aO1', 'T5'] = -1/3

        V.loc['F3-aF3', 'F3'] = 1 #"aF3" Definition="F7+C3+FZ+FP1"/>
        V.loc['F3-aF3', 'F7'] = -1/4
        V.loc['F3-aF3', 'C3'] = -1/4
        V.loc['F3-aF3', 'Fz'] = -1/4
        V.loc['F3-aF3', 'Fp1'] = -1/4

        V.loc['C3-aC3', 'C3'] = 1 # <AvgRef Name="aC3" Definition="T3+F3+CZ+P3"/>
        V.loc['C3-aC3', 'T3'] = -1/4
        V.loc['C3-aC3', 'F3'] = -1/4
        V.loc['C3-aC3', 'Cz'] = -1/4
        V.loc['C3-aC3', 'P3'] = -1/4

        V.loc["P3-aP3", 'P3'] = 1.0     # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", 'C3'] = -1/4     # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", 'Pz'] = -1/4     # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", 'O1'] = -1/4     # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>
        V.loc["P3-aP3", 'T5'] = -1/4     # <AvgRef Name="aP3" Definition="C3+PZ+O1+T5"/>

        V.loc['Cz-aCz', 'Cz'] = 1 # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc['Cz-aCz', 'Fz'] = -1/4 # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc['Cz-aCz', 'C4'] = -1/4 # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc['Cz-aCz', 'Pz'] = -1/4 # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>
        V.loc['Cz-aCz', 'C3'] = -1/4 # <AvgRef Name="aCz" Definition="FZ+C4+PZ+C3"/>

        V.loc["F4-aF4", 'F4'] = 1     # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", 'Fp2'] = -1/4 # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", 'F8'] = -1/4 # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", 'C4'] = -1/4 # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>
        V.loc["F4-aF4", 'Fz'] = -1/4 # <AvgRef Name="aF4" Definition="FP2+F8+C4+FZ"/>


        V.loc["C4-aC4", 'C4'] = 1.0     # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", 'F4'] = -1/4     # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", 'T4'] = -1/4     # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", 'P4'] = -1/4     # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>
        V.loc["C4-aC4", 'Cz'] = -1/4     # <AvgRef Name="aC4" Definition="F4+T4+P4+CZ"/>

        V.loc["P4-aP4", 'P4'] = 1
        V.loc['P4-aP4', 'C4'] = -1/4     # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc['P4-aP4', 'T6'] = -1/4     # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc['P4-aP4', 'O2'] = -1/4     # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>
        V.loc['P4-aP4', 'Pz'] = -1/4     # <AvgRef Name="aP4" Definition="C4+T6+O2+PZ"/>

        V.loc['F8-aF8', 'F8'] = 1     # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc['F8-aF8', 'Fp2'] = 1/3  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc['F8-aF8', 'F4'] = 1/3  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>
        V.loc['F8-aF8', 'T4'] = 1/3  # <AvgRef Name="aF8" Definition="FP2+F4+T4"/>

        V.loc['T4-aT4', 'T4'] = 1    # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc['T4-aT4', 'F8'] = -1/3 # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc['T4-aT4', 'C4'] = -1/3 # <AvgRef Name="aT4" Definition="F8+C4+T6"/>
        V.loc['T4-aT4', 'T6'] = -1/3 # <AvgRef Name="aT4" Definition="F8+C4+T6"/>

        V.loc['T6-aT6', 'T6'] = 1    # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc['T6-aT6', 'T4'] = -1/3 # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc['T6-aT6', 'P4'] = -1/3 # <AvgRef Name="aT6" Definition="T4+P4+O2"/>
        V.loc['T6-aT6', 'O2'] = -1/3 # <AvgRef Name="aT6" Definition="T4+P4+O2"/>

        V.loc['O2-aO2', 'O2'] = 1    # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc['O2-aO2', 'T6'] = -1/3 # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc['O2-aO2', 'P4'] = -1/3 # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
        V.loc['O2-aO2', 'Pz'] = -1/3 # <AvgRef Name="aO2" Definition="T6+P4+PZ"/>
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
class TCPMontageView(MontageView):
    TCP_LABELS = [
        'Fp1-F7',
        'F7-T3',
        'T3-T5',
        'T5-O1',

        'Fp2-F8',
        'F8-T4',
        'T4-T6',
        'T6-O2'

        'A1-T3',
        'T3-C3',
        'C3-Cz',
        'Cz-C4',
        'C4-T4',
        'T4-A2',

        'Fp1-F3',
        'F3-C3',
        'C3-P3',

        'Fp2-F4',
        'F4-C4',
        'C4-P4' ]
    
    def __init__(self, rec_labels, reversed_polarity=True):
        super().__init__(self.LAPLACIAN_LABELS, rec_labels)
        self.laplacian_set_matrix(self.V) # define connection matrix
        
        poschoice = {
            False : 'pos',
            True : 'neg'}
        if reversed_polarity:
            self.V = (-1) * self.V

        self.name = 'laplacian, up=%s' % poschoice[reversed_polarity]


def tcp_set_matrix(V):
    V.loc['Fp1-F7', 'Fp1'] = 1
    V.loc['Fp1-F7', 'F7'] = -1

    V.loc['F7-T3', 'F7'] = 1
    V.loc['F7-T3', 'T3'] = -1

    V.loc['T3-T5', 'T3'] = 1
    V.loc['T3-T5', 'T5'] = -1

    V.loc['T5-O1', 'T5'] = 1
    V.loc['T5-O1', 'O1'] = -1

    V.loc['Fp2-F8', 'Fp2'] = 1
    V.loc['Fp2-F8', 'F8'] = -1

    V.loc['F8-T4', 'F8'] = 1
    V.loc['F8-T4', 'T4'] = -1

    V.loc['T4-T6', 'T4'] = 1
    V.loc['T4-T6', 'T6'] = -1

    V.loc['T6-O2', 'T6'] = 1
    V.loc['T6-O2', '02'] = -1


    V.loc['A1-T3', 'A1'] = 1
    V.loc['A1-T3', 'T3'] = -1

    V.loc['T3-C3', 'T3'] = 1
    V.loc['T3-C3', 'C3'] = -1

    V.loc['C3-Cz', 'C3'] = 1
    V.loc['C3-Cz', 'Cz'] = -1

    V.loc['Cz-C4', 'Cz'] = 1
    V.loc['Cz-C4', 'C4'] = -1

    V.loc['C4-T4', 'C4'] = 1
    V.loc['C4-T4', 'T4'] = -1

    V.loc['T4-A2', 'T4'] = 1
    V.loc['T4-A2', 'A2'] = -1

    
    V.loc['Fp1-F3', 'Fp1'] = 1
    V.loc['Fp1-F3', 'F3'] = -1
    V.loc['F3-C3', 'F3'] = 1
    V.loc['F3-C3', 'C3'] = -1
    V.loc['C3-P3', 'C3'] = 1
    V.loc['C3-P3', 'P3'] = -1

    V.loc['Fp2-F4', 'Fp2'] = 1
    V.loc['Fp2-F4', 'F4'] = -1
    V.loc['F4-C4', 'F4'] = 1
    V.loc['F4-C4', 'C4'] = -1
    V.loc['C4-P4', 'C4'] = 1
    V.loc['C4-P4', 'P4'] = -1


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


if __name__ == '__main__':
    print("with ipython 0.10 run this with ipython -wthread")
    print("with ipython 0.11 run with ipython --pylab=wx")
    print("run montages.py")
    print("display_10_10_on_sphere()")
    print("mlab.show()")
    print("""might also want to try: nx.draw_spectral(G20)""")

    import mayavi.mlab as mlab
    display_10_10_on_sphere()
    # display_10_5_on_sphere()
    mlab.show()
