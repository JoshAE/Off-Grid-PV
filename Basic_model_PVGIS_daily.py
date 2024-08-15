#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 25 10:39:28 2024
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
latitude = 53.4
longitude = -2.16

start_year = 2005
end_year = 2015

surface_tilt = np.array([35,35])
surface_azimuth = np.array([0,180])

#Get solar data
df_PVGIS_p1, meta_p1, inputs_p1 = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt[0],surface_azimuth=surface_azimuth[0])
df_PVGIS_p2, meta_p2, inputs_p2 = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt[1],surface_azimuth=surface_azimuth[1])

#Determine solar cell temp for solar_data
cell_temp_p1 = pvlib.temperature.pvsyst_cell(df_PVGIS_p1['poa_global'], temp_air = df_PVGIS_p1['temp_air'], wind_speed=df_PVGIS_p1['wind_speed'], u_c=29, u_v=0)
cell_temp_p2 = pvlib.temperature.pvsyst_cell(df_PVGIS_p2['poa_global'], temp_air = df_PVGIS_p2['temp_air'], wind_speed=df_PVGIS_p2['wind_speed'], u_c=29, u_v=0)

#Solar cell specification
temp_coef = -0.45/100 #Temperature coefficient %/C
power = 215 #Nominal power 215W per pannel

#Determine dc power output from PV system model
array_power_p1 = pvlib.pvsystem.pvwatts_dc(df_PVGIS_p1['poa_global'], temp_cell=cell_temp_p1, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)
array_power_p2 = pvlib.pvsystem.pvwatts_dc(df_PVGIS_p2['poa_global'], temp_cell=cell_temp_p2, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)

#Battery specifications
bat_cap = 125*4*12 #battery capacity, 125Ah x 4 batteries x 12V
cut_off = 0.4 #fractional cutoff for lead-acid battery 40%
cam_consump = 840/24 #Daily consumption per hour 600Wh for the day

#Battery data frame
df_bat = {}
df_bat = pd.DataFrame(index=df_PVGIS_p1.index)
df_bat['consumption'] = cam_consump
df_bat['live_cap'] = bat_cap
df_bat['Production'] = array_power_p1 + array_power_p2
df_bat['net_change_per_hour'] = array_power_p1 + array_power_p2 - cam_consump
df_bat['Energy_excess'] = 0 
df_bat['full_count'] = 0 
df_bat['empty_count'] = 0 

## Select start date when tower is placed
setup_date = '2006-04-01 00:11:00 UTC' #mm/dd/2006

#Reorders data frame for start date
timestamp_to_reorder = pd.to_datetime(setup_date)

# Find the index of the timestamp
df_part1 = df_bat.loc[:timestamp_to_reorder]
df_part2 = df_bat.loc[timestamp_to_reorder:].iloc[1:]

# Concatenate with the part from the timestamp first
df_bat = pd.concat([df_part2, df_part1])
df_new2 = pd.concat([df_part2, df_part1])


REFILL = True #Batery refill when below cut-off

if REFILL == False:
    #Model battery charge/discharge at each hour
    for i in range(len(df_bat['consumption'])-1):
        df_bat.loc[df_bat.index[i], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap'] + df_bat.loc[df_bat.index[i], 'net_change_per_hour']
        
        if df_bat['live_cap'][i]>=bat_cap:
            df_bat.loc[df_bat.index[i], 'Energy_excess'] = df_bat.loc[df_bat.index[i], 'net_change_per_hour']
            df_bat.loc[df_bat.index[i], 'live_cap'] = bat_cap
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap']
        
        elif df_bat['live_cap'][i] <= 0:
            df_bat.loc[df_bat.index[i], 'live_cap'] = 0
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap']
            
        else:
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap']

elif REFILL == True:
    #Model battery charge/discharge at each hour
    for i in range(len(df_bat['consumption'])-1):
        df_bat.loc[df_bat.index[i], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap'] + df_bat.loc[df_bat.index[i], 'net_change_per_hour']
        
        if df_bat['live_cap'][i]>=bat_cap:
            df_bat.loc[df_bat.index[i], 'Energy_excess'] = df_bat.loc[df_bat.index[i], 'net_change_per_hour']
            df_bat.loc[df_bat.index[i], 'live_cap'] = bat_cap
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap']
        
        elif df_bat['live_cap'][i] <= bat_cap*cut_off:
            df_bat.loc[df_bat.index[i], 'live_cap'] = bat_cap*cut_off
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = bat_cap
            
        else:
            df_bat.loc[df_bat.index[i+1], 'live_cap'] = df_bat.loc[df_bat.index[i], 'live_cap']

#
df_bat.loc[df_bat['live_cap'] <= bat_cap*cut_off,'empty_count'] = 1
df_bat.loc[df_bat['live_cap'] == bat_cap,'full_count'] = 1

df = df_bat.resample('D').sum()
df['full_count'] = np.sign(df['full_count'])
df['empty_count'] = np.sign(df['empty_count'])

df_month_tot = df[['full_count','empty_count','Production','Energy_excess']].resample('M').sum()
df_month_tot['full %'] = 100*df_month_tot['full_count']/df_month_tot.index.day
df_month_tot['empty %'] = 100*df_month_tot['empty_count']/df_month_tot.index.day
df_month_tot['Production'] = df_month_tot['Production']/df_month_tot.index.day
df_month_tot['Energy_excess'] = df_month_tot['Energy_excess']/df_month_tot.index.day

df_month_avg = df_month_tot.groupby(df_month_tot.index.month).mean()
df_month_avg['Month'] = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df_month_avg.set_index('Month', inplace=True)

df_new = df_month_tot.groupby(df_month_tot.index.month).agg({'Production': ['mean', 'std'], 'Energy_excess': ['mean', 'std']})

##Plots 
#Percentage of Days with full/empty battery
df_month_avg[['empty %','full %']].plot.bar()
plt.ylabel('Percentage days empty/full (Avg over years)')
plt.show()

#Mean number of days in each month where battery goes below cut-off
df_month_avg['empty_count'].plot.bar()
plt.ylabel('Mean days requiring refill')
plt.ylim([0,31])
plt.show()

#Average monthyl production and uncaptured energy
df_new['Production']['mean'].plot.bar(yerr=[df_new['Production']['std']],capsize=6)
df_new['Energy_excess']['mean'].plot.bar(color='r',yerr=[df_new['Energy_excess']['std']],capsize=6)
plt.ylabel('Avg Energy Wh')
plt.show()

