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

#Solar_data collection parameters
latitude = 52.943
longitude = -1.133
start_year = 2005
end_year = 2016

surface_tilt = 35
surface_azimuth = 0

#Get solar data
df_PVGIS, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt,surface_azimuth=surface_azimuth)

#Determine solar cell temp for solar_data
cell_temp = pvlib.temperature.pvsyst_cell(df_PVGIS['poa_global'], temp_air = df_PVGIS['temp_air'], wind_speed=df_PVGIS['wind_speed'], u_c=29, u_v=0)

#Solar cell specification
temp_coef = -0.45/100 #Temperature coefficient %/C
power = 215 #Nominal power 215W per pannel

#Determine dc power output from PV system model
array_power = pvlib.pvsystem.pvwatts_dc(df_PVGIS['poa_global'], temp_cell=cell_temp, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)

#Battery specifications
bat_cap = 125*4*12 #battery capacity, 125Ah x 4 batteries x 12V
cut_off = 0.4 #fractional cutoff for lead-acid battery 40%
cam_consump = 600/24 #Daily consumption per hour 600Wh for the day

#Battery data frame
df_bat = {}
df_bat = pd.DataFrame(index=df_PVGIS.index)
df_bat['consumption'] = cam_consump
df_bat['live_cap'] = bat_cap
df_bat['Production'] = array_power
df_bat['net_change_per_hour'] = array_power - cam_consump
df_bat['Energy_excess'] = 0 
df_bat['full_count'] = 0 
df_bat['empty_count'] = 0 


#Model battery charge/discharge at each hour
for i in range(len(df_bat['consumption'])-1):
    
    df_bat['live_cap'][i] = df_bat['live_cap'][i] + df_bat['net_change_per_hour'][i]
    
    if df_bat['live_cap'][i]>=bat_cap:
        df_bat['Energy_excess'][i] =  df_bat['net_change_per_hour'][i]
        df_bat['live_cap'][i] = bat_cap
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]
    
    elif df_bat['live_cap'][i] <= 0:
        df_bat['live_cap'][i] = 0
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]
        
    else:
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]


#
df_bat.loc[df_bat['live_cap']<bat_cap*cut_off,'empty_count'] = 1
df_bat.loc[df_bat['live_cap']==bat_cap,'full_count'] = 1

df = df_bat.resample('D').sum()
df['full_count'] = np.sign(df['full_count'])
df['empty_count'] = np.sign(df['empty_count'])

df_month_tot = df[['full_count','empty_count','Production','Energy_excess']].resample('M').sum()
df_month_tot['full %'] = 100*df_month_tot['full_count']/df_month_tot.index.day
df_month_tot['empty %'] = 100*df_month_tot['empty_count']/df_month_tot.index.day
df_month_tot['Production'] = df_month_tot['Production']/df_month_tot.index.day
df_month_tot['Energy_excess'] = df_month_tot['Energy_excess']/df_month_tot.index.day

df_month_avg = df_month_tot.groupby(df_month_tot.index.month).mean()
df_month_avg['Month']=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df_month_avg.set_index('Month', inplace=True)


##Plots 

#Percentage of Days with full/empty battery
df_month_avg[['empty %','full %']].plot.bar()
plt.ylabel('Percentage days empty/full (Avg over years)')
plt.show()

#Mean number of days in each month where battery goes below cut-off
df_month_avg['empty_count'].plot.bar()
plt.ylabel('Mean days requiring refill')
plt.show()

#Average monthyl production and uncaptured energy
df_month_avg[['Production','Energy_excess']].plot.bar()
plt.ylabel('Avg Energy Wh')
plt.show()



