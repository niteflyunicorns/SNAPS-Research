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

from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import ruptures as rpt
import matplotlib.pyplot as plt
import numpy as np
import random as rand

#### UNCOMMENT THIS!!!!! ####
dest = "mongodb://schappus:unicornsSUM22@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
ztf_series_data = db['mag18o8_ss1']
asteroid_data = db['asteroids']

# This table finds the most outlying point (min or max) and calculates how many standard deviations away from the mean that point is. If it is above the mean, the number of sigmas is stored in the matrix. If it is below the mean, the negative number of sigmas is stored is the matrix. The final columns in the matrix are a row sum (of sigma multipliers) and a row sum of the absolute value of each matrix entry. 

dataset = pd.read_csv("totalSigmaTable.csv")

# User Testing:
print(dataset)

if ( input("Look at total data histogram (y/n): ") == 'y'):
        print("Row Sum Histogram")
        dude = np.array( dataset["Row Sum"])
        plt.hist(dude)
        plt.xlabel("num sigmas")
        plt.ylabel("num asteroids")
        plt.show()

        elongTest = dataset['elong'].sum()
        rbTest = dataset['rb'].sum()
        hTest = dataset['H'].sum()
        mag18 = dataset['mag18omag8'].sum()

        elongTestM = dataset['elong'].mean()
        rbTestM = dataset['rb'].mean()
        hTestM = dataset['H'].mean()
        mag18M = dataset['mag18omag8'].mean()


        print("ELONG")
        print("Sum :" + str(elongTest))
        print("Mean:" + str(elongTestM))
        plt.hist(np.array( dataset["elong"]))
        plt.xlabel("num sigmas")
        plt.ylabel("num asteroids")
        plt.show()

        print("RB")
        print("Sum :" + str(rbTest))
        print("Mean:" + str(rbTestM))
        plt.hist(np.array( dataset["rb"]))
        plt.xlabel("num sigmas")
        plt.ylabel("num asteroids")
        plt.show()

        print("H")
        print("Sum :" + str(hTest))
        print("Mean:" + str(hTestM))
        plt.hist(np.array( dataset["H"]))
        plt.xlabel("num sigmas")
        plt.ylabel("num asteroids")
        plt.show()

        print("MAG18OMAG8")
        print("Sum :" + str(mag18))
        print("Mean:" + str(mag18M))
        plt.hist(np.array( dataset["mag18omag8"]))
        plt.xlabel("num sigmas")
        plt.ylabel("num asteroids")
        plt.show()

# rbLowFlag = dataset[ dataset[ 'rb' ] <= -4 ]
# rbHighFlag = dataset[ dataset[ 'rb' ] >= 0 ]
# HHighFlag = dataset[ dataset[ 'H' ] >= 3 ]
# HLowFlag = dataset[ dataset[ 'H' ] <= -4 ]
# elongHighFlag = dataset[ dataset[ 'elong' ] >= 4 ]

#Filter Loop 
#############################################################

#New Area
   
filteredDataset = dataset

emptyFlag = False
continueFlag = True


while ( continueFlag and( not emptyFlag ) ):
    
    filterInput = input("Enter feature to filter by('n' if None): \n")
    continueFlag = (filterInput != 'n')

    if ( continueFlag ):
        filterHighLimit = int(input("High Limit( Data > limit): \n"))
        filterLowLimit = int(input("Low limit( Data < Limit): \n"))
        
        prevSet = filteredDataset
        filteredDataset = filteredDataset.loc[ ( filteredDataset[ filterInput ] >= filterHighLimit ) & ( filteredDataset[ filterInput ] <= filterLowLimit ) ]
        emptyFlag = filteredDataset.empty
        
        if ( not emptyFlag ):
            print(filteredDataset)

        else:
            print("This returns an empty Data Set ")

            resetInput = int(input("0 to continue, 1 to reset last filter, 2 to reset all filters"))

            if ( resetInput == 1):
                filteredDataset = prevSet
                emptyFlag = False
                continueFlag = True

            if ( resetInput == 2):
                filteredDataset = dataset
                emptyFlag = False
                continueFlag = True
        
        
    
    
    #####################################################################

inspectFlag = input("Inspect Specific Asteroid(y/n): ") != "n"

while ( inspectFlag ):
    astName = input("Asteroid Name:\n")
    asteroid = pd.DataFrame(ztf_series_data.find({"ssnamenr": int(astName)}).sort("jd"))
    print("Asteroid " + astName + " Stats:\n")

    # rb vs. Julian Date scatterplot
    plt.scatter(asteroid["jd"], asteroid['rb'], color = 'deeppink')
    plt.xlabel("jd")
    plt.ylabel("rb")
    plt.show()
    
    # mag18omag8 vs. Julian Date scatterplot
    plt.scatter(asteroid["jd"], asteroid['mag18omag8'], color = 'gold')
    plt.xlabel("jd")
    plt.ylabel("mag18omag8")
    plt.show()
    
    # elong vs. Julian Date scatterplot
    plt.scatter(asteroid["jd"], asteroid['elong'], color = 'blue')
    plt.xlabel("jd")
    plt.ylabel("elong")
    plt.show()
    
    # H vs. Julian Date scatterplot
    fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
    plt.scatter(fidFiltered["jd"], fidFiltered['H'], color = 'green')
    fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
    plt.scatter(fidFiltered["jd"], fidFiltered['H'], color = 'red')
    plt.xlabel("jd")
    plt.ylabel("H")
    plt.show()
    
    if ( input("Show all plots? (y/n): ") == 'y'):
        # mag18omag8 vs. rb scatterplot
        plt.scatter(asteroid["mag18omag8"], asteroid['rb'], color = 'darkorange')
        plt.xlabel("mag18omag8")
        plt.ylabel("rb")
        plt.show()
        
        # mag18omag8 vs. elong scatterplot
        plt.scatter(asteroid["mag18omag8"], asteroid['elong'], color = 'mediumaquamarine')
        plt.xlabel("mag18omag8")
        plt.ylabel("elong")
        plt.show()
        
        # mag18omag8 vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt.scatter(fidFiltered["mag18omag8"], fidFiltered['H'], color = 'limegreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt.scatter(fidFiltered["mag18omag8"], fidFiltered['H'], color = 'tomato')
        plt.xlabel("mag18omag8")
        plt.ylabel("H")
        plt.show()
        
        # rb vs. elong scatterplot
        plt.scatter(asteroid["rb"], asteroid['elong'], color = 'forestgreen')
        plt.xlabel("rb")
        plt.ylabel("elong")
        plt.show()
        
        # rb vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt.scatter(fidFiltered["rb"], fidFiltered['H'], color = 'darkgreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt.scatter(fidFiltered["rb"], fidFiltered['H'], color = 'darkred')
        plt.xlabel("rb")
        plt.ylabel("H")
        plt.show()
        
        # elong vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt.scatter(fidFiltered["elong"], fidFiltered['H'], color = 'seagreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt.scatter(fidFiltered["elong"], fidFiltered['H'], color = 'firebrick')
        plt.xlabel("elong")
        plt.ylabel("H")
        plt.show()
        
    inspectFlag = input("Inspect Another Asteroid(y/n): ") != "n"
    
## END OF PROGRAM ##