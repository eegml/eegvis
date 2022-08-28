
# coding: utf-8

# [//]: # ('cell_type':'markdown', "metadata":{'slideshow': {'slide_type': 'slide'}})
# ## Introduction to visualizing data in the eeghdf files

# In[1]:


# %load explore-eeghdf-files-basics.py
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


# In[2]:


hdf = h5py.File('../../eeghdf/data/spasms.eeghdf') # 5mo boy 


# In[3]:


pprint(list(hdf.items()))
pprint(list(hdf['patient'].attrs.items()))


# In[4]:


rec = hdf['record-0']
pprint(list(rec.items()))
pprint(list(rec.attrs.items()))
years_old = rec.attrs['patient_age_days']/365
pprint("age in years: %s" % years_old)


# In[5]:


signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]
print(signals.shape)


# [//]: # ('cell_type':'markdown', "metadata":{'slideshow': {'slide_type': 'slide'}})
# #### Simple visualization of EEG (electrodecrement seizure pattern)

# In[6]:


# search identified spasms at 1836, 1871, 1901, 1939
fig=stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)
show(fig)


# In[7]:


annot = rec['edf_annotations']
#print(list(annot.items()))
#annot['texts'][:]


# In[8]:


signals.shape


# In[9]:


antext = [s.decode('utf-8') for s in annot['texts'][:]]
starts100ns = [xx for xx in annot['starts_100ns'][:]]
len(starts100ns), len(antext)


# In[10]:


df = pd.DataFrame(data=antext, columns=['text'])
df['starts100ns'] = starts100ns
df['starts_sec'] = df['starts100ns']/10**7


# In[11]:


df # look at the annotations


# In[12]:


df[df.text.str.contains('sz',case=False)]


# In[13]:


df[df.text.str.contains('seizure',case=False)] # find the seizure


# In[14]:


df[df.text.str.contains('spasm',case=False)] # find the seizure


# In[15]:


list(annot.items())


# [//]: # ('cell_type':'markdown', "metadata":{'collapsed': True, 'slideshow': {'slide_type': 'skip'}})

# In[16]:


# search identified spasms at 1836, 1871, 1901, 1939
fig=stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)
bh = show(fig, notebook_handle=True)


# In[17]:


inr = stacklineplot.IpyStackplot(signals, 15, ylabels=electrode_labels, fs=rec.attrs['sample_frequency'])


# In[18]:


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


# In[19]:



inr.show()
ipywidgets.HBox([buttonback,buttonf])


# In[20]:


inr.data_source.data


# In[21]:


# this will move the window displayed in inr 
#inr.loc_sec = 1836
#inr.update()


# In[25]:


inr.yscale = 5.0


# In[26]:


#inr.fig.multi_line(xs=inr.xs, ys=inr.ys, line_color='#8073ac')


# In[27]:


push_notebook(handle=inr.bk_handle)


# In[28]:


# f2=bplt.figure()
# f2.multi_line(xs=inr.xs, ys=inr.ys, line_color='firebrick')
# show(f2)


# In[29]:


inr.fig.xaxis.axis_label = 'seconds'


# In[30]:


inr.loc_sec=1800


# In[31]:


push_notebook(handle=inr.bk_handle)

