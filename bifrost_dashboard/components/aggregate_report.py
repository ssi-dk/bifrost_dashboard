import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from plotly import tools
import pandas as pd
import numpy as np
import bifrost_dashboard.components.import_data as import_data
import bifrost_dashboard.components.global_vars as global_vars


def aggregate_report():
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.H6(
                        "QC parameters",
                        className="m-0 font-weight-bold text-primary"
                    ),
                ], className="card-header py-3"),
                html.Div([
                    html.Div(
                        [
                            html.Label("Plot species",
                                       htmlFor="plot-species"),
                            dcc.RadioItems(
                                options=[
                                    {"label": " Provided",
                                        "value": "provided"},
                                    {"label": " Detected",
                                        "value": "detected"},
                                ],
                                value="provided",
                                labelStyle={
                                    'margin': '0 0.5rem 0.5rem 0'},
                                id="plot-species-source"
                            ),
                            html.Div(dcc.Dropdown(
                                id="plot-species"
                            ), id="plot-species-div")
                        ],
                        className=""
                    ),

                    dcc.Graph(id="summary-plot"),
                ], className="card-body")
            ], className="card shadow")
        ], className="col-12 col-xl-8"),
        html.Div([
            html.Div([
                html.Div([
                    html.H6(
                        "MLST",
                        className="m-0 font-weight-bold text-primary"
                    ),
                ], className="card-header py-3"),
                html.Div([
                    dcc.Graph(id="mlst-plot")
                ], className="card-body")
            ], className="card shadow")
        ], className="col-12 col-xl-4")
    ], className="row")


# Callbacks

def aggregate_species_dropdown(sample_store, plot_species, selected_species):
    sample_ids = [s["_id"] for s in sample_store]

    plot_df = import_data.filter_all(
        sample_ids=sample_ids,
        projection={"properties": 1})

    species_col = "properties.species_detection.summary.detected_species"

    if plot_species == "provided":
        species_col = "properties.sample_info.summary.provided_species"
    elif plot_species == "detected":
        species_col = "properties.species_detection.summary.detected_species"

    if species_col not in plot_df:
        plot_df[species_col] = np.nan
    plot_df.loc[pd.isnull(plot_df[species_col]), species_col] = "Not classified"
    species_list = plot_df[species_col].unique()
    species_list = ["All species", ] + list(species_list)
    if selected_species == "Not classified" or selected_species is None or selected_species not in species_list:
        if species_list[0] == "Not classified" and len(species_list) > 1:
            selected_species = species_list[1]
        else:
            selected_species = species_list[0]
    species_list_options = [
        {
            "label": species,
            "value": species
        } for species in species_list]
    return [selected_species, species_list_options]


