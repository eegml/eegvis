I would like to expand the library to include the ability to: generate SVG versions of EEG.

Here is an overview of the EEG pipeline

EEG raw data pipeline steps:
1. take orginal data 
2. downsample data if necessary
3. select montage and transform original data into montage derivation of choice. This is often a linear operation. 
4. generate new labels for channels
5. apply appropriate band-pass filter (often 1-70 Hz but this is selectable)
6. plot the montaged channels, usually with convention that "negative is up" with chosen per channel gain to scale the waveform appropriately 
7. decorate the plot with appropriate scale bars and the time and channel labels

Please propose how to do this for SVG. Let's start with a simple task. The output of the above pipeline would be an SVG file.