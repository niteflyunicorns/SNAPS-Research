from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import ruptures as rpt
import matplotlib.pyplot as plt
# import numpy as np

# Connecting to mongo database
dest = "mongodb://schappus:unicornsSUM22monsoon@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db["snapshot 1"]
asteroid_data = db['asteroids']

# local vars
stdev_mult = 2
maxIn = 50
divider = ("_" * 120)
ast_ct = 0

# get all name
asteroids = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))

# attributes we look at 
wanted_attr = ["magpsf"]

# TOP 4 ATTR:
# magpsf: magnitude
# elong: elong val > 1 means oblong object, if this changes it's interesting
# rb (real-bogus): 
# H: another measurement of brightness

# ALL ATTRIBUTES
# "phaseangle" "diffmaglim", "magpsf", "sigmapsf", "chipsf", "magap", "sigmagap", "magapbig", "sigmagapbig", "distnr", "magnr", "fwhm", "elong", "rb", "ssdistnr", "ssmagnr", "G", "H", "ltc" 

# Loop through our collection of names 
while ( ast_ct < maxIn and ast_ct < len(asteroids)):
    # grab name 
    name = asteroids["ssnamenr"][ast_ct]
    
    # reset attributes looked at
    attr_ct = 0
    
    # loop through wanted attributes
    while ( attr_ct < len(wanted_attr) ):
        
        # sort specific asteroid data by Julian Date
        asteroid = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(name)}).sort("jd"))
        
        # grab feature data and calculate necessary math
        feature = wanted_attr[attr_ct]
        obj_stdev = stat.stdev(asteroid[feature])
        obj_mean = stat.mean(asteroid[feature])

        # outlier counting
        dataIndex = 0
        outlierCount = 0
        outlierFlag = obj_stdev * int(stdev_mult)
        outlierList = list()
         
        # outlier check
        while (dataIndex < len(asteroid[feature])):
            if ( abs(obj_mean - asteroid[feature][dataIndex]) ) > ( outlierFlag ):
                outlierCount += 1
                outlierList.append(asteroid["jd"][dataIndex])
                
            dataIndex += 1
        
        # display data
        print("Asteroid: " + str(name))
        print("Mean: " + str(obj_mean))
        print("Std Dev: " + str(obj_stdev))
        print("Low Cutoff: " + str(obj_mean - outlierFlag))
        print("High Cutoff: " + str(obj_mean + outlierFlag))
        print("Num Outliers: " + str(outlierCount))
        print("Outliers: " + str(outlierList))
        
        # plot data
        plt.scatter(asteroid["jd"], asteroid[feature])
        plt.xlabel("Julian Date")
        plt.ylabel(feature)
        plt.show()
        print(divider)
        
        attr_ct += 1
    
    
    ast_ct += 1
    
