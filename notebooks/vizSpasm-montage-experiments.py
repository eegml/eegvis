
# coding: utf-8

# ## Introduction to visualizing data in the eeghdf files
# ### Goals:
# - Demonstrate loading of eeghdf file
# - demonstrate raw data access
# - visualize data as waveform with montages in the notebook

# In[1]:


# import libraries
from __future__ import print_function, division, unicode_literals
get_ipython().run_line_magic('matplotlib', 'inline')
# %matplotlib notebook

import matplotlib
import matplotlib.pyplot as plt
#import seaborn
import pandas as pd
import numpy as np
import h5py
from pprint import pprint

import eegvis.stacklineplot as stacklineplot
import eegvis.montageview as montageview

matplotlib.rcParams['figure.figsize'] = (18.0, 12.0)
#matplotlib.rcParams['figure.figsize'] = (12.0, 8.0)


# In[2]:


ls "../../eeghdf/data"


# In[3]:


hdf = h5py.File('../../eeghdf/data/spasms.eeghdf') # 5mo boy 


# In[4]:


hdf


# In[5]:


rec = hdf['record-0']
years_old = rec.attrs['patient_age_days']/365
pprint("age in years: %s" % years_old)


# ### Access the raw signals and electrode labels

# In[6]:


signals = rec['signals']
labels = rec['signal_labels']
electrode_labels = [str(s,'ascii') for s in labels]
numbered_electrode_labels = ["%d:%s" % (ii, str(labels[ii], 'ascii')) for ii in range(len(labels))]


# #### Simple visualization of EEG (electrodecrement seizure pattern)

# In[7]:


# plot 10s epochs (multiples in DE)
ch0, ch1 = (0,19)
DE = 2 # how many 10s epochs to display
epoch = 53; ptepoch = 10*int(rec.attrs['sample_frequency'])
dp = int(0.5*ptepoch)
# stacklineplot.stackplot(signals[ch0:ch1,epoch*ptepoch+dp:(epoch+DE)*ptepoch+dp],secondsk=DE*10.0, ylabels=electrode_labels[ch0:ch1], yscale=0.3)
print("epoch:", epoch)


# In[8]:


matplotlib.rcParams['figure.figsize'] = (18.0, 12.0)


# In[9]:


# search identified spasms at 1836, 1871, 1901, 1939
stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)


# In[10]:


electrode_labels
r_labels = [ss.replace('EEG ','') for ss in electrode_labels]
r_labels


# In[11]:


montageview.DB_LABELS


# In[12]:


monv = montageview.MontageView(montageview.DB_LABELS, r_labels)


# In[13]:


v = montageview.double_banana_set_matrix(monv.V)
v
dfv = v.to_dataframe(name='doublebanana')


# In[14]:


res = np.dot(monv.V.data,signals[:, 10000:10099]) # example of how to do transformation
signals.dtype


# In[15]:


# access the coordinate labels in the xarray
[xx for xx in monv.V.coords['x'].data]


# In[16]:


[yy for yy in monv.V.coords['y'].data]


# In[17]:


stacklineplot.show_montage_centered(signals, monv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0) 


# In[18]:


stacklineplot.show_montage_centered(signals, monv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0) 
fg = plt.gcf()
fg.savefig('spasm_example.eps')


# In[19]:


# plt.figure?


# In[20]:


annot = rec['edf_annotations']
#print(list(annot.items()))
#annot['texts'][:]


# In[21]:


signals.shape


# In[22]:


antext = [s.decode('utf-8') for s in annot['texts'][:]]
starts100ns = [xx for xx in annot['starts_100ns'][:]]
len(starts100ns), len(antext)


# In[23]:


import pandas as pd


# In[24]:


df = pd.DataFrame(data=antext, columns=['text'])
df['starts100ns'] = starts100ns
df['starts_sec'] = df['starts100ns']/10**7


# In[25]:


df # look at the annotations


# In[26]:


df[df.text.str.contains('sz',case=False)]


# In[27]:


df[df.text.str.contains('seizure',case=False)] # find the seizure


# In[28]:


df[df.text.str.contains('spasm',case=False)] # find the seizure


# In[29]:


list(annot.items())


# 2.6*10**12 /10

# In[30]:


monv.V


# In[31]:


import matplotlib.pyplot as plt


# In[32]:


plt.imshow(monv.V)


# In[33]:


lapmv = montageview.LaplacianMontageView(r_labels)


# In[34]:


plt.imshow(lapmv.V)


# In[35]:


stacklineplot.show_montage_centered(signals, lapmv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0, topdown=True) 
fg = plt.gcf()


# In[36]:


# %pdb on


# In[37]:


tcpmv = montageview.TCPMontageView(r_labels)


# In[38]:


stacklineplot.show_montage_centered(signals, tcpmv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0, topdown=True) 

