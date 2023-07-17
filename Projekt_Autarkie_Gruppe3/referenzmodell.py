
"""
Created on Fri May 12 17:15:53 2023

@author: User

name:
   
    
overview:
   
    
"""
import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython import display
import seaborn as sns
import sys
#import gurobipy

print(sys.version)



#csv-Datei importieren
csv_datei = "DennisDDDeDe.csv"
df_data = pd.read_csv(csv_datei, sep=';', decimal = ',')
df_data
# Verbrauch = elektrische Last

#Spaltennamen vergeben 
pv_ertrag = df_data['PV-Ertrag']
elektrische_last = df_data['Verbrauch '] 
thermische_last = df_data['Thermische Last ']
netzeinspeisung = df_data['Netzeinspeisung ']

#Annahmen für das Ref-Netzwerke

#Marginale Kosten
strompreis_bezug = 0.40                             #€/kWh
strompreis_einspeisung = -0.08                      #€/kWh

#Kapitalkosten pro Jahr pro kW
kapital_kosten_batteriespeicher = 892/12.5          #892€/kWh auf 12.5 Jahre
kapital_kosten_pufferspeicher = 53.32/20            #Preis(1965€)/36,85kWh (800l) 
kapital_kosten_wp = 80                              #€/kW
kapital_kosten_pv = 100                             #€/kW #10kWp Anlage ink. WR für 20000€ auf 20 Jahre

#Wirkungsgrade der Komponenten
wirkungsgrad_batteriespeicher_laden = 0.88        
wirkungsgrad_batteriespeicher_entladen = 0.88       #Wirkungsgrad von wurzel(77%)
selbstentlade_verluste_bs = 0.07
selbstentlade_verluste_ps = 0.08
wirkungsgrad_wp = 3.5                               #aktuell den COP als konstant angenommen

# Refrenznetzwerk = Ref-Netzwerk

# define reference Network
ref_network = pypsa.Network()
ref_network.set_snapshots(df_data.index)

#Busses
ref_network.add('Bus', name = 'strom', carrier='AC')
ref_network.add('Bus', name = 'waerme')#, carrier='heat') #dafür muss man einen carrier definieren
ref_network.add('Bus',name= 'batterie', carrier='AC')
ref_network.add('Bus', name ='ueberschuss', carrier= 'AC')
#Generatoren
ref_network.add('Generator', name = 'pv_generator', bus = 'ueberschuss',capital_cost = kapital_kosten_pv, p_nom_extendable = True, p_nom_max = 10 ,p_max_pu= pv_ertrag/10, carrier = 'AC')
ref_network.add('Generator', name = 'netzbezug' , bus= 'strom', p_nom = elektrische_last.max(), marginal_cost = strompreis_bezug, carrier = 'AC')
ref_network.add('Generator', name = 'netzeinspeisung' , bus= 'ueberschuss', p_nom_extendable = True, 
            marginal_cost = strompreis_einspeisung,sign = -1, carrier = 'AC')

#Lasten
ref_network.add('Load', name= 'thermische_last', bus='waerme',p_set = thermische_last)
ref_network.add('Load', name= 'elektrische_last', bus='strom',p_set = elektrische_last)

#Speicher
ref_network.add('Store' , name = 'batteriespeicher', bus= 'batterie', e_nom_extendable = True,
            capital_cost = kapital_kosten_batteriespeicher , standing_loss = selbstentlade_verluste_bs)
ref_network.add('Store', name= 'pufferspeicher', bus= 'waerme', e_nom_extendable = True, capital_cost= kapital_kosten_pufferspeicher, 
                standing_loss= selbstentlade_verluste_ps)

#Links
ref_network.add('Link', name = 'Bs_entladen', bus0= 'batterie', bus1='strom',p_nom_extendable = True,
            efficiency= wirkungsgrad_batteriespeicher_entladen)
ref_network.add('Link', name = 'Bs_laden', bus0= 'strom', bus1='batterie' ,p_nom_extendable = True, 
            efficiency= wirkungsgrad_batteriespeicher_laden)
ref_network.add ('Link',name= 'eigenverbrauch', bus0= 'ueberschuss', bus1= 'strom', p_nom_extendable = True)
ref_network.add('Link', name= 'waermepumpe', bus0= 'strom', bus1='waerme',p_nom_extendable = True, p_nom_min = 12.5,
            efficiency= wirkungsgrad_wp, capital_cost= kapital_kosten_wp) #p_nom_min im Referenzmodell laut Berechnungen 12.5

ref_network.optimize(solver_name = 'gurobi', threads = 1, method = 1)
#ref_network.lopf(pyomo=False, solver_name='gurobi')  #Effizienter laufen soll
ref_network.generators_t.p.plot()
ref_network.links_t.p0.plot()
ref_network.loads_t.p.plot()
generators = ref_network.generators
print(ref_network.stores.e_nom_opt)