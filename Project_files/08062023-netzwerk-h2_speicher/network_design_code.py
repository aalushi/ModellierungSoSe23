
"""
Created on Fri May 12 17:15:53 2023

@author: User

name:
    dataHandler
    
overview:
    Handles the import and export of data 
    used by simulation of power-to-h2
    
"""
import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython import display
import seaborn as sns

# load in energy profiles

electrical_load = pd.read_csv('household_2_1h.Electricity.csv', sep = ';', decimal = ',')['Sum [kWh]'] # 1h resolution, 2-Personen Load Profile Generator
heat_load = pd.read_csv('heat_load.csv', sep = ';', decimal = ',') 
#hot_water_consum.plot()
#Annahme: 40L Warmwasser mit 45°C pro Person pro Tag und JAZ 3.0 - circa 406 kWh/a für 2 Personen (energie-experten.org) // 2.2 kWh pro 40 L

#heat_load = hot_water_consum * (2.2/40) #kWh
#heat_load[4000:4100].plot()
#plt.xlabel('Zeit')
#plt.ylabel('Heizleistung für Warmwasser [kWh]')

#print(heat_load.sum())

pv_p = pd.read_csv('Wesseling_PV_50.8203_6.9721.csv', skiprows = 3)['electricity']   # 1 year in Wesseling for 10 kWp

#pv_p.plot()

heat_load_new = heat_load#.transpose()
heat_load_new = heat_load_new.stack().reset_index().rename(columns={0:'value'})
heat_load_new[isinstance(heat_load_new['value'], float)]
#print(heat_load_new[0:364])

#heat_load_new.rename(index = {'Date': 'Uhrzeit'})
#sns.heatmap(heat_load)

##### Parameters: #####

electricity_rate = 0.5 # €/kWh
pv_infeed = 0.082 # €/kWh

lifespan_pv = 20 #years
specific_heat_power = 0.06 # kW/m² Annahme
living_space = 157 #m²
p_heat_pump = specific_heat_power * living_space

# define design parameters in dictionarys for pv, grid, electrolysis, fuellcell, heatpump, storages 
pv_params = {
    'p_nom_pv': 10,    # kWp
    'p_max_pu_pv': pv_infeed,
    'capital_cost_pv': 14000/10,
    'marginal_cost_pv': 0.02 * lifespan_pv
}

fuellcell_params = {
    'p_nom_fuelcell': 1.5, #kW_el Brennstoffzellenleistung picea
    'electrical_efficiency_fuelcell': 0.8,
    'thermal_efficiency_fuelcell': 0.2,
   # 'capital_cost_fuelcell': 1000,
   # 'marginal_cost_fuelcell': 40
}

electrolysis_params = {
    'p_nom_electrolysis': 2.3, #kW_el Wasserstofferzeugungsleistung picea
    'efficiency_electrolysis': 0.8,
 #   'capital_cost_electrolysis': 12000,
  #  'marginal_cost_electrolysis': 100
}

heatpump_params = {
    'p_nom_heatpump': p_heat_pump,
    'efficiency_heatpump': 3,
    #'p_max_pu_heatpump': *hier Kennlinie hinterlegen*
    'capital_cost_heatpump': 1000,
    'marginal_cost_heatpump': 40
}

battery_params = { # battery integrated in picea system
    'e_nom_battery': 20, #kWh picea system
    #'e_min_pu_battery': 0.2,
    #'e_max_pu_battery': 1.0,
    'capital_cost_battery': 5000,
    'marginal_cost_battery': 30,
    'standing_loss_battery': 0.01
}

heatstore_params = {
    'e_nom_heat_storage': 300, #kWh
    'e_min_pu_heat_storage': 0.6,
    'e_max_pu_heat_storage': 1.0,
    'volume': 300, #Litre
    'capital_cost_heat_storage': 750,
    'marginal_cost_heat_storage': 600,
    'standing_loss_heat_storage': 0.05
}
    
hydrogenstore_params = {
    'e_nom_heat_hydrogen': 300, #kWh_el - picea, auf 1500 kWh_el erweiterbar
 #   'e_min_pu_hydrogen': 0.6,
  #  'e_max_pu_hydrogen': 1.0,
    'capital_cost_hydrogen': 120000, #€ picea system
    'marginal_cost_hydrogen': 499.8,
    'standing_loss_hydrogen': 0.001
}

#### define reference network####
# carrier: 'AC / DC' for electrical or 'heat / gas' for energy carrier (Bus, Link, Generator, Load)

ref_network = pypsa.Network()
ref_network.set_snapshots(range(8760))

# pv - electrical subnetwork

ref_network.add('Bus', name = 'electricity_bus')
ref_network.add('Bus', name='battery_bus')

ref_network.add('Load', name='electrical_load', bus='electricity_bus', p_set = electrical_load)    # electrical load for house

ref_network.add('Generator', name='PV', bus='electricity_bus',
                p_nom = pv_params['p_nom_pv'], p_max_pu = pv_params['p_max_pu_pv'], p_nom_extendable = True,
                capital_cost = pv_params['capital_cost_pv'], marginal_cost = pv_params['marginal_cost_pv'])
ref_network.add('Generator', name='grid', bus='electricity_bus', marginal_cost = electricity_rate)

ref_network.add('Store', name='battery', bus="battery_bus", e_nom = battery_params['e_nom_battery'],
                e_nom_extendable = True, e_cyclic=True,
                capital_cost = battery_params['capital_cost_battery'], 
                marginal_cost = battery_params['marginal_cost_battery'])   # electrical storage

ref_network.add('Link', name='house_battery_charge', bus0='electricity_bus', bus1='battery_bus', efficiency = 0.98)
ref_network.add('Link', name='house_battery_discharge', bus0='battery_bus', bus1='electricity_bus', efficiency = 0.98)


# heat subnetwork

ref_network.add('Bus', name='heat_bus')
ref_network.add('Bus', name='heat_storage_bus')

#ref_network.add('Load', name='heat_load', bus='heat_bus', p_set = heat_load_new[1:364])     # heat load for house
"""
ref_network.add('Store', name='heat_storage', bus='heat_storage_bus', e_nom = heatstore_params['e_nom_heat_storage'],
                e_cyclic=True, capital_cost = heatstore_params['capital_cost_heat_storage'],
               marginal_cost = heatstore_params['marginal_cost_heat_storage'],
                standing_loss = heatstore_params['standing_loss_heat_storage'])    # warm water storage

ref_network.add('Link', name='heat_pump', bus0='electricity_bus', bus1='heat_bus', p_nom = 12.6, p_nom_extendable = True,
                capital_cost = heatpump_params['capital_cost_heatpump'], marginal_cost = electricity_rate)    # heat pump
ref_network.add('Link', name='heat_storage_charge', bus0='heat_bus', bus1='heat_storage_bus')    # charge heat storage
ref_network.add('Link', name='heat_storage_discharge', bus0='heat_storage_bus', bus1='heat_bus') # d
"""