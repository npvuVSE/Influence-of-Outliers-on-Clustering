import numpy as np
import os
import pandas as pd
from kmodes.kmodes import KModes 
from ucimlrepo import fetch_ucirepo
from sklearn.cluster import KMeans, DBSCAN
from scipy.io.arff import loadarff
import matplotlib.pyplot as plt 

from algorithms.quantitative.cbrw import CBRW
from algorithms.quantitative.fpof import FPOF
from tabulate import tabulate
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc, ConfusionMatrixDisplay

from data.scripts.get_data import get_data_numerical, get_data_categorical
from data.scripts.get_data_from_csv import get_data_from_csv, convert_iris_to_categorical
from data.scripts.data_transformations import split_df, concat_df
from data.scripts.plant_outliers import add_local_outliers, add_global_outliers, add_contextual_outliers, add_collective_outliers


def detect_outliers_cbrw(X, contamination):
    detector = CBRW()
    observations = X.to_dict('records')
    detector.add_observations(observations)
    detector.fit()
    scores = detector.score(observations)
    indexed_scores = [(i, round(score, 4)) for i, score in enumerate(scores)]
    indexed_scores.sort(key=lambda x: x[1], reverse=True)

    num_outliers = int(len(X) * contamination)
    outlier_indices = [i for i, score in indexed_scores[:num_outliers]]
    is_outlier = [i in outlier_indices for i in range(len(X))]

    return is_outlier

def detect_outliers_fpof(X, min_support, contamination):
    fpof_values, top_n_transactions, top_k_contradict_patterns = FPOF(X, min_support=min_support, top_n=10, top_k=2)

    indexed_values = [(i, value) for i, value in enumerate(fpof_values)]
    indexed_values.sort(key=lambda x: x[1])

    num_outliers = int(len(fpof_values) * contamination)
    outlier_indices = [i for i, value in indexed_values[:num_outliers]]
    is_outlier = [i in outlier_indices for i in range(len(fpof_values))]

    return is_outlier

def calculate_smc_dissimilarity(row, centroid):
    matches = sum(row == centroid)
    total_attributes = len(row)
    
    smc_similarity = matches / total_attributes
    return 1 - smc_similarity

def detect_outliers_kmodes(X, contamination, n_clusters=3, init='Huang', n_init=5):
    kmodes = KModes(n_clusters=n_clusters, init=init, n_init=n_init)
    clusters = kmodes.fit_predict(X)

    dissimilarity_scores = pd.Series([
        calculate_smc_dissimilarity(X.iloc[i], kmodes.cluster_centroids_[clusters[i]])
        for i in range(len(X))
    ])

    indexed_scores = [(i, score) for i, score in enumerate(dissimilarity_scores)]
    indexed_scores.sort(key=lambda x: x[1], reverse=True)

    num_outliers = int(len(dissimilarity_scores) * contamination)
    outlier_indices = [i for i, score in indexed_scores[:num_outliers]]

    outliers = [i in outlier_indices for i in range(len(dissimilarity_scores))]
    return outliers

######################
# Data with outliers #
######################

# NB_BINS = 7

# outlier_names = ['local', 'global', 'contextual', 'collective']
# outlier_percentages = [1, 5, 10]

# data_wOutliers = {}

# outlier_detection_methods = {
#     'FPOF': FPOF,
#     'CBRW': CBRW,
#     'KModes': KModes
# }

# for name in outlier_names:
#     for percentage in outlier_percentages:
#         df = pd.read_csv(f'data/categorical/wOutliers/run1/df_{name}_outliers_{percentage}percent.csv')
#         data_wOutliers[f'df_{name}_outliers_{percentage}percent'] = df

# for name, df in data_wOutliers.items():
#     for column in df.columns[:-2]:
#         df[column] = pd.cut(df[column], bins=NB_BINS)


# for name, df in data_wOutliers.items():
#     X, y = split_df(df, number_of_columns=2)
#     true_outliers = y['IsOutlier']
#     X = X.astype(str)
#     percentage = int(name.split('_')[-1].replace('percent', '')) / 100 - 0.0029

#     print(f'Processing {name} with {len(X)} observations and {len(X.columns)} features')

#     # Kmodes
#     kmodes = KModes(n_clusters=3, init='Huang', n_init=5)
#     clusters = kmodes.fit_predict(X)

#     dissimilarity_scores = pd.Series([
#         calculate_smc_dissimilarity(X.iloc[i], kmodes.cluster_centroids_[clusters[i]])
#         for i in range(len(X))
#     ])

#     indexed_scores = [(i, score) for i, score in enumerate(dissimilarity_scores)]
#     indexed_scores.sort(key=lambda x: x[1], reverse=True)

