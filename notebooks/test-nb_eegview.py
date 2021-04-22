# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: pyt15-pytorch 1.5+
#     language: python
#     name: pyt15
# ---

# %%
# #%pdb on

# %%
from __future__ import print_function, division, unicode_literals

import sys
import os.path
import pandas as pd
import numpy as np
import eeghdf
from pprint import pprint

import ipywidgets
from IPython.display import display

# import eegvis.stacklineplot
import eegvis.montageview as montageview
import eegvis.nb_eegview as nb_eegview
import eegvis.stackplot_bokeh as sbokplot
from bokeh.io import output_notebook, push_notebook
import bokeh.plotting as bplt
from bokeh.plotting import show
output_notebook()

# current testing based upon a anaconda=5.2 conda environment
# note if you get an h5py depecation warning then may update h5py to version 2.8 to prevent
# for example: conda update -c anaconda h5py OR conda install -c anaconda h5py=2.8

# %%
from IPython.core.display import display, HTML
display(HTML("<style>.container { width:100% !important; }</style>"))

# %%
ARCHIVEDIR = r'../../eeghdf/data/'
#EEGFILE = ARCHIVEDIR + 'spasms.eeghdf'
EEGFILE = ARCHIVEDIR + 'absence_epilepsy.eeghdf'

# %%
hf = eeghdf.Eeghdf(EEGFILE)

# %% slideshow={"slide_type": "slide"}
eegbrow = nb_eegview.EeghdfBrowser(hf, montage='double banana', start_seconds=1385, plot_width=1800, plot_height=800)

# %%
eegbrow.show()

# %%
f = eegbrow._highpass_cache['5 Hz'] # grab one of the filters

# %%
eegbrow.yscale = 3.0 # interact with live plot
eegbrow.update()

# %%

# %%

# %%

# %%
# experiment with more anotations, need to add a scale bar
import bokeh
from bokeh.models.annotations import BoxAnnotation, Arrow
t = eegbrow.loc_sec - eegbrow.page_width_seconds/2.0
#scalbox = BoxAnnotation(left=t, right=t+0.5, top=500.0, bottom=0, fill_color='gray', fill_alpha=0.5)
#eegbrow.fig.add_layout(scalbox)
arwV = Arrow(x_start=t, x_end=t, y_start=0, y_end=500.0, end=None) # don't draw an arrow head
arwH = Arrow(x_start=t, x_end=t+0.5, y_start=0, y_end=0, end=None)
eegbrow.fig.add_layout(arwV)
eegbrow.fig.add_layout(arwH)
eegbrow.push_notebook()

# %%
arwV.x_start = 1384.0; arwV.x_end = 1384.0
eegbrow.push_notebook()

# %%
r = eegbrow.fig.renderers
arrowrend = [ii for ii in r if ii.__class__ == bokeh.models.annotations.Arrow]
a0 = arrowrend[0]
a0.x_end

# %%
montageview.MONTAGE_BUILTINS

# %%
eegbrow.montage_options

# %%

# %%
