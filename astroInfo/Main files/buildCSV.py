########################################################################################
# How this program works:                                                              #
# The program accepts a number of asteroids to observe and value for where in the data #
# to start. Then, it pulls data for each individual asteroid, and finds the most       #
# outlying point (min or max) and calculates the number of standard deviations away    #
# from the mean that point is. If it is above the mean, the number of sigmas is stored #
# in the matrix. If it is below the mean, the negative number of sigmas is stored in   #
# the matrix. The final columns in the matrix are a row sum (of sigma multipliers) and #
# a row sum of the absolute value of each matrix entry. The program then allows users  #
# to filter the data by features at specific user-given values. Then users can view    #
# histograms of all the sigma data and scatterplots for individual asteroids           #
########################################################################################

# This program is responsible for creating a CSV file for later diagnostic use in totalSearch
# It will iterate through a user specified amount of asteroids and build a sigma matrix based on the 
# outlier math. The seperation of building and searching allows users to search data and not having to
# build over and over. This also allows for the fine tuning of the actual detection math. Currently that
# would be the major challenge to hone in on.

from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import ruptures as rpt
import matplotlib.pyplot as plt
import numpy as np
import random as rand

# Connecting to mongo database and obtain data
dest = "mongodb://schappus:unicornsSUM22monsoon@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db['mag18o8_ss1']
asteroid_data = db['asteroids']

# local vars
offset = 0

# total num of asteroids we want to look at
maxIn = int(input("How many asteroids do you want to look at(-1 if all): "))

# check if we want to look at all
if ( maxIn < 0 ) :
    maxIn = asteroid_data.count()

# where to start in the data
offset = int(input("Where to start in data:(-1 if random):  "))

# randomize the starting position
if ( offset < 0 and maxIn < asteroid_data.count() ):
    offset = rand.randint(0, asteroid_data.count() - maxIn - 1)

# num of asteroids we have looked at 
ast_ct = 0

# divider line for output
divider = ("_" * 120)

#weights for features
weightDict  = {
  "H": 1,
  "mag18omag8": 1,
  "elong": 1,
  "rb": 1
}

# get all asteroid names
asteroidNames = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))

# attributes we look at
wanted_attr = [ "elong", "rb", "H", "mag18omag8" ]
numFeatures = len(wanted_attr)

# list for associated ztf id for observation
antIDS = list()

#Sigma Matrix
sigmaMatrix = np.zeros([maxIn, numFeatures + 2])

# TOP 4 ATTR:
# mag180mag8 : sigma value for difference in 18 aperture vs 8 aperture photos
# elong: elong val > 1 means oblong object, if this changes it's interesting
# rb (real-bogus):
# H: another measurement of brightness

# Loop through our collection of names
while ( ast_ct < maxIn and ast_ct < len(asteroidNames)):
    
    # grab asteroid name
    name = asteroidNames["ssnamenr"][ast_ct + offset]

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

        # grab weight for feature
        attr_weight = weightDict[feature]

        # sort specific asteroid data by feature
        dataSortedByFeature = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(name)}).sort(feature))
        

        # calculate min, max, and ranges for highSigma and lowSigma values
        minIndex = 0
        maxIndex = len(dataSortedByFeature) - 1

        minSumVal = ( dataSortedByFeature[feature][minIndex] +
                    dataSortedByFeature[feature][minIndex + 1] +
                    dataSortedByFeature[feature][minIndex + 2] )

        maxSumVal = ( dataSortedByFeature[feature][maxIndex] +
                    dataSortedByFeature[feature][maxIndex - 1] +
                    dataSortedByFeature[feature][maxIndex - 2] )

        minAvgVal = minSumVal / 3
        maxAvgVal = maxSumVal / 3

        upperRange = maxAvgVal - obj_mean
        lowerRange = obj_mean - minAvgVal

        highSigma = upperRange / obj_stdev
        lowSigma = lowerRange / obj_stdev


        # add data to sigmaMatrix
        if (highSigma > lowSigma):
            sigmaMatrix[ast_ct][attr_ct] = highSigma * attr_weight
            rowSum += highSigma * attr_weight
            absRowSum += highSigma * attr_weight
            
            # keep track of ant id with specific observation
            antIDS.append(dataSortedByFeature['id'][maxIndex])
            
        else:
            sigmaMatrix[ast_ct][attr_ct] = -lowSigma * attr_weight
            rowSum += -lowSigma * attr_weight
            absRowSum += lowSigma * attr_weight
            
            # keep track of ant id with specific observation
            antIDS.append(dataSortedByFeature['id'][minIndex])
            
        
        #update attribute count
        attr_ct += 1

    # append row sums to sigmaMatrix
    sigmaMatrix[ast_ct][attr_ct] = rowSum
    sigmaMatrix[ast_ct][attr_ct + 1] = absRowSum
    
    # update asteroid count
    ast_ct += 1


# Formatting data structures
nameArray = np.array( asteroidNames['ssnamenr'])[offset: offset + ast_ct]
listNames= np.array( antIDS )
idArray = np.reshape(listNames, (maxIn, numFeatures))


# DataFrame creation for main data display
dataset = pd.DataFrame({'Name': nameArray, 'elong': sigmaMatrix[:, 0],'ZTF-ELONG': idArray[:, 0], 'rb': sigmaMatrix[:, 1], 'ZTF-RB': idArray[:, 1], 'H': sigmaMatrix[:, 2], 'ZTF-H': idArray[:, 2], 'mag18omag8': sigmaMatrix[:, 3], 'ZTF-MAG18OMAG8': idArray[:, 3], 'Row Sum': sigmaMatrix[:, 4], 'Abs Row Sum': sigmaMatrix[:, 5]})


# User Testing:
print(dataset)

dataset.to_csv("totalSigmaTable.csv")
