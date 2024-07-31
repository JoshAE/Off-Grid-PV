#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 30 10:51:50 2024

@author: joshua
"""

import os  # for getting environment variables
import pathlib  # for finding the example dataset
import pvlib
import pandas as pd  # for data wrangling
import matplotlib.pyplot as plt  # for visualization
from pvlib import location
from pvlib.modelchain import ModelChain
import numpy as np
import itertools
#Solar_data collection parameters
latitude = 52.943
longitude = -1.133

start_year = 2005
end_year = 2016

surface_tilt = 35
surface_azimuth = 0

#Get solar data
df_PVGIS_p1, meta_p1, inputs_p1 = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt,surface_azimuth=surface_azimuth)

# Extracting year and month
df_PVGIS_p1['year'] = df_PVGIS_p1.index.year
df_PVGIS_p1['month'] = df_PVGIS_p1.index.month
df_PVGIS_p1['day'] = df_PVGIS_p1.index.day
df_PVGIS_p1['time_stamp'] = df_PVGIS_p1.index.time

# Shuffle years within each month
shuffled_df = pd.DataFrame()

def shuffle_years(group):
    group = group.copy()
    shuffled_years = np.random.permutation(group['year'].values)
    group['shuffled_year'] = shuffled_years
    return group

grouped_df = df_PVGIS_p1.groupby(['month','day','time_stamp']).apply(shuffle_years).reset_index(drop=True)

shuffled_df = grouped_df.sort_values(by=['shuffled_year','month','day','time_stamp'])
date_range = pd.date_range(start=str(end_year + (start_year%4) - (end_year%4))+'-01-01 00:11:00+00:00', end=str(2*end_year - start_year + (start_year%4) - (end_year%4))+'-12-31 23:11:00+00:00',periods=len(shuffled_df))

# Set the new index
shuffled_df['timestamp'] = date_range
shuffled_df = shuffled_df.set_index('timestamp')

shuffled_df = shuffled_df.drop(['year', 'month','day','shuffled_year','time_stamp'], axis=1)
