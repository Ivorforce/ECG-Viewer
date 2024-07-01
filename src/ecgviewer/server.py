import base64
import io
from datetime import timedelta
from multiprocessing import Condition
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import setproctitle
import wfdb
from dash import Dash, html, dcc, callback, Output, Input, State
from flask_caching import Cache

from ecgviewer import visualization
from ecgviewer.domino import terminate_when_parent_process_dies
from ecgviewer.visualization import add_ann_vlines


def start_dash(host: str, port: int, server_is_started: Condition):
    # Set the process title.
    setproctitle.setproctitle('ecg-viewer-dash')
    # When the parent dies, follow along.
    terminate_when_parent_process_dies()

    # The following is the minimal sample code from dash itself:
    # https://dash.plotly.com/minimal-app

    app = Dash(__name__)
    cache = Cache(app.server, config={
        'CACHE_TYPE': 'SimpleCache',
    })

    app.layout = [
        html.Div([
            dcc.Store(id='memory'),
            dcc.Upload(
                id='upload-data',
                multiple=True,
            ),
            dcc.Upload(
                id='upload-annotations',
                multiple=False,
            ),
        ], style={'display': 'none'}),
        html.Div([
            html.Div([
                dcc.Dropdown(
                    id="leads-mode",
                    style={'width': 200},
                    options=["Separate Leads", "Stacked Leads"],
                    value="Separate Leads",
                    searchable=False,
                    clearable=False,
                ),
                html.Div([
                    dcc.Dropdown(id="leads", multi=True),
                ], style={'flex': '1 1 auto', 'padding-left': 20}),
            ], style={'padding': '20px', 'display': 'flex', 'flex-wrap': 'nowrap'}),
            html.Div([
                dcc.Graph(
                    id='graph-content',
                    config={
                        'modeBarButtonsToRemove': ['autoScale'],
                        'displaylogo': False,
                        # 'displayModeBar': False,
                    },
                ),
            ], style={'flex': '1 1 auto', "overflow-y": "scroll"}),
            dcc.Slider(
                0, 5, 0.04 * 5,
                id='position',
                tooltip={"placement": "bottom", "always_visible": True, "transform": "secs_to_timestamp"},
                value=0,
                updatemode='mouseup',
            ),
        ], style={
            "height": "100vh",
            "width": "100vw",
            "display": "flex",
            "overflow": "hidden",
            "flex-direction": "column",
        }),
    ]

    def decode_data(contents):
        content_type, content_string = contents.split(',')
        return base64.b64decode(content_string)

    @cache.memoize(timeout=60 * 10)
    def read_record(list_of_contents, list_of_names: List[str]) -> Optional[wfdb.Record]:
        if not list_of_contents or not list_of_names:
            return None

        record_name = next((n[:-4] for n in list_of_names if n.endswith(".hea")), None)
        hea_data = next((c for c, n in zip(list_of_contents, list_of_names) if n.endswith(".hea")), None)
        sig_data = next((c for c, n in zip(list_of_contents, list_of_names) if n.endswith(".dat")), None)

        if record_name is None or hea_data is None or sig_data is None:
            return None

        return wfdb.rdrecord(
            record_name,
            hea_stream=io.BytesIO(decode_data(hea_data)),
            sig_stream=io.BytesIO(decode_data(sig_data)),
        )

    @cache.memoize(timeout=60 * 10)
    def read_annotations(ann_data) -> Optional[wfdb.Annotation]:
        if ann_data is None:
            return None

        return wfdb.rdann("dummy", extension="dm", ann_stream=io.BytesIO(decode_data(ann_data)))

    @callback(
        Output('position', 'marks'),
        Output('position', 'max'),
        Output('leads', 'options'),
        Output('leads', 'value'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
    )
    def update_gui(list_of_contents, list_of_names: List[str]):
        record = read_record(list_of_contents, list_of_names)
        if record is None:
            return (
                {i: f"{i}" for i in range(11)},
                10,
                [],
                []
            )

        marks = np.linspace(0, record.sig_len // record.fs, num=10)

        return (
            {i: f"{int(i // 60)}:{int(i % 60)}" for i in marks},
            record.sig_len // record.fs,
            list(record.sig_name),
            list(record.sig_name),
        )

    @callback(
        Output('graph-content', 'figure'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        Input('upload-annotations', 'contents'),
        Input('position', 'value'),
        Input('leads', 'value'),
        Input('leads-mode', 'value'),
    )
    def update_graph(list_of_contents, list_of_names: List[str], annotations_file, position: int, leads: List[str], leads_mode: str):
        record = read_record(list_of_contents, list_of_names)
        annotation = read_annotations(annotations_file)

        if record is None or leads is None:
            return {}

        sampfrom = max(0, int(position * record.fs - record.fs * 1.5))
        sampto = min(record.sig_len, int(position * record.fs + record.fs * 1.5))

        data = record.p_signal[sampfrom:sampto, [record.sig_name.index(l) for l in leads]]
        # index = np.linspace(sampfrom / record.fs, sampto / record.fs, num=data.shape[0], endpoint=False)
        index = pd.timedelta_range(
            timedelta(seconds=sampfrom / record.fs),
            timedelta(seconds=sampto / record.fs),
            periods=data.shape[0],
            closed='right',
        ) + pd.Timestamp("1970/01/01")

        is_separate_leads = leads_mode == "Separate Leads"
        if is_separate_leads:
            data = np.copy(data)
            # Separate by 3 big boxes
            for i in range(1, data.shape[1]):
                data[:, i] -= i * 1.5

        min_shown_data = (-data.shape[1] * 1.5) if is_separate_leads else -1.5
        max_shown_data = 1.5

        fig = go.Figure(
            data=[
                go.Scatter(y=data[:, i], x=index, mode='lines', name=record.sig_name[i])
                for i in range(data.shape[1])
            ],
            layout=go.Layout(
                yaxis=go.layout.YAxis(
                    autorange=False,
                    range=[min_shown_data, max_shown_data],
                    # TODO This just scrolls back and for some reason zooms the graph?
                    # minallowed=min_shown_data - 2,
                    # maxallowed=max_shown_data + 2,
                    constraintoward='center',
                    # fixedrange=True,
                    # TODO This doesn't work when using datetime x indices
                    # scaleanchor="x",
                    # scaleratio=0.4,
                    automargin=False,
                ),
                xaxis=go.layout.XAxis(
                    # fixedrange=True,
                    # Don't just use index here, because otherwise the edges are weirdly scaled
                    range=[
                        timedelta(seconds=(position * record.fs - record.fs * 1.5) / record.fs) + pd.Timestamp("1970/01/01"),
                        timedelta(seconds=(position * record.fs + record.fs * 1.5) / record.fs) + pd.Timestamp("1970/01/01"),
                    ],
                    # rangeslider=go.layout.xaxis.Rangeslider(
                    #     visible=True,
                    #     yaxis=go.layout.xaxis.rangeslider.YAxis(rangemode='fixed', range=[-1.5, 1.5]),
                    # ),
                    automargin=False,
                    # FIXME This somehow breaks the graph
                    # minallowed=index[0],
                    # maxallowed=index[-1],
                ),
                margin=go.layout.Margin(l=20, r=20, t=20, b=50),
                height=(200 + data.shape[1] * 200) if is_separate_leads else (200 + 200),
                hovermode="x unified"
            ),
        )
        visualization.add_grid(fig)

        if annotation is not None:
            add_ann_vlines(fig, annotations=annotation, fs=record.fs, sampfrom=sampfrom, sampto=sampto)

        return fig

#     app.clientside_callback(
#         '''
# function(input_value_1) {
#     Plotly.relayout(document.getElementById("graph-content"), { selections: [{ type: 'path' }] });
# }
# ''',
#         Input('graph-content', 'figure'),
#     )

    with server_is_started:
        server_is_started.notify()

    # debug cannot be True right now with nuitka: https://github.com/Nuitka/Nuitka/issues/2953
    app.run(debug=False, host=host, port=port)
