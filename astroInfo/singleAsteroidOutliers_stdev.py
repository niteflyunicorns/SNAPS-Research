from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import ruptures as rpt
import matplotlib.pyplot as plt
# import numpy as np

# What properties are cyclic? Maybe all of them, don't really want to
# prejudice our understanding
dest = "mongodb://schappus:unicornsSUM22monsoon@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db["snapshot 1"]
asteroid_data = db['asteroids']

# FOR TESTING:
# uncomment to test specific a specific asteroid, feature, & stdev
ast_num = input("Asteroid ssnamenr:\n")
feature = input("Asteroid Feature:\n")
stdev_mult = input("Desired std dev multiplier for outlier detection:\n")



asteroids = pd.DataFrame(asteroid_data.find())
object_series_fields_drop = ["_id", "id", "pid", "obsdist", "phaseangle", "heliodist", "antaresID"]
asteroid = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(ast_num)}).sort("jd"))

obj_stdev = stat.stdev(asteroid[feature])
obj_mean = stat.mean(asteroid[feature])

# FOR TESTING ALSO:
# need to create dict with key = "jd" and value = feature, then sort by jd
plt.plot(asteroid["jd"], asteroid[feature])

dataIndex = 0
outlierCount = 0
outlierFlag = obj_stdev * int(stdev_mult)
outlierList = list()

while (dataIndex < len(asteroid[feature])):
    if ( abs(obj_mean - asteroid[feature][dataIndex]) ) > ( outlierFlag ):
        outlierCount += 1
        outlierList.append(dataIndex)
    dataIndex += 1

print("Mean: " + str(obj_mean))
print("Std Dev: " + str(obj_stdev))
#print("Outlier Range: " + outlierFlag)
print("Low Cutoff: " + str(obj_mean - outlierFlag))
print("High Cutoff: " + str(obj_mean + outlierFlag))
print("Num Outliers: " + str(outlierCount))
print("Outliers: " + str(outlierList))
