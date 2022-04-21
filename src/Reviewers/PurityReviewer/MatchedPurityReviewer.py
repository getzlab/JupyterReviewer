from src.ReviewData import ReviewData, ReviewDataAnnotation
from src.ReviewDataApp import ReviewDataApp

import pandas as pd
import numpy as np
import functools
import time

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from jupyter_dash import JupyterDash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash import Dash, dash_table
import dash
import dash_bootstrap_components as dbc
import functools

from src.Reviewers.Reviewer import Reviewer
from src.lib.plot_cnp import plot_acr_interactive

from rpy2.robjects import r, pandas2ri
import rpy2.robjects as robjects


csize = {'1': 249250621, '2': 243199373, '3': 198022430, '4': 191154276, '5': 180915260,
        '6': 171115067, '7': 159138663, '8': 146364022, '9': 141213431, '10': 135534747,
        '11': 135006516, '12': 133851895, '13': 115169878, '14': 107349540, '15': 102531392,
        '16': 90354753, '17': 81195210, '18': 78077248, '19': 59128983, '20': 63025520,
        '21': 48129895, '22': 51304566, '23': 156040895, '24': 57227415}

def gen_data_summary_table(r, cols):
    return [[html.H1(f'{r.name} Data Summary'), dbc.Table.from_dataframe(r[cols].to_frame().reset_index())]]


def plot_cnp_histogram(fig, row, col, 
                       seg_df, 
                       mu_major_col, 
                       mu_minor_col, 
                       length_col,
                       max_mu=2, step=0.05):
    # bin over 
    mu_bins = np.arange(0, max_mu + step, step)
    mu_bins_counts = {b: 0 for b in mu_bins}
    for _, r in seg_df.iterrows():
        mu_bins_counts[mu_bins[np.argmax(r[mu_major_col] < mu_bins) - 1]] = r[length_col]
        mu_bins_counts[mu_bins[np.argmax(r[mu_minor_col] < mu_bins) - 1]] = r[length_col]
    
    mu_bin_counts_df = pd.DataFrame.from_dict(mu_bins_counts, 
                                              orient='index',
                                              columns=['count'])
    mu_bin_counts_df.index.name = 'mu_bin'
    mu_bin_counts_df = mu_bin_counts_df.reset_index()
    
    bar_trace = go.Bar(x=mu_bin_counts_df['count'], y=mu_bin_counts_df['mu_bin'], orientation='h')
    fig.add_trace(bar_trace, row=row, col=col)
    fig.update_xaxes(title_text='Length Count',  
                     row=row, col=col)
    fig.update_layout(showlegend=False)
    
    
def parse_absolute_soln(rdata_path: str):
    pandas2ri.activate()
    
    r_list_vector = robjects.r['load'](rdata_path)
    r_list_vector = robjects.r[r_list_vector[0]]
    r_data_id = r_list_vector.names[0]

    rdata_tables = r_list_vector.rx2(str(r_data_id))

    mode_res = rdata_tables.rx2('mode.res')
    mode_tab = mode_res.rx2('mode.tab')
    mod_tab_df = pd.DataFrame(columns=['alpha', 'tau', 'tau_hat', '0_line', 'comb',
                                       'clonal_cna_filter',
                                       # 'candidate_cna_absolute_copy_number',
                                       'reliable_seg_absolute_copy_number',
                                       'cna_comb_fit_score',
                                       'clonal_driver_mutations_filtered_table_idx',
                                       'clonal_driver_mutations_filtered'])
    list_type_cols = ['comb',
                      'clonal_cna_filter',
                      'reliable_seg_absolute_copy_number',
                      'clonal_driver_mutations_filtered_table_idx',
                      'clonal_driver_mutations_filtered']
    mod_tab_df[list_type_cols] = mod_tab_df[list_type_cols].astype('object')
    mod_tab_df['alpha'] = mode_tab[:, 0]
    err = estimate_purity_ci(mode_tab[:, 0])
    mod_tab_df['alpha_CIL'] = mode_tab[:, 0] - err
    mod_tab_df['alpha_CIH'] = mode_tab[:, 0] + err
    mod_tab_df['tau'] = mode_tab[:, 1]
    mod_tab_df['tau_hat'] = mode_tab[:, 7]
    mod_tab_df['0_line'] = mode_tab[:, 3]
    mod_tab_df['step_size'] = (1.0 - mod_tab_df['0_line']) / (mod_tab_df['tau'] / 2.0)
    return mod_tab_df
    
