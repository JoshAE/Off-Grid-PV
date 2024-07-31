#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 30 10:42:35 2024

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

class PVGIS_model:
    def __init__(self, latitude, longitude, surface_tilt, surface_azimuth, ):
        

    #Get solar data
    df_PVGIS_p1, _, _ = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2005, end=2015, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt[0],surface_azimuth=surface_azimuth[0])
    df_PVGIS_p2, _, _ = pvlib.iotools.get_pvgis_hourly(latitude, longitude, start=2005, end=2015, map_variables=True, components=False, usehorizon=True, userhorizon=None, raddatabase='PVGIS-SARAH', surface_tilt=surface_tilt[1],surface_azimuth=surface_azimuth[1])

    #Determine solar cell temp for solar_data
    cell_temp_p1 = pvlib.temperature.pvsyst_cell(df_PVGIS_p1['poa_global'], temp_air = df_PVGIS_p1['temp_air'], wind_speed=df_PVGIS_p1['wind_speed'], u_c=29, u_v=0)
    cell_temp_p2 = pvlib.temperature.pvsyst_cell(df_PVGIS_p2['poa_global'], temp_air = df_PVGIS_p2['temp_air'], wind_speed=df_PVGIS_p2['wind_speed'], u_c=29, u_v=0)

    #Solar cell specification
    temp_coef = -0.45/100 #Temperature coefficient %/C
    power = 215 #Nominal power 215W per pannel

    #Determine dc power output from PV system model
    array_power_p1 = pvlib.pvsystem.pvwatts_dc(df_PVGIS_p1['poa_global'], temp_cell=cell_temp_p1, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)
    array_power_p2 = pvlib.pvsystem.pvwatts_dc(df_PVGIS_p2['poa_global'], temp_cell=cell_temp_p2, pdc0=power, gamma_pdc=temp_coef, temp_ref = 25.0)

    