import pandas as pd
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash import Dash, dash_table
import dash
import dash_bootstrap_components as dbc

from JupyterReviewer.ReviewDataApp import AppComponent
from JupyterReviewer.AppComponents.utils import cluster_color


def gen_mutation_table_app_component():
    return AppComponent(
        'Mutations',
        layout=gen_mutation_table_layout(),

        callback_input=[
            Input('column-selection-dropdown', 'value'),
            Input('hugo-dropdown', 'value'),
            Input('table-size-dropdown', 'value'),
            Input('variant-classification-dropdown', 'value'),
            Input('cluster-assignment-dropdown', 'value')
        ],
        callback_output=[
            Output('column-selection-dropdown', 'options'),
            Output('column-selection-dropdown', 'value'),
            Output('mutation-table-component', 'children'),
            Output('hugo-dropdown', 'options'),
            Output('variant-classification-dropdown', 'options'),
            Output('cluster-assignment-dropdown', 'options')
        ],
        new_data_callback=gen_maf_table,
        internal_callback=internal_gen_maf_table
    )

def gen_mutation_table_layout():
    return html.Div([
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.P('Table Size (Rows)'),
                ], width=2),
                dbc.Col([
                    html.P('Select Columns')
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id='table-size-dropdown',
                        options=[10,20,30],
                        value=10
                    )
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(
                        id='column-selection-dropdown',
                        options=[],
                        value=[],
                        multi=True,
                    )
                ], width=10)
            ])
        ]),

        html.Div(
            dbc.Row([
                dbc.Col([
                    dcc.Dropdown(
                        id='hugo-dropdown',
                        options=[],
                        multi=True,
                        placeholder='Filter by Hugo Symbol',
                    )
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(
                        id='variant-classification-dropdown',
                        options=[],
                        multi=True,
                        placeholder='Filter by Variant Classification'
                    )
                ], width=2),
                dbc.Col([
                    dcc.Dropdown(
                        id='cluster-assignment-dropdown',
                        options=[],
                        multi=True,
                        placeholder='Filter by Cluster Assignment'
                    )
                ], width=2)
            ])
        ),

        html.Div(dash_table.DataTable(
            id='mutation-table',
            columns=[{'name': i, 'id': i, 'selectable': True} for i in pd.DataFrame().columns],
            data=pd.DataFrame().to_dict('records')
        ), id='mutation-table-component'),
    ])

def format_style_data(column_id, filter_query, color='Black', backgroundColor='White'):
    """

    Parameters
    ----------
    column_id
        name of the column that the content to be colored is in
    filter_query
        content to be colored
    color
        text color
    backgroundColor

    Returns
    -------
    dict
        dict following the style_data_conditinal format for a dash table

    """
    return {
        'if': {
            'column_id': column_id,
            'filter_query': '{%s} = "%s"' % (column_id, filter_query)
        },
        'color': color,
        'backgroundColor': backgroundColor,
        'fontWeight': 'bold'
    }

def gen_style_data_conditional(df, custom_colors, maf_cols_value):
    """Generate mutation table coloring and add custom colors if given.

    Parameters
    ----------
    df
        df from gen_review_data
    custom_colors
        custom_colors kwarg from gen_review_app

    Returns
    -------
    style_data_conditinal : list of dicts
        list of dicts from format_style_data

    """
    style_data_conditional = []

    if 'Cluster_Assignment' in maf_cols_value:
        for n in df.Cluster_Assignment.unique():
            style_data_conditional.append(format_style_data('Cluster_Assignment', n, color=cluster_color(n)))

    if 'functional_effect' in maf_cols_value:
        style_data_conditional.extend([
            format_style_data('functional_effect', 'Likely Loss-of-function', backgroundColor='DarkOliveGreen'),
            format_style_data('functional_effect', 'Likely Gain-of-function', backgroundColor='DarkSeaGreen')
        ])

    if 'oncogenic' in maf_cols_value:
        style_data_conditional.append(format_style_data('oncogenic', 'Likely Oncogenic', backgroundColor='DarkOliveGreen'))

    if 'dbNSFP_Polyphen2_HDIV_ann' in maf_cols_value:
        style_data_conditional.append(format_style_data('dbNSFP_Polyphen2_HDIV_ann', 'D', backgroundColor='FireBrick'))

    if custom_colors != []:
        for list in custom_colors:
            style_data_conditional.append(format_style_data(list[0], list[1], list[2], list[3]))

    return style_data_conditional

