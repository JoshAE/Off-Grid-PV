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
def shuffle_years(group):
    group = group.copy()
    shuffled_years = np.random.permutation(group['year'].values)
    group['shuffled_year'] = shuffled_years
    return group

def shuffle_solar_data(df):
    df_copy = df.copy()
    # Extracting year and month
    df_copy['year'] = df.index.year
    df_copy['month'] = df.index.month
    df_copy['day'] = df.index.day
    df_copy['time_stamp'] = df.index.time
    
    start_year = df_copy['year'].min()
    end_year = df_copy['year'].max()
    
    # Shuffle years within each month
    shuffled_df = pd.DataFrame()
    
    grouped_df = df_copy.groupby(['month','day','time_stamp']).apply(shuffle_years).reset_index(drop=True)
    
    shuffled_df = grouped_df.sort_values(by=['shuffled_year','month','day','time_stamp'])
    date_range = pd.date_range(start=str(end_year + (start_year%4) - (end_year%4))+'-01-01 00:11:00+00:00', end=str(2*end_year - start_year + (start_year%4) - (end_year%4))+'-12-31 23:11:00+00:00',periods=len(shuffled_df))
    
    # Set the new index
    shuffled_df['timestamp'] = date_range
    shuffled_df = shuffled_df.set_index('timestamp')
    
    shuffled_df = shuffled_df.drop(['year', 'month','day','shuffled_year','time_stamp'], axis=1)

    return shuffled_df

#Solar_data collection parameters
latitude = 52.943
longitude = -1.133

start_year = 2005
end_year = 2016

surface_tilt = 35
surface_azimuth = 0

#Get solar data
df, meta_p1, inputs_p1 = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt,surface_azimuth=surface_azimuth)
#Determine solar cell temp for solar_data
cell_temp_p1 = pvlib.temperature.pvsyst_cell(df['poa_global'], temp_air = df['temp_air'], wind_speed=df['wind_speed'], u_c=29, u_v=0)

#Solar cell specification
temp_coef = -0.45/100 #Temperature coefficient %/C
power = 215 #Nominal power 215W per pannel

#Determine dc power output from PV system model
df_p = pd.DataFrame()
df_p['power'] = pvlib.pvsystem.pvwatts_dc(df['poa_global'], temp_cell=cell_temp_p1, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)

df_copy = df_p.copy()
# Extracting year and month
df_copy['year'] = df_p.index.year
df_copy['month'] = df_p.index.month
df_copy['day'] = df_p.index.day
df_copy['time_stamp'] = df_p.index.time

start_year = df_copy['year'].min()
end_year = df_copy['year'].max()

# Shuffle years within each month
shuffled_df = pd.DataFrame()

grouped_df = df_copy.groupby(['month','day','time_stamp']).apply(shuffle_years).reset_index(drop=True)

shuffled_df = grouped_df.sort_values(by=['shuffled_year','month','day','time_stamp'])
date_range = pd.date_range(start=str(end_year + (start_year%4) - (end_year%4))+'-01-01 00:11:00+00:00', end=str(2*end_year - start_year + (start_year%4) - (end_year%4))+'-12-31 23:11:00+00:00',periods=len(shuffled_df))

# Set the new index
shuffled_df['timestamp'] = date_range
shuffled_df = shuffled_df.set_index('timestamp')

shuffled_df = shuffled_df.drop(['year', 'month','day','shuffled_year','time_stamp'], axis=1)


df_extend = pd.concat([df,shuffle_solar_data(df)])




