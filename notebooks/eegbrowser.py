# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.2'
#       jupytext_version: 1.2.1
#   kernelspec:
#     display_name: Python [conda env:mne]
#     language: python
#     name: conda-env-mne-py
# ---

# %%
# import dependencies
import ipywidgets
import bokeh
from bokeh.io import output_notebook, push_notebook

output_notebook()
# %%

import eegvis.nb_eegview as nb_eegview
import eeghdf

# %%
# use full browser width
nb_eegview.setNotebookWidth100()
# %%
# load your eeg file
hf = eeghdf.Eeghdf("../../eeg-hdfstorage/data/absence_epilepsy.eeghdf")

# %%
browser = nb_eegview.EeghdfBrowser(hf)

# %%
browser.show()

# %%
