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
def get_pvgis_data(latitude, longitude, start_year, end_year, surface_tilt=35, surface_azimuth=0, service='PVGIS-SARAH'):
    """
    Retrieve solar data from PVGIS for a specific location and range of years.

    Parameters:
    - latitude: float, Latitude of the location
    - longitude: float, Longitude of the location
    - start_year: int, Start year for the data retrieval
    - end_year: int, End year for the data retrieval
    - service: str, PVGIS service to use (default is 'PVGIS-SARAH')

    Returns:
    - data: DataFrame, Retrieved solar data
    """
    all_data = []

    for year in range(start_year, end_year + 1):
        print(f"Retrieving data for year {year}...")
        result, meta, inputs = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=year, end=year, map_variables=True, components=True, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=35)
        year_data = result[0]
        year_data['year'] = year
        all_data.append(year_data)

    # Concatenate all yearly data into a single DataFrame
    data = pd.concat(all_data)
    return data

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
df_bat['current_capacity_Wh'] = bat_cap
df_bat['live_cap'] = bat_cap
df_bat['Production'] = array_power
df_bat['net_change_per_hour'] = array_power - cam_consump
df_bat['empty_count'] = 0 
df_bat['full_count'] = 0
df_bat['bat_refill_count'] = 0

#Model battery charge/discharge at each hour
for i in range(len(df_bat['consumption'])-1):
    
    df_bat['current_capacity_Wh'][i] = df_bat['current_capacity_Wh'][i] + df_bat['net_change_per_hour'][i]
    df_bat['live_cap'][i] = df_bat['live_cap'][i] + df_bat['net_change_per_hour'][i]
    
    if df_bat['current_capacity_Wh'][i]>bat_cap:
        df_bat['current_capacity_Wh'][i] = bat_cap
        df_bat['current_capacity_Wh'][i+1] = df_bat['current_capacity_Wh'][i]
       
    elif df_bat['current_capacity_Wh'][i]<cut_off*bat_cap:
        df_bat['bat_refill_count'] = 1
        df_bat['current_capacity_Wh'][i] = bat_cap
        df_bat['current_capacity_Wh'][i+1] = df_bat['current_capacity_Wh'][i]
    else: 
        df_bat['current_capacity_Wh'][i+1] = df_bat['current_capacity_Wh'][i]
    
    if df_bat['live_cap'][i]>=bat_cap:
        df_bat['full_count'][i] = 1
        df_bat['live_cap'][i] = bat_cap
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]
    
    elif df_bat['live_cap'][i]<=0:
        df_bat['live_cap'][i] = 0
        df_bat['empty_count'][i] = 1
        
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]
    elif df_bat['live_cap'][i]< cut_off*bat_cap:
        df_bat['empty_count'][i] = 1
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]
    else:
        df_bat['live_cap'][i+1] = df_bat['live_cap'][i]


df = df_bat.resample('D').sum()
df['full_count'] = np.sign(df['full_count'])
df['empty_count'] = np.sign(df['empty_count'])
df['bat_refill_count'] = np.sign(df['bat_refill_count'])

df_month_tot = df[['full_count','empty_count','bat_refill_count']].resample('M').sum()
df_month_tot['full %'] = 100*df_month_tot['full_count']/df_month_tot.index.day
df_month_tot['empty %'] = 100*df_month_tot['empty_count']/df_month_tot.index.day

df_month_avg = df_month_tot.groupby(df_month_tot.index.month).mean()
df_month_avg['Month']=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df_month_avg.set_index('Month', inplace=True)
df_month_avg[['empty %','full %']].plot.bar()
plt.ylabel('Percentage days empty/full (Avg over years)')
plt.show()


df_month_avg['bat_refill_count'].plot.bar()
plt.ylabel('Mean days requiring refill')
plt.show()


# df_bat['storage'] = 100*df_bat['current_capacity_Wh']/bat_cap  

# df_plot_bat = pd.DataFrame({
#     'Battery_Capacity': df_bat['storage'],
# })

# df_plot_bat = df_plot_bat.reset_index()
# df_plot_bat['time(UTC)'] = pd.to_datetime(df_plot_bat['time(UTC)'])

# monthly_output_bat = df_plot_bat.groupby(df_plot_bat['time(UTC)'].dt.month)['Battery_Capacity'].min().reset_index()

# # summing hourly power (W) gives (W h)
# monthly_output_bat.plot.bar()
# plt.ylabel('Energy [Wh]')