def update_aggregate_fig(selected_species, sample_store, plot_species_source):
    if len(sample_store) == 0:
        return {"data": []}, {"data": []}
    plot_values = global_vars.plot_values
    traces = []
    trace_ranges = []

    species_col = "properties.species_detection.summary.detected_species"
    if plot_species_source == "provided":
        species_col = "properties.sample_info.summary.provided_species"
    elif plot_species_source == "detected":
        species_col = "properties.species_detection.summary.detected_species"

    sample_ids = [s["_id"] for s in sample_store]
    plot_df = import_data.filter_all(
        sample_ids=sample_ids)

    if "properties.sample_info.summary.provided_species" not in plot_df:
        plot_df["properties.sample_info.summary.provided_species"] = np.nan

    plot_df.loc[pd.isnull(plot_df[species_col]),
                species_col] = "Not classified"

    # Some columns need to have some text extracted
    for col in global_vars.value_from_test:
        if col in plot_df.columns:
            new = plot_df[col].str.split(":", expand=True)
            loc = plot_df.columns.get_loc(col)
            plot_df.insert(loc + 1, col + ".value", new[2])
    sunburst_fig = generate_sunburst(plot_df)

    # Convert to string so the id can be shown in the plot.
    plot_df["_id"] = plot_df["_id"].astype(str)

    if species_col in plot_df.columns and (selected_species in plot_df[species_col].unique() or
                                           selected_species == "All species"):
        for plot_value in plot_values:
            plot_id = plot_value["id"]
            if selected_species == "All species":
                species_df = plot_df
            else:
                species_df = plot_df[plot_df[species_col] == selected_species]
            species_df[plot_id] = pd.to_numeric(
                species_df[plot_id], errors="coerce")
            if (plot_id in species_df.columns):
                data_range = plot_value["limits"][1] - plot_value["limits"][0]
                low_limit = min(
                    float(species_df[plot_id].min()), plot_value["limits"][0])
                if low_limit == float(species_df[plot_id].min()):
                    low_limit -= data_range * 0.1
                high_limit = max(
                    float(species_df[plot_id].max()), plot_value["limits"][1])
                if high_limit == float(species_df[plot_id].max()):
                    high_limit += data_range*0.1
                trace_ranges.append([low_limit, high_limit])
                traces.append(
                    go.Box(
                        x=species_df.loc[:, plot_id],
                        text=species_df["name"],
                        marker=dict(
                            size=4
                        ),

                        boxpoints="all",
                        jitter=0.3,
                        pointpos=-1.6,
                        selectedpoints=list(
                            range(len(species_df.index))),
                        name=plot_value["name"],
                        showlegend=False,
                        customdata=species_df["_id"]
                    )
                )
    fig = tools.make_subplots(rows=7, cols=1, print_grid=False)
    fig["layout"].update(
        hovermode="closest",
        title=selected_species,
        height=750,
        margin=go.layout.Margin(
            l=175,  # noqa
            r=50,
            b=25,
            t=50
        ),
    )
    try:
        fig.append_trace(traces[0], 1, 1)
        fig.append_trace(traces[1], 1, 1)
        fig.append_trace(traces[2], 2, 1)
        fig.append_trace(traces[3], 3, 1)
        fig.append_trace(traces[4], 4, 1)
        fig.append_trace(traces[5], 5, 1)
        fig.append_trace(traces[6], 6, 1)
        fig.append_trace(traces[7], 7, 1)

        fig["layout"]["xaxis"].update(range=trace_ranges[0])
        fig["layout"]["xaxis2"].update(range=trace_ranges[2])
        fig["layout"]["xaxis3"].update(range=trace_ranges[3])
        fig["layout"]["xaxis4"].update(range=trace_ranges[4])
        fig["layout"]["xaxis5"].update(range=trace_ranges[5])
        fig["layout"]["xaxis6"].update(range=trace_ranges[6])
        fig["layout"]["xaxis7"].update(range=trace_ranges[7])
    except IndexError:
        pass  # It won't draw al ranges/traces because they don't exist.

    fig["layout"]["yaxis"].update(domain=(0.78, 1))
    fig["layout"]["yaxis2"].update(domain=(0.655, 0.75))
    fig["layout"]["yaxis3"].update(domain=(0.53, 0.625))
    fig["layout"]["yaxis4"].update(domain=(0.415, 0.5))
    fig["layout"]["yaxis5"].update(domain=(0.28, 0.375))
    fig["layout"]["yaxis6"].update(domain=(0.155, 0.25))
    fig["layout"]["yaxis7"].update(domain=(0.03, 0.125))

    species_size = import_data.get_species_QC_values(selected_species)

    annotations = [
        {
            "x": species_size["min_length"],
            "y": 0,
            "xref": "x",
            "yref": "y",
            "text": "min",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {
            "x": species_size["min_length"],
            "y": 1,
            "xref": "x",
            "yref": "y",
            "text": "min",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {
            "x": species_size["max_length"],
            "y": 0,
            "xref": "x",
            "yref": "y",
            "text": "max",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {
            "x": species_size["max_length"],
            "y": 1,
            "xref": "x",
            "yref": "y",
            "text": "max",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {
            "x": 250000,
            "y": 0,
            "xref": "x2",
            "yref": "y2",
            "text": "max",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Cov
            "x": 10,
            "y": 0,
            "xref": "x3",
            "yref": "y3",
            "text": "fail",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Cov
            "x": 25,
            "y": 0,
            "xref": "x3",
            "yref": "y3",
            "text": "low",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Cov
            "x": 50,
            "y": 0,
            "xref": "x3",
            "yref": "y3",
            "text": "warn",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Num reads
            "x": 10000,
            "y": 0,
            "xref": "x5",
            "yref": "y5",
            "text": "min",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Main+uncl
            "x": 0.95,
            "y": 0,
            "xref": "x6",
            "yref": "y6",
            "text": "min",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
        {  # Uncl
            "x": 0.2,
            "y": 0,
            "xref": "x7",
            "yref": "y7",
            "text": "max",
            "arrowhead": 0,
            "ax": 0,
            "ay": 40
        },
    ]

    fig["layout"].update(annotations=annotations)

    return fig, sunburst_fig

def generate_sunburst(plot_df):
    species_col = "properties.species_detection.summary.species"
    mlst_col = "properties.mlst.summary.strain"
    if not (species_col in plot_df.columns and mlst_col in plot_df.columns):
        return go.Figure()
    
    unique_species = plot_df[species_col].unique()
    labels = ["samples"]
    parents = [""]
    ids = ["samples"]
    values = [len(plot_df["_id"])]
    for row in plot_df.loc[plot_df[mlst_col].isnull(), mlst_col].index:
        plot_df.at[row, mlst_col] = [None]
    def joinmlst(l):
        return ', '.join(map(str, l))

    plot_df["properties.mlst.summary.strainstr"] = plot_df[mlst_col].apply(joinmlst)
    for species in unique_species:
        species_df = plot_df[plot_df[species_col] == species]
        ids.append(short_species(species))
        labels.append(short_species(species))
        parents.append("samples")
        values.append(len(species_df))
        if "properties.mlst.summary.strainstr" in species_df.columns:
            unique_mlst = species_df["properties.mlst.summary.strainstr"].unique(
            )
            for mlst in unique_mlst:
                ids.append("{} - {}".format(species, mlst))
                labels.append(mlst)
                parents.append(short_species(species))
                values.append(str(
                    len(species_df[species_df["properties.mlst.summary.strainstr"] == mlst])))
    trace = go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        outsidetextfont={"size": 20, "color": "#377eb8"},
        marker={"line": {"width": 2}},
    )

    layout = go.Layout(
        margin=go.layout.Margin(t=0, l=0, r=0, b=0)
    )
    return go.Figure([trace], layout)


def short_species(species):
    if species is None or pd.isna(species):
        return None
    words = species.split(" ")
    if len(words) == 1:
        return species
    return "{}. {}".format(words[0][0], " ".join(words[1:]))
