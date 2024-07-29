## Off-Grid-PV
Modelling Off Grid PV systems for camera towers. The aim is to model the battery dynamics from historical data so that it is possible to predict how often batteries must be replaced.

# Basic model PVGIS daily
This simple model uses the historic data from the PVGIS to determine how the battery charge state changes through the months of a calander year from set-up.
The parameters that are free for the user to change are:
1. Location: Entered as longitude and lattitude.
2. Surface tilt: Tilt from horzontal of the pannels, this can be enetered as an array with elements corresponding to the number of pannels on the tower
3. Surface azimuth: Azimuth angle from south for each pannel.
4. Nominal power: The nominal power of the pannels (assumed all are the same)
5. Temperature coefficient: The temperature coefficient of the pannels (assumed all are the same)

The battery parameters that can be changed are:
1. Battery capacity: the default set-up is for 4 lead-acid batteries, 4 $\times$12V$\times$125Ah=6000Wh.
2. Consumption: Camera tower energy consumption, assumed to be 600Wh per day.
3. Battery cut-off: The decimal value at which the battery is deemed to be cut-off.

