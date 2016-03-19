import matplotlib.pyplot as plt
import matplotlib.lines as mlines

def display_precision_recall_plot(series):

    fig, ax = plt.subplots()
    plt.suptitle('Precision and recall')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.grid(True)
    for serie in series:
        ax.plot([p['recall'] for p in serie['data']], [p['precision'] for p in serie['data']], label=serie['name'])
    ax.legend(loc='lower left', shadow=True)
    plt.show()


def display_loss_curve_plot(data):
    pass
