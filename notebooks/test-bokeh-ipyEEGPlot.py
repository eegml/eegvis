
# coding: utf-8

# ## Introduction to browsing data in the eeghdf files in "raw" form

# In[1]:


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
ARCHIVEDIR = r'../../eeghdf/notebooks/archive'


# ### load the hdf eeg file we are interested in

# In[8]:


#hdf = h5py.File('./archive/YA2741BS_1-1+.eeghdf') # 5mo boy 
hdf = h5py.File(os.path.join(ARCHIVEDIR,'YA2741G2_1-1+.eeghdf')) # absence 10yo


# In[9]:


rec = hdf['record-0']
years_old = rec.attrs['patient_age_days']/365


# In[10]:


signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
ref_labels = montageview.standard2shortname(electrode_labels)
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]


# In[11]:


inr = sbokplot.IpyEEGPlot(signals, 15, electrode_labels=electrode_labels, fs=rec.attrs['sample_frequency'])
inr.show()


# ### Try showing fewer channels for better visualization

# In[12]:


smallerplot = sbokplot.IpyEEGPlot(signals, 15, electrode_labels=electrode_labels, fs=rec.attrs['sample_frequency'], showchannels=(0,21))
smallerplot.show()


# In[13]:


smallerplot.ch_start


# In[14]:


smallerplot.ch_stop


# In[15]:


import bokeh


# In[16]:


bokeh.__version__

