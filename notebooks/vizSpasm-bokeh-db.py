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

# %% [markdown]
# [//]: # ('cell_type':'markdown', "metadata":{'slideshow': {'slide_type': 'slide'}})
# ## Introduction to visualizing data in the eeghdf files

# %%
# # %load explore-eeghdf-files-basics.py
# Here is an example of how to do basic exploration of what is in the eeghdf file. I show how to discover the fields in the file and to plot them.
# 
# I have copied the stacklineplot from my python-edf/examples code to help with display. Maybe I will put this as a helper or put it out as a utility package to make it easier to install.

from __future__ import print_function, division, unicode_literals
import pandas as pd
import numpy as np
import h5py
from pprint import pprint

import ipywidgets
from IPython.display import display

import eegvis.stacklineplot
import eegvis.stackplot_bokeh as stacklineplot
from bokeh.io import output_notebook, push_notebook
import bokeh.plotting as bplt
from bokeh.plotting import show
output_notebook()

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
hdf = h5py.File('../../eeg-hdfstorage/data/spasms.eeghdf') # 5mo boy 

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
pprint(list(hdf.items()))
pprint(list(hdf['patient'].attrs.items()))

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
rec = hdf['record-0']
pprint(list(rec.items()))
pprint(list(rec.attrs.items()))
years_old = rec.attrs['patient_age_days']/365
pprint("age in years: %s" % years_old)

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]
print(signals.shape)

# %% [markdown]
# [//]: # ('cell_type':'markdown', "metadata":{'slideshow': {'slide_type': 'slide'}})
# #### Simple visualization of EEG (electrodecrement seizure pattern)

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
# search identified spasms at 1836, 1871, 1901, 1939
fig=stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)
show(fig)


# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
annot = rec['edf_annotations']
#print(list(annot.items()))
#annot['texts'][:]

# %% attributes={"classes": [], "id": "", "metadata": ""}
signals.shape

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
antext = [s.decode('utf-8') for s in annot['texts'][:]]
starts100ns = [xx for xx in annot['starts_100ns'][:]]
len(starts100ns), len(antext)

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
df = pd.DataFrame(data=antext, columns=['text'])
df['starts100ns'] = starts100ns
df['starts_sec'] = df['starts100ns']/10**7

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
df # look at the annotations

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
df[df.text.str.contains('sz',case=False)]

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
df[df.text.str.contains('seizure',case=False)] # find the seizure

# %% attributes={"classes": [], "id": "", "metadata": ""}
df[df.text.str.contains('spasm',case=False)] # find the seizure

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
list(annot.items())

# %% [markdown]
# [//]: # ('cell_type':'markdown', "metadata":{'collapsed': True, 'slideshow': {'slide_type': 'skip'}})

# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}
# search identified spasms at 1836, 1871, 1901, 1939
fig=stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)
bh = show(fig, notebook_handle=True)



# %% attributes={"classes": [], "id": "", "metadata": "{'slideshow':"}

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
inr = stacklineplot.IpyStackplot(signals, 15, ylabels=electrode_labels, fs=rec.attrs['sample_frequency'])

# %% attributes={"classes": [], "id": "", "metadata": ""}
inr.plot()
buttonf = ipywidgets.Button(description="go forward 10s")
buttonback = ipywidgets.Button(description="go backward 10s")
goto = ipywidgets.BoundedFloatText(value=0.0, min=0, max=inr.num_samples/inr.fs, step=1, description='goto time(sec)')
def go_forward(b):
    inr.loc_sec += 10
    inr.update()
    
    
def go_backward(b):
    inr.loc_sec -= 10
    inr.update()
    
def go_to_handler(change):
    # print("change:", change)
    if change['name'] == 'value':
        inr.loc_sec = change['new']
        inr.update()
    
    
buttonf.on_click(go_forward)
buttonback.on_click(go_backward)
goto.observe(handler=go_to_handler) # try using traitlet event to do callback on change

# %% attributes={"classes": [], "id": "", "metadata": ""}

inr.show()
ipywidgets.HBox([buttonback,buttonf])


# %% attributes={"classes": [], "id": "", "metadata": ""}
inr.data_source.data

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
# this will move the window displayed in inr 
#inr.loc_sec = 1836
#inr.update()

# %% attributes={"classes": [], "id": "", "metadata": ""}
inr.yscale = 5.0

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
#inr.fig.multi_line(xs=inr.xs, ys=inr.ys, line_color='#8073ac')

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
push_notebook(handle=inr.bk_handle)

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
# f2=bplt.figure()
# f2.multi_line(xs=inr.xs, ys=inr.ys, line_color='firebrick')
# show(f2)

# %% attributes={"classes": [], "id": "", "metadata": "{'collapsed':"}
inr.fig.xaxis.axis_label = 'seconds'

# %% attributes={"classes": [], "id": "", "metadata": ""}
inr.loc_sec=1800

# %%
push_notebook(handle=inr.bk_handle)

# %%
