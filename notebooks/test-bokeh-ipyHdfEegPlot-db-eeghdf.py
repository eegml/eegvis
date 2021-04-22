# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: pytorch 1.5+
#     language: python
#     name: pyt15
# ---

# %% [markdown] slideshow={"slide_type": "slide"}
# ## Introduction to browsing data in the eeghdf files in the jupyter notebook

# %% [markdown] slideshow={"slide_type": "slide"}
# ### First import libraries

# %% slideshow={"slide_type": "fragment"}
# # %load explore-eeghdf-files-basics.py
# Here is an example of how to do basic exploration of what is in the eeghdf file. I show how to discover the fields in the file and to plot them.
# 
# I have copied the stacklineplot from my python-edf/examples code to help with display. Maybe I will put this as a helper or put it out as a utility package to make it easier to install.

from __future__ import print_function, division, unicode_literals
import os.path
import pandas as pd
import numpy as np
import eeghdf
from pprint import pprint

import ipywidgets
from IPython.display import display

# import eegvis.stacklineplot
import eegvis.montageview as montageview
import eegvis.stackplot_bokeh as sbokplot
from bokeh.io import output_notebook, push_notebook
import bokeh.plotting as bplt
from bokeh.plotting import show
output_notebook()

ARCHIVEDIR = r'../../eeghdf/data'
EEGFILE = os.path.join(ARCHIVEDIR, 'spasms.eeghdf')


# %% slideshow={"slide_type": "slide"}
#hdf = h5py.File('./archive/YA2741BS_1-1+.eeghdf') # 5mo boy 
print(EEGFILE)
hf = eeghdf.Eeghdf(EEGFILE)# absence 10yo


# %%
hf.electrode_labels

# %%
hf.shortcut_elabels

# %%

# %% slideshow={"slide_type": "slide"}
tmp = sbokplot.IpyHdfEegPlot(hf,page_width_seconds=15, showchannels=(0,19)) # doing this just to make the labels

# %% [markdown] slideshow={"slide_type": "slide"}
# ## Now demonstrate using a double banana montage

# %% slideshow={"slide_type": "fragment"}
db = montageview.DoubleBananaMontageView(rec_labels=hf.shortcut_elabels)
inr = sbokplot.IpyHdfEegPlot(hf.hdf,page_width_seconds=15, montage=db)

# inr.all_montages.append(db)
#inr.current_montage = db

# %% slideshow={"slide_type": "slide"}
inr.show()

# %% slideshow={"slide_type": "skip"}
# you can manipulate the EEG plot directly
inr.loc_sec = 600
inr.update()

# %% slideshow={"slide_type": "skip"}
inr.current_montage.name

# %% slideshow={"slide_type": "skip"}
hf.hdf.filename

# %%
import bokeh
bokeh.__version__

# %%
