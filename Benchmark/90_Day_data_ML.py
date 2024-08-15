#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 16:21:04 2024

@author: joshua
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
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

from solcast import historic
import pvlib
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


# Load your data
data = pd.DataFrame(df_off_hour['PV power W'])#.resample('H').mean())
data = data.dropna()
df_solcast_reindex = df_solcast.reindex(data.index, method='nearest', limit=len(data))
data['irradiance_0'] = df_solcast_reindex['poa_global']
data['air_temperature_0'] = df_solcast_reindex['air_temp']

data['∆t_0'] = data.index.to_series().diff().dt.total_seconds() / 3600

for i in range(3):
    data[['∆t_'+str(i+1),'air_temperature_'+str(i+1), 'irradiance_'+str(i+1)]]= data[['∆t_0','air_temperature_0', 'irradiance_0']].shift((i+1))

data['tilt_angle'] = 28
data['battery_coefficient_0'] = -0.0045 
data['nominal_power'] = 430
data = data.dropna()

# Define features and target variable
X = data.drop(columns=['PV power W'])
y = data['PV power W']

split_point = int(len(data) * 0.9)
X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]

#Random forest model
# Initialize the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
# Train the model
model.fit(X_train, y_train)

import xgboost 
from xgboost import XGBRegressor

modelXGBR = XGBRegressor(n_estimators=100, learning_rate=0.05)
modelXGBR.fit(X_train, y_train)
# Train the model
modelXGBR.fit(X_train, y_train)

#X_test = X
#y_test = y

# Make predictions
y_pred_RF = model.predict(X_test)
y_pred_XGBR =  modelXGBR.predict(X_test)

# Evaluate the model
mseRF = mean_squared_error(y_test, y_pred_RF)
rmseRF = np.sqrt(mseRF)

mseXGBR = mean_squared_error(y_test, y_pred_XGBR)
rmseXGBR = np.sqrt(mseXGBR)


import numpy as np
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))

# Scatter plot for actual test data
plt.plot(y_test.index, y_test, color='green', label='Actual Data')

# Line plot for predicted data
plt.plot(y_test.index, y_pred_RF, color='red', label='Predicted Data RF')
plt.plot(y_test.index, y_pred_XGBR, color='blue', label='Predicted Data XGBR')

# Labels and title
plt.xlabel('Feature (e.g., Time)')
plt.ylabel('Target (e.g., Power Output)')
plt.title('Actual vs Predicted Data')
plt.legend()
# Show the plot
plt.show()

results = pd.DataFrame()


results.index = data.index
results['PV power W'] = data['PV power W']
results['Forecast PV power (RF)'] = model.predict(X)
results['Forecast PV power (XGBR)'] =  modelXGBR.predict(X)


