def gen_mut_figure(r, maf_col, 
                   chromosome_col='Chromosome', 
                   start_position_col='Start_position', 
                   hugo_symbol_col='Hugo_Symbol',
                   variant_type_col='Variant_Type',
                   alt_count_col='t_alt_count',
                   ref_count_col='t_ref_count',
                   csize=csize,
                   hover_data=[]  # TODO: include
                  ):
    fig = make_subplots(rows=1, cols=1)
    maf_df = pd.read_csv(r[maf_col], sep='\t')
    if maf_df[chromosome_col].dtype == 'object':
        maf_df[chromosome_col].replace({'X': 23, 'Y': 24}, inplace=True)
        maf_df[chromosome_col] = maf_df[chromosome_col].astype(str)
    
    maf_df['new_position'] = maf_df.apply(lambda r: csize[r[chromosome_col]] + r[start_position_col], axis=1)
    maf_df['tumor_f'] = maf_df[alt_count_col] / (maf_df[alt_count_col] + maf_df[ref_count_col])
    
    # color by clonal/subclonal
    fig = px.scatter(maf_df, x='new_position', y='tumor_f', marginal_y='histogram')
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    fig.update_yaxes(range=[0, 1])
    return fig
    
def gen_cnp_figure(r, 
                   acs_col,
                   sigmas=True, 
                   mu_major_col='mu.major', 
                   mu_minor_col='mu.minor', 
                   length_col='length',
                   csize=csize):
    
    seg_df = pd.read_csv(r[acs_col], sep='\t')
    layout = go.Layout(
            plot_bgcolor='rgba(0,0,0,0)',
        )
    cnp_fig = make_subplots(rows=1, cols=2, shared_yaxes=True)
    plot_acr_interactive(seg_df, cnp_fig, csize, sigmas=sigmas, row=0, col=0)
    
    plot_cnp_histogram(cnp_fig, 1, 2,
                       seg_df,
                       mu_major_col, 
                       mu_minor_col, 
                       length_col)
    
    return cnp_fig

def gen_absolute_figures(r, 
                         acs_col, 
                         maf_col,
                         chromosome_col='Chromosome', 
                         start_position_col='Start_position', 
                         variant_type_col='Variant_Type',
                         alt_count_col='t_alt_count',
                         ref_count_col='t_ref_count',
                         sigmas=True, 
                         mu_major_col='mu.major', 
                         mu_minor_col='mu.minor', 
                         length_col='length',
                         csize=csize):
    cnp_fig = gen_cnp_figure(r, 
                             acs_col,
                             sigmas=sigmas, 
                             mu_major_col=mu_major_col,
                             mu_minor_col=mu_minor_col,
                             length_col=length_col,
                             csize=csize)
    mut_fig = gen_mut_figure(r, maf_col, 
                             chromosome_col=chromosome_col, 
                             start_position_col=start_position_col,
                             variant_type_col=variant_type_col,
                             alt_count_col=alt_count_col,
                             ref_count_col=ref_count_col,
                             csize=csize
                            )
    
    return [cnp_fig, mut_fig]
    

class MatchedPurityReviewer(Reviewer):


    def gen_review_data_object(session_dir, df: pd.DataFrame, more_annot_cols: {str: ReviewDataAnnotation}):

        annot_data = {'purity': ReviewDataAnnotation( 'number', 
                                           validate_input=lambda x: (x <= 1.0) and (x >= 0.0)),
                      'ploidy': ReviewDataAnnotation('number', 
                                           validate_input=lambda x: x >= 0.0)}

        # TODO: make sure there are no duplicates
        rd = ReviewData(review_dir=session_dir,
                        df = df, # optional if directory above already exists. 
                        annotate_data = {**annot_data, **more_annot_cols})

        return rd

    def gen_review_data_app(review_data_obj, 
                            sample_info_cols,
                            acs_col,
                            maf_col):

        app = ReviewDataApp(review_data_obj)


        app.add_custom_component('sample-info-component', 
                                  html.Div(children=[html.H1('Data Summary'), 
                                                     dbc.Table.from_dataframe(df=pd.DataFrame())],
                                           id='sample-info-component'
                                          ), 
                                  callback_output=[Output('sample-info-component', 'children')],
                                  func=gen_data_summary_table, 
                                  cols=sample_info_cols)

        # For now just plot copy number profile
        app.add_custom_component('cnp-plot',
                                 html.Div(children=[html.H1('Copy Number Profile'), 
                                                    dcc.Graph(id='cnp-graph', figure={}),
                                                    dcc.Graph(id='mut-graph', figure={})
                                                   ]),
                                 callback_output=[Output('cnp-graph', 'figure'), Output('mut-graph', 'figure')],
                                 func=gen_absolute_figures,
                                 acs_col=acs_col,
                                 maf_col=maf_col
                                )

        return app
                    