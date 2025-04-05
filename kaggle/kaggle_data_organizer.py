import zipfile
import pandas as pd

with zipfile.ZipFile("iris.zip", "r") as zip_ref:
    zip_ref.extractall("data")
 

# Load the dataset
data = pd.read_csv("data/Iris.csv")

# Display the first few rows
print(data.head())