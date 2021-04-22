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
# ## Introduction to visualizing data in the eeghdf files
# ### Goals:
# - Demonstrate loading of eeghdf file
# - demonstrate raw data access
# - visualize data as waveform with montages in the notebook

# %% slideshow={"slide_type": "slide"}
# import libraries
from __future__ import print_function, division, unicode_literals
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

matplotlib.rcParams['figure.figsize'] = (18.0, 12.0)
#matplotlib.rcParams['figure.figsize'] = (12.0, 8.0)

# %% slideshow={"slide_type": "skip"}
# ls "../../eeg-hdfstorage/data"

# %% slideshow={"slide_type": "slide"}
hdf = h5py.File('../../eeg-hdfstorage/data/spasms.eeghdf') # 5mo boy 

# %% slideshow={"slide_type": "skip"}
hdf

# %% slideshow={"slide_type": "slide"}
rec = hdf['record-0']
years_old = rec.attrs['patient_age_days']/365
pprint("age in years: %s" % years_old)

# %% [markdown] slideshow={"slide_type": "slide"}
# ### Access the raw signals and electrode labels

# %% slideshow={"slide_type": "fragment"}
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
# stacklineplot.stackplot(signals[ch0:ch1,epoch*ptepoch+dp:(epoch+DE)*ptepoch+dp],secondsk=DE*10.0, ylabels=electrode_labels[ch0:ch1], yscale=0.3)
print("epoch:", epoch)



# %%
matplotlib.rcParams['figure.figsize'] = (18.0, 12.0)

# %% slideshow={"slide_type": "slide"}
# search identified spasms at 1836, 1871, 1901, 1939
stacklineplot.show_epoch_centered(signals, 1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0)



# %% slideshow={"slide_type": "slide"}
electrode_labels
r_labels = [ss.replace('EEG ','') for ss in electrode_labels]
r_labels

# %% slideshow={"slide_type": "slide"}
montageview.DB_LABELS

# %% slideshow={"slide_type": "slide"}
monv = montageview.MontageView(montageview.DB_LABELS, r_labels)

# %% slideshow={"slide_type": "fragment"}
v = montageview.double_banana_set_matrix(monv.V)
v
dfv = v.to_dataframe(name='doublebanana')

# %%
res = np.dot(monv.V.data,signals[:, 10000:10099]) # example of how to do transformation
signals.dtype

# %%
# access the coordinate labels in the xarray
[xx for xx in monv.V.coords['x'].data]

# %%
[yy for yy in monv.V.coords['y'].data]


# %% slideshow={"slide_type": "slide"}
stacklineplot.show_montage_centered(signals, monv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0) 

# %% slideshow={"slide_type": "skip"}
stacklineplot.show_montage_centered(signals, monv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0) 
fg = plt.gcf()
fg.savefig('spasm_example.eps')

# %% slideshow={"slide_type": "skip"}
# # plt.figure?

# %% slideshow={"slide_type": "skip"}
annot = rec['edf_annotations']
#print(list(annot.items()))
#annot['texts'][:]

# %% slideshow={"slide_type": "skip"}

# %% slideshow={"slide_type": "skip"}

# %% slideshow={"slide_type": "skip"}
signals.shape

# %% slideshow={"slide_type": "skip"}
antext = [s.decode('utf-8') for s in annot['texts'][:]]
starts100ns = [xx for xx in annot['starts_100ns'][:]]
len(starts100ns), len(antext)

# %% slideshow={"slide_type": "slide"}
import pandas as pd

# %% slideshow={"slide_type": "fragment"}
df = pd.DataFrame(data=antext, columns=['text'])
df['starts100ns'] = starts100ns
df['starts_sec'] = df['starts100ns']/10**7

# %% slideshow={"slide_type": "slide"}
df # look at the annotations

# %% slideshow={"slide_type": "skip"}
df[df.text.str.contains('sz',case=False)]

# %% slideshow={"slide_type": "skip"}
df[df.text.str.contains('seizure',case=False)] # find the seizure

# %% slideshow={"slide_type": "slide"}
df[df.text.str.contains('spasm',case=False)] # find the seizure

# %% slideshow={"slide_type": "skip"}
list(annot.items())

# %% slideshow={"slide_type": "skip"}

# %% [markdown] slideshow={"slide_type": "skip"}
# 2.6*10**12 /10

# %% slideshow={"slide_type": "slide"}
monv.V

# %% slideshow={"slide_type": "slide"}
import matplotlib.pyplot as plt

# %% slideshow={"slide_type": "fragment"}
plt.imshow(monv.V)

# %% slideshow={"slide_type": "skip"}
lapmv = montageview.LaplacianMontageView(r_labels)

# %% slideshow={"slide_type": "skip"}
plt.imshow(lapmv.V)

# %% slideshow={"slide_type": "skip"}
stacklineplot.show_montage_centered(signals, lapmv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0, topdown=True) 
fg = plt.gcf()

# %%
# # %pdb on

# %%
tcpmv = montageview.TCPMontageView(r_labels)

# %%
stacklineplot.show_montage_centered(signals, tcpmv,1836,
                        epoch_width_sec=15,
                        chstart=0, chstop=19, fs=rec.attrs['sample_frequency'],
                        ylabels=electrode_labels, yscale=3.0, topdown=True) 

# %%

# %%

# %%

# %%

# %%

# %%
