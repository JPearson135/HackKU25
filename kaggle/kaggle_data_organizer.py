import kaggle 
import os 
import pandas as pd

kaggle.api.authenticate()  # Authenticate with Kaggle API

kaggle.api.dataset_download_files('hanaksoy/health-and-sleep-statistics', path='.', unzip=True,)