def gen_maf_columns(df, idx, cols, hugo, variant, cluster):
    """Generate mutation table columns from selected columns and filtering dropdowns.

    Parameters
    ----------
    df
    idx
    cols
        column selection dropdown value
    hugo
        hugo symbol filtering dropdown value
    variant
        variant classification filtering dropdown value
    cluster
        cluster assignment filtering dropdown value

    Returns
    -------
    maf_df : pd.DataFrame
        unchanged df from maf_fn
    maf_cols_options : list of str
        options in mutation table columns dropdown
    maf_cols_value : list of str
        values selected in mutation table columns dropdown
    hugo_symbols : list of str
        all hugo symbols present in given data
    variant_classifications : list of str
        all variant classifications present in given data
    sorted(cluster_assignments) : list of int
        all cluster assignments present in given data, in order
    filtered_maf_df: pd.DataFrame
        maf_df after being filtered by hugo, variant, and cluster

    """
    start_pos = 'Start_position' or 'Start_Position'
    end_pos = 'End_position' or 'End_Position'
    protein_change = 'Protein_change' or 'Protein_Change'
    t_ref_count = 't_ref_count' or 't_ref_count_pre_forecall'
    t_alt_count = 't_alt_count' or 't_alt_count_pre_forecall'

    default_maf_cols = [
        'Hugo_Symbol',
        'Chromosome',
        start_pos,
        end_pos,
        protein_change,
        'Variant_Classification',
        t_ref_count,
        t_alt_count,
        'n_ref_count',
        'n_alt_count'
    ]

    #maf_cols_options = (list(maf_df))
    maf_cols_value = []
    hugo_symbols = []
    variant_classifications = []
    cluster_assignments = []

    maf_df = pd.read_csv(df.loc[idx, 'maf_fn'], sep='\t')
    #maf_df = pd.read_csv('~/Broad/JupyterReviewer/example_notebooks/example_data/all_mut_ccfs_maf_annotated_w_cnv_single_participant.txt', sep='\t')
    maf_cols_options = (list(maf_df))

    for col in default_maf_cols:
        if col in maf_cols_options and col not in maf_cols_value:
            maf_cols_value.append(col)

    for col in cols:
        if col in maf_cols_options and col not in maf_cols_value:
            maf_cols_value.append(col)

    for symbol in maf_df.Hugo_Symbol.unique():
        if symbol not in hugo_symbols:
            hugo_symbols.append(symbol)

    for classification in maf_df.Variant_Classification.unique():
        if classification not in variant_classifications:
            variant_classifications.append(classification)

    for n in maf_df.Cluster_Assignment.unique():
        if n not in cluster_assignments:
            cluster_assignments.append(n)

    filtered_maf_df = maf_df.copy()
    if hugo:
        filtered_maf_df = filtered_maf_df[filtered_maf_df.Hugo_Symbol.isin(hugo)]
    if variant:
        filtered_maf_df = filtered_maf_df[filtered_maf_df.Variant_Classification.isin(variant)]
    if cluster:
        filtered_maf_df = filtered_maf_df[filtered_maf_df.Cluster_Assignment.isin(cluster)]

    return [
        maf_df,
        maf_cols_options,
        maf_cols_value,
        hugo_symbols,
        variant_classifications,
        sorted(cluster_assignments),
        filtered_maf_df
    ]

def maf_callback_return(maf_cols_options, values, maf_cols_value, filtered_maf_df, table_size, custom_colors, hugo_symbols, variant_classifications, cluster_assignments):
    return [
        maf_cols_options,
        values,
        dash_table.DataTable(
            data=filtered_maf_df.to_dict('records'),
            columns=[{'name': i, 'id': i, 'selectable': True} for i in values],
            filter_action='native',
            sort_action='native',
            row_selectable='single',
            column_selectable='multi',
            page_action='native',
            page_current=0,
            page_size=table_size,
            style_data_conditional=gen_style_data_conditional(filtered_maf_df, custom_colors, maf_cols_value)
        ),
        hugo_symbols,
        variant_classifications,
        cluster_assignments
    ]

def gen_maf_table(df, idx, cols, hugo, table_size, variant, cluster, custom_colors):
    """Mutation table callback function with parameters being the callback inputs and returns being callback outputs."""
    maf_df, maf_cols_options, maf_cols_value, hugo_symbols, variant_classifications, cluster_assignments, filtered_maf_df = gen_maf_columns(df, idx, cols, hugo, variant, cluster)

    return maf_callback_return(maf_cols_options, maf_cols_value, maf_cols_value, filtered_maf_df, table_size, custom_colors, hugo_symbols, variant_classifications, cluster_assignments)

def internal_gen_maf_table(df, idx, cols, hugo, table_size, variant, cluster, custom_colors):
    """Mutation table internal callback function with parameters being the callback inputs and returns being callback outputs."""
    maf_df, maf_cols_options, maf_cols_value, hugo_symbols, variant_classifications, cluster_assignments, filtered_maf_df = gen_maf_columns(df, idx, cols, hugo, variant, cluster)

    return maf_callback_return(maf_cols_options, cols, maf_cols_value, filtered_maf_df, table_size, custom_colors, hugo_symbols, variant_classifications, cluster_assignments)