#     num_outliers = int(len(dissimilarity_scores) * percentage)
#     outlier_indices = [i for i, score in indexed_scores[:num_outliers]]
#     outliers_kmodes = [i in outlier_indices for i in range(len(dissimilarity_scores))]
#     # print(outliers_kmodes)

#     cm = confusion_matrix(true_outliers, outliers_kmodes)
#     cm_df = pd.DataFrame(cm, columns=['Predicted Negative', 'Predicted Positive'], index=['Actual Negative', 'Actual Positive'])
#     print(tabulate(cm_df, headers='keys', tablefmt='psql'))

#     # FPOF
#     outliers_fpof = detect_outliers_fpof(X, min_support=0.1, contamination=percentage)
#     # print(outliers_fpof)
#     cm = confusion_matrix(true_outliers, outliers_fpof)
#     cm_df = pd.DataFrame(cm, columns=['Predicted Negative', 'Predicted Positive'], index=['Actual Negative', 'Actual Positive'])
#     print(tabulate(cm_df, headers='keys', tablefmt='psql'))

#     # CBRW
#     outliers_cbrw = detect_outliers_cbrw(X, contamination=percentage)
#     # print(outliers_cbrw)
#     cm = confusion_matrix(true_outliers, outliers_cbrw)
#     cm_df = pd.DataFrame(cm, columns=['Predicted Negative', 'Predicted Positive'], index=['Actual Negative', 'Actual Positive'])
#     print(tabulate(cm_df, headers='keys', tablefmt='psql'))


NB_BINS = 7

outlier_names = ['local', 'global', 'contextual', 'collective']
outlier_percentages = [1, 5, 10]

data_wOutliers = {}

outlier_detection_methods = {
    'FPOF': detect_outliers_fpof,
    'CBRW': detect_outliers_cbrw,
    'KModes': detect_outliers_kmodes
}

results = {
    outlier_type: {
        percentage: {
            method: {
                'accuracy': [],
                'db_scores': []
            } for method in outlier_detection_methods
        }
        for percentage in outlier_percentages
    }
    for outlier_type in outlier_names
}    

for run in range(1, 51):
    print(f'Processing run {run}')
    for outlier_type in outlier_names:
        for percentage in outlier_percentages:
            df = pd.read_csv(f'data/categorical/wOutliers/run{run}/df_{outlier_type}_outliers_{percentage}percent.csv')
            # print(run, outlier_type, percentage)
            
            # data_wOutliers[f'df_{name}_outliers_{percentage}percent'] = df
            for method_name, method in outlier_detection_methods.items():
                # print(f'Processing {method_name} method')
                X, y = split_df(df, number_of_columns=2)
                true_outliers = y['IsOutlier']
                X = X.astype(str)

                if percentage == 1:
                    percentage_float = percentage / 100 - 0.001
                else:
                    percentage_float = percentage / 100 - 0.005

                if method_name == 'FPOF':
                    outliers = method(X, min_support=0.1, contamination=percentage_float)
                else:
                    outliers = method(X, contamination=percentage_float)
                # print(outliers)

                directory = f'data/categorical/wOutliers/run{run}/removed/{method_name}'
                if not os.path.exists(directory):
                    os.makedirs(directory)

                df_no_outliers = df[~np.array(outliers)]
                print(df_no_outliers.tail(15))
                df_no_outliers.to_csv(f'data/categorical/wOutliers/run{run}/removed/{method_name}/df_{outlier_type}_outliers_{percentage}percent_removed_{method_name}.csv', index=False)

                accuracy = accuracy_score(true_outliers, outliers)
                precision = precision_score(true_outliers, outliers)

                results[outlier_type][percentage][method_name]['accuracy'].append(accuracy)
                results[outlier_type][percentage][method_name]['db_scores'].append(precision)
                print(f'Apending to {outlier_type} - {percentage} - {method_name}: Accuracy = {accuracy} - Precision = {precision}')
                # print(f'Accuracy: {accuracy}')
                # print(f'Precision: {precision}')
                # print(f'{accuracy * 100:.2f} & {precision * 100:.2f} \\\\')
                # print(results[outlier_type][percentage][method_name])

                cm = confusion_matrix(true_outliers, outliers)
                cm_df = pd.DataFrame(cm, columns=['Predicted Negative', 'Predicted Positive'], index=['Actual Negative', 'Actual Positive'])
                print(tabulate(cm_df, headers='keys', tablefmt='psql'))

for outlier_type, type in results.items():
    for percentage, methods in type.items():
        print(f'{outlier_type} & {percentage} &', end=' ')
        for method, scores in methods.items():
            avg_accuracy = np.mean(scores["accuracy"])
            avg_db_scores = np.mean(scores["db_scores"])
            print(f' \\{method} & {avg_accuracy * 100:.2f} & {avg_db_scores * 100:.2f} \\\\', end=' ')
        print()
        