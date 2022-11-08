# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python [conda env:py36mayavi]
#     language: python
#     name: conda-env-py36mayavi-py
# ---

# %% [markdown] slideshow={"slide_type": "slide"}
# ## Introduction to browsing data in the eeghdf files in "raw" form

# %% slideshow={"slide_type": "fragment"}

# load the eegvis libaries and some others we might use

from __future__ import print_function, division, unicode_literals
import os.path
import pandas as pd
import numpy as np
import h5py

import ipywidgets
from IPython.display import display

import eegvis.stacklineplot
import eegvis.montageview as montageview
import eegvis.stackplot_bokeh as sbokplot
from bokeh.io import output_notebook, push_notebook
#import bokeh.plotting as bplt
#from bokeh.plotting import show
output_notebook()

ARCHIVEDIR = r'../../eeg-hdfstorage/notebooks/archive'

# %% [markdown] slideshow={"slide_type": "slide"}
# ### load the hdf eeg file we are interested in

# %% slideshow={"slide_type": "fragment"}
#hdf = h5py.File('./archive/YA2741BS_1-1+.eeghdf') # 5mo boy 
hdf = h5py.File(os.path.join(ARCHIVEDIR,'YA2741G2_1-1+.eeghdf')) # absence 10yo

# %% slideshow={"slide_type": "slide"}
rec = hdf['record-0']
years_old = rec.attrs['patient_age_days']/365

# %% slideshow={"slide_type": "slide"}

signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
ref_labels = montageview.standard2shortname(electrode_labels)
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]


# %% slideshow={"slide_type": "slide"}
inr = sbokplot.IpyEEGPlot(signals, 15, electrode_labels=electrode_labels, fs=rec.attrs['sample_frequency'])
inr.show()

# %% [markdown] slideshow={"slide_type": "slide"}
# ### Try showing fewer channels for better visualization

# %% slideshow={"slide_type": "fragment"}
smallerplot = sbokplot.IpyEEGPlot(signals, 15, electrode_labels=electrode_labels, fs=rec.attrs['sample_frequency'], showchannels=(0,21))
smallerplot.show()

# %% slideshow={"slide_type": "skip"}
smallerplot.ch_start

# %% slideshow={"slide_type": "skip"}
smallerplot.ch_stop

# %% slideshow={"slide_type": "skip"}
import bokeh

# %%
bokeh.__version__

# %%

