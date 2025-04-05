import kaggle 
import os 
import pandas as pd

kaggle.api.authenticate()  # Authenticate with Kaggle API

output_dir = "datasets"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)  # Create the directory if it doesn't exist

kaggle.api.dataset_download_files(
    'hanaksoy/health-and-sleep-statistics', 
    path=output_dir, 
    unzip=True)

kaggle.api.dataset_download_files('shariful07/student-mental-health', 
    path=output_dir,
    unzip=True)

