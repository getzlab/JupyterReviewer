from .ReviewData import ReviewData, ReviewDataAnnotation
from .ReviewDataApp import ReviewDataApp, valid_annotation_app_display_types

import pandas as pd
import os
from dash.dependencies import State
from typing import Union, List
from abc import ABC, abstractmethod


# class ReviewerTemplate(ABC):
    
class ReviewerTemplate(ABC):
    
    def __init__(self):
        self.review_data = None
        self.app = None
        self.autofill_dict = {}
        self.annot_app_display_types_dict = {}
    
    @abstractmethod
    def gen_review_data(self,
                        review_data_fn: str, 
                        description: str = '',
                        df: pd.DataFrame = pd.DataFrame(), 
                        review_data_annotation_list: [ReviewDataAnnotation] = None,
                        reuse_existing_review_data_fn: str = None, *args, **kwargs) -> ReviewData:
        
        return None

    @abstractmethod
    def gen_review_data_annotations(self):
        """
        Add annotations to review data object
        """
        return None

    @abstractmethod
    def gen_review_app(self) -> ReviewDataApp:
        app = ReviewDataApp()
        app.add_component()
        
        return app

    @abstractmethod
    def gen_review_data_annotation_app_display(self):
        return None

    @abstractmethod
    def gen_autofill(self):
        return None
    
    # Public methods
    def set_review_data(self,
                        review_data_fn: str, 
                        description: str='', 
                        df: pd.DataFrame = pd.DataFrame(), 
                        # review_data_annotation_list: List[ReviewDataAnnotation] = None,
                        reuse_existing_review_data_fn: str = None,  
                        **kwargs):
        
        if os.path.exists(review_data_fn) or ((reuse_existing_review_data_fn is not None) and 
                                              os.path.exists(reuse_existing_review_data_fn)):
            self.review_data = ReviewData(review_data_fn=review_data_fn,
                                          description=description,
                                          df=df,
                                          # review_data_annotation_dict=review_data_annotation_dict,
                                          reuse_existing_review_data_fn=reuse_existing_review_data_fn)
        else:
            self.review_data = self.gen_review_data(review_data_fn,
                                                    description,
                                                    df,
                                                    # review_data_annotation_list,
                                                    reuse_existing_review_data_fn,
                                                    **kwargs)

    def set_review_data_annotations(self):
        self.gen_review_data_annotations()

    def add_review_data_annotation(self, annot_name: str, review_data_annotation: ReviewDataAnnotation):
        self.review_data.add_annotation(annot_name, review_data_annotation)
    
    def set_review_app(self, *args, **kwargs):
        self.app = self.gen_review_app(*args, **kwargs)

    def set_review_data_annotations_app_display(self):
        self.gen_review_data_annotation_app_display()

    def add_review_data_annotations_app_display(self, name, app_display_type):
        if name not in self.review_data.review_data_annotation_dict.keys():
            raise ValueError(f"Invalid annotation name '{name}'. "
                             f"Does not exist in review data object annotation table")

        if app_display_type not in valid_annotation_app_display_types:
            raise ValueError(f"Invalid app display type {app_display_type}. "
                             f"Valid options are {valid_annotation_app_display_types}")

        # TODO: check if display type matches annotation type (list vs single value)

        self.annot_app_display_types_dict[name] = app_display_type

    def set_autofill(self):
        self.gen_autofill()
        
    def add_autofill(self, component_name: str, fill_value: Union[State, str, float], annot_col: str):
        if component_name not in self.autofill_dict.keys():
            self.autofill_dict[component_name] = {annot_col: fill_value}
        else:
            self.autofill_dict[component_name][annot_col] = fill_value
        
        # verify 
        self.app.gen_autofill_buttons_and_states(self.review_data, self.autofill_dict)

    def run(self, 
            mode='external', 
            host='0.0.0.0', 
            port=8050):
        self.app.run(review_data=self.review_data, 
                     autofill_dict=self.autofill_dict,
                     annot_app_display_types_dict=self.annot_app_display_types_dict,
                     mode=mode,
                     host=host,
                     port=port)
