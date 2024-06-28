from datetime import timedelta

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
import wfdb


# Some annotations are missing from the array, so unfortunately,
#  is_qrs cannot be used as a mask.
ann_qrs_indices = np.arange(
    len(wfdb.io.annotation.is_qrs)
)[wfdb.io.annotation.is_qrs]
qrs_symbols = tuple(wfdb.io.annotation.ann_label_table['symbol'][ann_qrs_indices])


def add_grid(fig: go.Figure):
    """Add a red ECG grid to the figure.
    The grid expects x / dataframe.index to be set in seconds, and y to be set in mV.
    """
    def to_dt(s):
        return s * 1000

    fig.update_layout(
        xaxis=dict(
            tick0=to_dt(0), dtick=to_dt(0.04 * 5),
            minor=dict(tick0=to_dt(0), dtick=to_dt(0.04), gridwidth=2),
            gridcolor="rgb(250, 200, 200)", zerolinecolor="rgb(250, 150, 150)", gridwidth=2,
            tickformat='%M:%S:%L',
        ),
        yaxis=dict(
            tick0=0, dtick=0.1 * 5,
            gridcolor="rgb(250, 200, 200)", zerolinecolor="rgb(250, 150, 150)", gridwidth=2,
            minor=dict(tick0=0, dtick=0.1, gridwidth=2),
            showticklabels=False,
        ),
        plot_bgcolor='rgba(0,0,0,0)'
    )


def add_ann_vlines(fig: go.Figure, annotations: wfdb.Annotation, fs, sampfrom, sampto):
    cmap = plotly.colors.qualitative.Plotly

    is_included = (annotations.sample > sampfrom) & (annotations.sample < sampto)
    print(np.sum(is_included))

    for i in np.arange(annotations.ann_len)[is_included]:
        cmap_idx = None
        if annotations.symbol[i] in qrs_symbols:
            cmap_idx = 1
        elif annotations.symbol[i] in ["(", ")"]:
            cmap_idx = 0
        elif annotations.symbol[i] == "p":
            cmap_idx = 2
        elif annotations.symbol[i] == "t":
            cmap_idx = 3

        fig.add_vline(
            # FIXME see https://github.com/plotly/plotly.py/issues/3065
            x=(timedelta(seconds=annotations.sample[i] / fs) + pd.Timestamp("1970/01/01")).timestamp() * 1000 - 1000 * 60 * 60,
            line_color=cmap[cmap_idx] if cmap_idx is not None else None,
            # line_dash="dash",
            opacity=0.5,
            annotation=go.layout.Annotation(
                text=annotations.symbol[i],
                hovertext=f"Subtype: {annotations.subtype[i]} \n Note: {annotations.aux_note[i]}"
            )
        )
