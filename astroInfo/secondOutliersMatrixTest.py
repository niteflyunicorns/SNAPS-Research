from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import ruptures as rpt
import matplotlib.pyplot as plt
import numpy as np

# Connecting to mongo database
dest = "mongodb://schappus:unicornsSUM22monsoon@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db['mag18o8_ss1']
asteroid_data = db['asteroids']

# local vars
maxIn = 500
divider = ("_" * 120)
ast_ct = 0

#weights for features
weightDict  = {
  "magpsf": -1,
  "H": 1,
  "mag18omag8": .5,
  "elong": .3,
  "rb": .5
}

# get all asteroid names
asteroidNames = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))

# attributes we look at
wanted_attr = ["magpsf", "elong", "rb", "H", "mag18omag8"]
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
while ( ast_ct < maxIn and ast_ct < len(asteroidNames)):
    # grab asteroid name
    name = asteroidNames["ssnamenr"][ast_ct + 5000]

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

        minDataVal = dataSortedByFeature[feature][minIndex + 1]
        maxDataVal = dataSortedByFeature[feature][maxIndex  - 1]

        upperRange = maxDataVal - obj_mean
        lowerRange = obj_mean - minDataVal

        highSigma = upperRange / obj_stdev
        lowSigma = lowerRange / obj_stdev

        # add data to sigmaMatrix
        if (highSigma > lowSigma):
            sigmaMatrix[ast_ct][attr_ct] = highSigma * attr_weight
            rowSum += highSigma * attr_weight
            absRowSum += highSigma * attr_weight
        else:
            sigmaMatrix[ast_ct][attr_ct] = -lowSigma * attr_weight
            rowSum += -lowSigma * attr_weight
            absRowSum += lowSigma * attr_weight

        attr_ct += 1

    # append row sums to sigmaMatrix
    sigmaMatrix[ast_ct][attr_ct] = rowSum
    sigmaMatrix[ast_ct][attr_ct + 1] = absRowSum

    ast_ct += 1

#print(sigmaMatrix)

nameArray = np.array( asteroidNames['ssnamenr'])[: ast_ct]

dataset = pd.DataFrame({'Name': nameArray, 'magpsf': sigmaMatrix[:, 0], 'elong': sigmaMatrix[:, 1], 'rb': sigmaMatrix[:, 2], 'H': sigmaMatrix[:, 3], 'mag18omag8': sigmaMatrix[:, 4], 'Row Sum': sigmaMatrix[:, 5], 'Abs Row Sum': sigmaMatrix[:, 6]})


#User Testing:
print(dataset)

if (input() == "test"):
    astName = input("Asteroid Name:\n")
    feature = input("Feature:\n")

    asteroid = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(astName)}).sort("jd"))

    print("Asteroid " + astName + " Stats:\n")
    print("Mean: " + str(stat.mean(asteroid[feature])))
    print("Std Dev: " + str(stat.stdev(asteroid[feature])))


    plt.scatter(asteroid["jd"], asteroid[feature], color = 'green')
    plt.scatter(asteroid["jd"], asteroid['mag18omag8'], color = 'red')
    plt.scatter(asteroid["jd"], asteroid['elong'], color = 'blue')
    plt.legend([feature, "mag18omag8", "elong"])

    plt.plot(asteroid["jd"], asteroid[feature], color = 'green')
    plt.plot(asteroid["jd"], asteroid['mag18omag8'], color = 'red')
    plt.plot(asteroid["jd"], asteroid['elong'], color = 'blue')
    plt.legend([feature, "mag18omag8", "elong"])
    plt.show()


print("Row Sum Histogram")
dude = np.array( dataset["Row Sum"])
plt.hist(dude)
plt.show()

magTest = dataset['magpsf'].sum()
elongTest = dataset['elong'].sum()
rbTest = dataset['rb'].sum()
hTest = dataset['H'].sum()
mag18 = dataset['mag18omag8'].sum()

magTestM = dataset['magpsf'].mean()
elongTestM = dataset['elong'].mean()
rbTestM = dataset['rb'].mean()
hTestM = dataset['H'].mean()
mag18M = dataset['mag18omag8'].mean()


print("MAGPSF")
print("Sum :" + str(magTest))
print("Mean:" + str(magTestM))
plt.hist(np.array( dataset["magpsf"]))
plt.show()

print("ELONG")
print("Sum :" + str(elongTest))
print("Mean:" + str(elongTestM))
plt.hist(np.array( dataset["elong"]))
plt.show()

print("RB")
print("Sum :" + str(rbTest))
print("Mean:" + str(rbTestM))
plt.hist(np.array( dataset["rb"]))
plt.show()

print("H")
print("Sum :" + str(hTest))
print("Mean:" + str(hTestM))
plt.hist(np.array( dataset["H"]))
plt.show()

print("MAG18OMAG8")
print("Sum :" + str(mag18))
print("Mean:" + str(mag18M))
plt.hist(np.array( dataset["mag18omag8"]))
plt.show()
