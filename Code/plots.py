from collections import Counter
from matplotlib import pyplot as plt
from Code import process_lcsh as pl
import numpy as np


def plot_stacked(ax, x, yDict, colours, xLabel=None, yLabel=None, title=None, barLabels=None, legend=True):
    width = 0.8
    bottom = np.zeros(len(x))
    ax.margins(0.02)
    i = 0
    for lab, counts in yDict.items():
        p = ax.bar(x, counts, width, label=lab, bottom=bottom, color=colours[i])
        bottom += counts
        i += 1
    if title is not None:
        ax.set_title(title)
    if legend:
        ax.legend(handleheight=0.5, handlelength=0.5, fontsize=11,
                  loc="lower center", bbox_to_anchor=(0.02, -0.5), ncol=2, frameon=False)
    ax.spines[['right', 'top']].set_visible(False)
    if xLabel is not None:
        ax.set_xlabel(xLabel, fontsize=11)
    if yLabel is not None:
        ax.set_ylabel(yLabel, fontsize=11)
    ax.tick_params(axis='both', labelsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(x, rotation=90)
    
    if barLabels is not None:
        for i in range(len(x)):
            ax.text(x[i], bottom[i], barLabels[i], ha='center', va='bottom', fontsize=8)
    plt.subplots_adjust(wspace=0.5, 
                        hspace=0.35)
    return ax


def added_each_year(min_date, max_date, terms_m, terms_w, kind='headings'):
    """
    Plots the number of terms added each year in the range of dates given.
    :param min_date: int, the minimum date to consider.
    :param max_date: int, the maximum date to consider.
    :param terms_m: list, the list of terms for men 
    :param terms_w: list, the list of terms for wormen
    :return: None
    """
    # Count the number of terms added each year
    years_m = [term['yearAdded'] for term in terms_m.values() if term['yearAdded'] >= min_date and term['yearAdded'] <= max_date]
    years_w = [term['yearAdded'] for term in terms_w.values() if term['yearAdded'] >= min_date and term['yearAdded'] <= max_date]    
    count_m = Counter(years_m)
    count_w = Counter(years_w)
    x = range(min_date, max_date+1)
    count_m = [count_m[year] for year in x]
    count_w = [count_w[year] for year in x]
    y_counts = {'Men': count_m, 'Women':count_w}

    prop_w = [count_w[i]/(count_w[i]+count_m[i]) for i in range(len(count_w))]
    prop_m = [count_m[i]/(count_w[i]+count_m[i]) for i in range(len(count_m))]
    y_props = {'Men': prop_m, 'Women':prop_w}
    colours = ['goldenrod', 'rebeccapurple']
    _, ax = plt.subplots(2, 1, figsize=(10, 6))
    plot_stacked(ax[0], x, y_props, colours, yLabel=f'Proportion of {kind}', legend=False)
    plot_stacked(ax[1], x, y_counts, colours, xLabel='Year', yLabel=f'Number of {kind}', legend=True)
    #stacked_dict = {'Men': }    
    
    # Create the plot
    
    

