from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
#import ruptures as rpt
import matplotlib.pyplot as plt
import numpy as np

# Connecting to mongo database
dest = "mongodb://schappus:unicornsSUM22@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db["snapshot 1"]
asteroid_data = db['asteroids_all']

# local vars
stdev_mult = 2
maxIn = 10
divider = ("_" * 120)
ast_ct = 0

# get all asteroid names
asteroids = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))

# attributes we look at 
wanted_attr = ["magpsf", "elong", "rb", "H"]
numFeatures = len(wanted_attr)

#Sigma Matrix
sigmaMatrix = np.zeros([maxIn, numFeatures + 2])

# TOP 4 ATTR:
# magpsf: magnitude
# elong: elong val > 1 means oblong object, if this changes it's interesting
# rb (real-bogus): 
# H: another measurement of brightness

# ALL ATTRIBUTES
# "phaseangle" "diffmaglim", "magpsf", "sigmapsf", "chipsf", "magap", "sigmagap", "magapbig", "sigmagapbig", "distnr", "magnr", "fwhm", "elong", "rb", "ssdistnr", "ssmagnr", "G", "H", "ltc" 

# Loop through our collection of names 
while ( ast_ct < maxIn and ast_ct < len(asteroids)):
    # grab asteroid name 
    name = asteroids["ssnamenr"][ast_ct]
    
    # reset attributes looked at
    attr_ct = 0
    rowSum = absRowSum = 0
    
    # loop through wanted attributes
    while ( attr_ct < len(wanted_attr) ):
        
        # sort specific asteroid data by Julian Date
        asteroid = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(name)}).sort("jd"))
        
        # grab feature data and calculate mean and standard deviation
        feature = wanted_attr[attr_ct]
        obj_stdev = stat.stdev(asteroid[feature])
        obj_mean = stat.mean(asteroid[feature])
        
        # sort specific asteroid data by Julian Date
        dataSortedByFeature = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(name)}).sort(feature))
        
        # calculate min, max, and ranges for highSigma and lowSigma values
        minIndex = 0
        maxIndex = len(dataSortedByFeature) - 1
        
        minDataVal = dataSortedByFeature[feature][minIndex]
        maxDataVal = dataSortedByFeature[feature][maxIndex]
        
        upperRange = maxDataVal - obj_mean
        lowerRange = obj_mean - minDataVal
        
        highSigma = upperRange / obj_stdev
        lowSigma = lowerRange / obj_stdev    
        
        # add data to sigmaMatrix
        if (highSigma > lowSigma):
            sigmaMatrix[ast_ct][attr_ct] = highSigma
            rowSum += highSigma
            absRowSum += highSigma
        else:
            sigmaMatrix[ast_ct][attr_ct] = -lowSigma
            rowSum += -lowSigma
            absRowSum += lowSigma
           
        attr_ct += 1
        
    # append row sums to sigmaMatrix
    sigmaMatrix[ast_ct][attr_ct] = rowSum
    sigmaMatrix[ast_ct][attr_ct + 1] = absRowSum
        
    ast_ct += 1
    
print(sigmaMatrix)  

nameArray = np.array( asteroids['ssnamenr'])[: ast_ct]

dataset = pd.DataFrame({'Name': nameArray, 'magpfs': sigmaMatrix[:, 0], 'elong': sigmaMatrix[:, 1], 'rb': sigmaMatrix[:, 2], 'H': sigmaMatrix[:, 3], 'Row Sum': sigmaMatrix[:, 4], 'Abs Row Sum': sigmaMatrix[:, 5]})

