#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 11:17:57 2024

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
from Model_funcs import PV_data,battery,PV_dynamics
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

# get battery df
df_bat = battery(array_power, bat_cap, cam_consump)

# battery dynamics
df_bat_dyn = PV_dynamics(df_bat, cam_consump, bat_cap)

# day totals
df = df_bat_dyn.resample('D').sum()

# empty and full battery count
df['full_count'] = np.sign(df['full_count'])
df['empty_count'] = np.sign(df['empty_count'])

# monthly totals
df_month_tot = df[['full_count','empty_count','Production','Energy_excess']].resample('M').sum()
df_month_tot['full %'] = 100*df_month_tot['full_count']/df_month_tot.index.day
df_month_tot['empty %'] = 100*df_month_tot['empty_count']/df_month_tot.index.day
df_month_tot['Production'] = df_month_tot['Production']/df_month_tot.index.day
df_month_tot['Energy_excess'] = df_month_tot['Energy_excess']/df_month_tot.index.day

# monthly averages over years 
df_month_avg = df_month_tot.groupby(df_month_tot.index.month).median()
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