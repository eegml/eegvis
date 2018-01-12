# -*- coding: utf-8 -*-
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


# EKG
# PG1
# PG2


#### TCP
# def tcp(B):
#     B('Fp1-F7', 'Fp1') = 1
#     B('Fp1-F7', 'F7') = -1
#     B('F7-T3', 'F7') = 1
#     B('F7-T3', 'T3') = -1
#     B('T3-T5', 'T3') = 1
#     B('T3-T5', 'T5') = -1
#     B('T5-O1', 'T5') = 1
#     B('T5-O1', 'O1') = -1

#     B('Fp2-F8', 'Fp2') = 1
#     B('Fp2-F8', 'F8') = -1
#     B('F8-T4', 'F8') = 1
#     B('F8-T4', 'T4') = -1
#     B('T4-T6', 'T4') = 1
#     B('T4-T6', 'T6') = -1
#     B('T6-O2', 'T6') = 1
#     B('T6-O2', '02') = -1

#     B('A1-T3', 'A1') = 1
#     B('A1-T3', 'T3') = -1
#     B('T3-C3', 'T3') = 1
#     B('T3-C3', 'C3') = -1
#     B('C3-Cz', 'C3') = 1
#     B('C3-Cz', 'Cz') = -1
#     B('Cz-C4', 'Cz') = 1
#     B('Cz-C4', 'C4') = -1
#     B('C4-T4', 'C4') = 1
#     B('C4-T4', 'T4') = -1
#     B('T4-A2', 'T4') = 1
#     B('T4-A2', 'A2') = -1

#     B('Fp1-F3', 'Fp1') = 1
#     B('Fp1-F3', 'F3') = -1
#     B('F3-C3', 'F3') = 1
#     B('F3-C3', 'C3') = -1
#     B('C3-P3', 'C3') = 1
#     B('C3-P3', 'P3') = -1

#     B('Fp2-F4', 'Fp2') = 1
#     B('Fp2-F4', 'F4') = -1
#     B('F4-C4', 'F4') = 1
#     B('F4-C4', 'C4') = -1
#     B('C4-P4', 'C4') = 1
#     B('C4-P4', 'P4') = -1


####################

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
