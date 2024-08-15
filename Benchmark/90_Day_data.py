#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 11:58:39 2024
@author: joshua
"""
import pandas as pd
import pvlib
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simps
def df_diff(df1, df2):
    # Reset indices to make them columns for the merge operation
    df1 = df_hourly.reset_index()
    df2 = df.reset_index()

    # Merging with an indicator
    df_diff = df1.merge(df2, on=list(df1.columns), how='outer', indicator=True)
    # Filtering the differences
    df_diff = df_diff[df_diff['_merge'] != 'both']
    # Dropping the merge indicator column
    df_diff = df_diff.drop(columns=['_merge'])
    
    return df_diff

def cum_simps(df, x_title, y_title, time_index=False):
    
    # Initialize a list to store cumulative integrals
    cumulative_integrals = []
    
    if time_index==True:
        # Convert datetime index to numeric (total seconds from start)
        df['x_numeric'] = (df.index - df.index[0]).total_seconds()/3600
        x_title = 'x_numeric'
    
    # Calculate cumulative integral up to each element
    for i in range(1, len(df) + 1):
        x_subset = df[x_title][:i].values
        y_subset = df[y_title][:i].values
        if len(x_subset) > 1:
            integral = simps(y_subset, x_subset)
        else:
            integral = 0  # If there is only one point, integral is 0
        cumulative_integrals.append(integral)
    return cumulative_integrals

def readin_df(filename):
    full_df = pd.read_csv(filename, header=1)
    full_df['PV power'][0] = 'W'

    df = full_df.copy()

    ## Setting timestamp index
    df['Europe/London (+01:00)'] = pd.to_datetime(df['Europe/London (+01:00)']) #make timestamp datetime type
    df.set_index(df.columns[0], inplace=True) #make timestamp index
    

    ## Identify columns where the second row contains NaN
    columns_to_drop = df.columns[df.iloc[0].isna()]
    df = df.drop(columns=columns_to_drop) # Drop those columns

    ## Changing titles of columns to include units
    second_row = df.iloc[0] # Extract the first row
    new_headers = [f"{col} {second_row[i]}" for i, col in enumerate(df.columns)] # Concatenate second row values with the current column headers
    df.columns = new_headers # Set the new headers
    df = df.iloc[1:]# Drop the row

    #Remove forecast rows
    df = df.loc[:, ~df.columns.str.contains('forecast', case=False)]
    df = df.loc[:, ~df.columns.str.contains('accuracy', case=False)]
    df = df.astype(float)
    df.index=df.index.tz_localize('UTC')
    return df

## Read in file
df1 = readin_df('90_day_test_tower/sheet_2.csv')
df2 = readin_df('90_day_test_tower/sheet_1.csv')

df = pd.concat([df1, df2], axis = 0)
df = df.sort_index()

## On the hour df
df_hourly = df[df.index.minute == 0]
df_hourly = df_hourly[df_hourly.index.second == 0]
df_hourly = df_hourly.dropna(axis = 1, how = 'all')

df_off_hour = df[df.index.minute != 0]
df_off_hour = df_off_hour[df_off_hour.index.second != 0]
df_off_hour = df_off_hour.dropna(axis = 1, how = 'all')

## Off the hour df
# df_off_hour = df_diff(df_hourly, df)
# df_off_hour['Europe/London (+01:00)'] = pd.to_datetime(df_off_hour['Europe/London (+01:00)']) #make timestamp datetime type
# df_off_hour.set_index(df_off_hour.columns[0], inplace=True) #make timestamp index

# df_off_hour = df_off_hour.dropna(axis=1, how='all')
df_PV = df[['Current A', 'PV voltage V', 'PV power W', 'PV - DC-coupled W']]

df_off_hour['dt s'] = df_off_hour.index.to_series().diff().dt.total_seconds() / 3600

def avg_nn_col(df,col):
    # Shift column 'B' to get the previous element
    next_el = df[col].shift(-1)

    # Calculate the average of the current and previous element in column 'B'
    avg = (df[col] + next_el) / 2
    return avg


# Calculate the average of the current and previous element in column 'B'
P_PV_avg = avg_nn_col(df_off_hour, 'PV power W')
P_PVDC_avg = avg_nn_col(df_off_hour, 'PV - DC-coupled W')
P_sysDC_avg = avg_nn_col(df_off_hour, 'DC System W')


# Multiply column 'A' by the calculated average and create a new column
df_off_hour['Calc_yield PV kWh'] = ((df_off_hour['dt s'].shift(-1) * P_PV_avg)/1000).round(2)
df_off_hour['Calc PV - DC-coupled kWh'] = ((df_off_hour['dt s'].shift(-1) * P_PVDC_avg)/1000).round(2)
df_off_hour['Calc DC System PV kWh'] = ((df_off_hour['dt s'].shift(-1) * P_sysDC_avg)/1000).round(2)

#df_off_hour['Calc_yield simps'] = cum_simps(df_off_hour, 'Europe/London (+01:00)', 'PV power W', time_index=True)

df_off_hour['Calc_daily_yield kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc_yield PV kWh'].cumsum()
df_off_hour['Calc_daily PV - DC-coupled kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc PV - DC-coupled kWh'].cumsum()
df_off_hour['Calc_daily DC System PV kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc DC System PV kWh'].cumsum()


df_day_off_hour = {}
df_day_off_hour = pd.DataFrame()
df_day_off_hour['PV power W'] = df_off_hour['PV power W'].groupby(df_off_hour.index.date).sum()
df_day_off_hour['Yield kWh'] = df_off_hour['Yield today kWh'].groupby(df_off_hour.index.date).max()
df_day_off_hour['Calc_daily_yield kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc_daily_yield kWh'].max()
df_day_off_hour['Calc_daily PV-DC kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc_daily PV - DC-coupled kWh'].max()
df_day_off_hour['Calc_daily DC-sys kWh'] = df_off_hour.groupby(df_off_hour.index.date)['Calc_daily DC System PV kWh'].max()




#df_solcast = pd.read_csv('90_day_test_tower/SolcastAPI_90day.csv')
#df_solcast['period_end'] = df_solcast['period_end'].str.replace('T', ' ')
#df_solcast['period_end']=pd.to_datetime(df_solcast['period_end'])
#df_solcast.set_index(df_solcast.columns[3], inplace=True)
#df_solcast['Solar Irradiance W/m²'] = df_solcast['ghi']*0.8 + df_solcast['dni']*0.2

from solcast import historic
loc = pvlib.location.Location(latitude=53.43,
longitude=-2.11)
resp = historic.radiation_and_weather(
    latitude=53.43,
    longitude=-2.11,
    array_type='fixed',
    tilt=35,
    output_parameters=["air_temp","ghi","dhi","dni","wind_speed_10m"],
    start="2024-05-08 00:00:00-10:00",
    end="2024-08-06 00:00:00-10:00",
    period="PT60M",
    api_key='WTcqkIYVyfzgZMC74Rxww5DpCEtb8L3P'
)


df_solcast = resp.to_pandas()
solpos = loc.get_solarposition(df_solcast.index)

total_irrad = pvlib.irradiance.get_total_irradiance(28, 180,
                                   solpos.apparent_zenith, solpos.azimuth,
                                   dni=df_solcast['dni'], ghi=df_solcast['ghi'], dhi=df_solcast['dhi'])

df_solcast['poa_global'] = total_irrad.poa_global

#temp model
df_solcast['temp_pv'] = pvlib.temperature.pvsyst_cell(df_solcast['poa_global'], temp_air = df_solcast['air_temp'], u_c=29, u_v=0)
#temp as air temp
#df_solcast['temp_pv'] = df_solcast['air_temp']


P_nom = 215

df_solcast['array_power'] = pvlib.pvsystem.pvwatts_dc(df_solcast['poa_global'], temp_cell = df_solcast['temp_pv'],pdc0=P_nom, gamma_pdc=-0.0045, temp_ref = 25.0)
df_day_off_hour['solcast_PVlib_estimated daily Yield kWh'] = df_solcast['array_power'].groupby(df_solcast.index.date).sum()/1000
df_day_off_hour['Diff_factor'] = df_day_off_hour['Yield kWh']/df_day_off_hour['solcast_PVlib_estimated daily Yield kWh']


#df_hourly.index=df_hourly.index.tz_localize('UTC')
## PVlib calculation
array_power = pvlib.pvsystem.pvwatts_dc(df_hourly['Solar Irradiance W/m²'], temp_cell = df_solcast['temp_pv'], pdc0=P_nom, gamma_pdc=-0.0045, temp_ref = 25.0)
array_power = pd.DataFrame(array_power)
df_day_off_hour['PVlib_estimated daily Yield kWh'] = array_power[0].groupby(array_power.index.date).sum()/1000


plt.hist(df_day_off_hour['Diff_factor'],bins=50)
plt.show()

plt.plot(df_day_off_hour.index[1:-2],df_day_off_hour['Yield kWh'][1:-2])
plt.plot(df_day_off_hour.index[1:-2],df_day_off_hour['solcast_PVlib_estimated daily Yield kWh'][1:-2])
plt.plot(df_day_off_hour.index[1:-2],df_day_off_hour['PVlib_estimated daily Yield kWh'][1:-2])
plt.xlabel('Date')
plt.ylabel('Yield kWh')
plt.legend(['Actual', 'Model solcast', 'Model measured Irr'])
plt.show()


plt.plot(df_day_off_hour.index,df_day_off_hour['solcast_PVlib_estimated daily Yield kWh']/df_day_off_hour['Yield kWh'])
plt.show()

print(df_day_off_hour['Diff_factor'].mean(), df_day_off_hour['Diff_factor'].std())


