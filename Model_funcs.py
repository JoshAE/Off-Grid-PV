#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 10:11:47 2024

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

def battery(array_power, bat_cap, cam_consump):
    
    #Battery data frame
    df_bat = {}
    
    df_bat = pd.DataFrame(index=array_power.index)
    df_bat['consumption'] = cam_consump
    df_bat['live_cap'] = bat_cap
    df_bat['Production'] = array_power['power']
    
    df_bat['net_change_per_hour'] = df_bat['Production'] - df_bat['consumption']
    df_bat['Energy_excess'] = 0 
    df_bat['full_count'] = 0 
    df_bat['empty_count'] = 0 
    
    return df_bat


def PV_data(latitude,longitude, surface_tilt, surface_azimuth, temp_coef = np.array([-0.0045, -0.0045]), power = np.array([215, 215]), start_year=2005, end_year=2016, FAKE=False):
    n = len(surface_tilt)
    DF = [None]*n
    cell_temp = [None]*n
    array_power = [None]*n
    for i in range(len(surface_tilt)):
        DF[i], _, _ = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=start_year, end=end_year, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt[i],surface_azimuth=surface_azimuth[i], pvcalculation=True,peakpower=power[i]/1000)
        cell_temp[i] = pvlib.temperature.pvsyst_cell(DF[i]['poa_global'], temp_air = DF[i]['temp_air'], wind_speed=DF[i]['wind_speed'], u_c=29, u_v=0)
        array_power[i] = pvlib.pvsystem.pvwatts_dc(DF[i]['P'], temp_cell=cell_temp[i], pdc0=power[i], gamma_pdc=temp_coef[i], temp_ref = 25.0)
    tot_power = sum(array_power)
    
    df_p = pd.DataFrame()
    df_p['power'] = tot_power
    
    # Create fake years
    if FAKE == True:
        #Create fake years
        df_p = pd.concat([df_p, shuffle_solar_data(df_p)])
    
    
    return df_p

def PV_dynamics(df_bat, cam_consump, bat_cap, setup_date = '01-01', setup_time='00:11:00', cut_off=0.4, REFILL=True, DAY = False):
    ## Select start date when tower is placed
    setup_date = '2006-' + setup_date + ' ' + setup_time + ' UTC' 
    #Reorders data frame for start date
    timestamp_to_reorder = pd.to_datetime(setup_date)

    # Find the index of the timestamp
    df_part1 = df_bat.loc[:timestamp_to_reorder]
    df_part2 = df_bat.loc[timestamp_to_reorder:].iloc[1:]

    # Concatenate with the part from the timestamp first
    df_bat = pd.concat([df_part2, df_part1])
    
    if DAY == True:
        df_bat = df_bat.resample('D').sum()
    else:
        pass
    
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
    
    
    df_bat.loc[df_bat['live_cap'] <= bat_cap*cut_off,'empty_count'] = 1
    df_bat.loc[df_bat['live_cap'] == bat_cap,'full_count'] = 1
    
    # day totals
    df = df_bat.resample('D').sum()
    
    # empty and full battery count
    df['full_count'] = np.sign(df['full_count'])
    df['empty_count'] = np.sign(df['empty_count'])
    
    return df
    
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

## Input parameters

# location
latitude = 52.943
longitude = -1.133

# PV pannels
surface_tilt = np.array([35,35])
surface_azimuth = np.array([0,180])
power = np.array([215, 215]) #Nominal power 215W per pannel
temp_coef = np.array([-0.0045, -0.0045])

# battery
bat_cap = 125*4*12 #battery capacity, 125Ah x 4 batteries x 12V
cut_off = 0.4 #fractional cutoff for lead-acid battery 40%
cam_consump = 500/24 #Daily consumption per hour 600Wh for the day

# get PV df
array_power = PV_data(latitude, longitude, surface_tilt, surface_azimuth, FAKE=True)


#array_power_ext = pd.concat([shuffle_solar_data(array_power), array_power])

# get battery df
df_bat = battery(array_power, bat_cap, cam_consump)

# battery dynamics
df = PV_dynamics(df_bat, cam_consump, bat_cap, DAY=True)


# monthly totals
df_month_tot = df[['full_count','empty_count','Production','Energy_excess']].resample('M').sum()
df_month_tot['full %'] = 100*df_month_tot['full_count']/df_month_tot.index.day
df_month_tot['empty %'] = 100*df_month_tot['empty_count']/df_month_tot.index.day
df_month_tot['Production'] = df_month_tot['Production']/df_month_tot.index.day
df_month_tot['Energy_excess'] = df_month_tot['Energy_excess']/df_month_tot.index.day

# monthly averages over years 
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

