# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: pyt16:pytorch 1.6+
#     language: python
#     name: pyt16
# ---

# %% [markdown] slideshow={"slide_type": "slide"}
# ## Introduction to visualizing data in the eeghdf files

# %% slideshow={"slide_type": "fragment"}
# # %load explore-eeghdf-files-basics.py
# Here is an example of how to do basic exploration of what is in the eeghdf file. I show how to discover the fields in the file and to plot them.
# 
# I have copied the stacklineplot from my python-edf/examples code to help with display. Maybe I will put this as a helper or put it out as a utility package to make it easier to install.

from __future__ import print_function, division, unicode_literals
import os.path
# %matplotlib inline
# # %matplotlib notebook

import matplotlib
import matplotlib.pyplot as plt
#import seaborn
import pandas as pd
import numpy as np
import h5py
from pprint import pprint

import eegvis.stacklineplot as stacklineplot
import eegvis.montageview as montageview

# matplotlib.rcParams['figure.figsize'] = (18.0, 12.0)
matplotlib.rcParams['figure.figsize'] = (12.0, 8.0)
ARCHIVEDIR = r'../../eeghdf/data'
EEGFILE = os.path.join(ARCHIVEDIR, 'YA2741BS_1-1+.eeghdf')

# %%
# ls ../../eeghdf/data

# %% slideshow={"slide_type": "slide"}
hdf = h5py.File(EEGFILE) 

# %% slideshow={"slide_type": "slide"}
rec = hdf['record-0']
years_old = rec.attrs['patient_age_days']/365
pprint("age in years: %s" % years_old)

# %% jupyter={"outputs_hidden": true} slideshow={"slide_type": "slide"}
signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]

# %% [markdown] slideshow={"slide_type": "slide"}
# #### Simple visualization of EEG (electrodecrement seizure pattern)

# %% slideshow={"slide_type": "fragment"}
# plot 10s epochs (multiples in DE)
ch0, ch1 = (0,19)
DE = 2 # how many 10s epochs to display
epoch = 53; ptepoch = 10*int(rec.attrs['sample_frequency'])
dp = int(0.5*ptepoch)
# stacklineplot.stackplot(signals[ch0:ch1,epoch*ptepoch+dp:(epoch+DE)*ptepoch+dp],seconds=DE*10.0, ylabels=electrode_labels[ch0:ch1], yscale=0.3)
print("epoch:", epoch)



# %%
# search identified spasms at 1836, 1871, 1901, 1939
stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)



# %%
electrode_labels
r_labels = [ss.replace('EEG ','') for ss in electrode_labels]
r_labels

# %%
montageview.DB_LABELS

# %% jupyter={"outputs_hidden": true}
