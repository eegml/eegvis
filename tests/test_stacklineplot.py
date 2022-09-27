import numpy as np
import matplotlib.pyplot as plt
import eegvis.stacklineplot as stacklineplot

def make_calibration_signal(numSamples, levels=[0, 10, -10, 10, -10]):
    N = len(levels)

    interval = int(numSamples / N)
    data  = np.zeros(numSamples)
    for ii in range(N):
        data[ii * interval : (ii + 1) * interval] = levels[ii]
    return data

def test_add_data_vertical_scalebar():
    

    numSamples, numRows = 800, 5
    data = np.random.randn(numRows, numSamples)  # test data
    data[2, :] = 5 * data[2, :]
    data[-1:] = make_calibration_signal(numSamples)

    fig, ax = plt.subplots()
    ax = stacklineplot.stackplot(data, ax=ax, ysensitivity=7)
    stacklineplot.add_data_vertical_scalebar(ax=ax,units=r'$\mu$V')
    #plt.show()
    fig.savefig('test_add_vertical_data_scalebar.svg')


def test_add_relative_vertical_scalebar():
    numSamples, numRows = 800, 5
    data = np.random.randn(numRows, numSamples)  # test data
    data[2, :] = 5 * data[2, :]
    data[-1:] = make_calibration_signal(numSamples)

    fig, ax = plt.subplots()
    ax = stacklineplot.stackplot(data, ax=ax)
    stacklineplot.add_relative_vertical_scalebar(ax=ax,units=r'$\mu$V')
    #plt.show()
    fig.savefig('test_add_relative_vertical_scalebar.svg')
