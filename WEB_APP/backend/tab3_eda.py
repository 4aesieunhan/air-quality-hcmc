import pandas as pd
import numpy as np

def get_correlation_matrix(df, pollutants_list):
    """
    Computes the correlation matrix (Pearson) between the given pollutants.
    """
    if df.empty or not pollutants_list:
        return pd.DataFrame()

    pollutants_df = df[pollutants_list].dropna(axis=0) # Drop rows with NaN
    if pollutants_df.empty:
        return pd.DataFrame()
        
    correlation_matrix = pollutants_df.corr(method='pearson')
    
    return correlation_matrix

def get_distribution_data(df, pollutant_name):
    """
    Returns the distribution of a specific pollutant across all stations for visualization.
    """
    if df.empty or pollutant_name not in df.columns:
        return pd.Series()

    data = df[pollutant_name].dropna()
    
    # Optional: Basic outlier removal for cleaner plot?
    # Q1 = data.quantile(0.25)
    # Q3 = data.quantile(0.75)
    # IQR = Q3 - Q1
    # data = data[~((data < (Q1 - 1.5 * IQR)) | (data > (Q3 + 1.5 * IQR)))]
    
    return data
