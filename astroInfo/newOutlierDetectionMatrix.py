from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
#import ruptures as rpt
import matplotlib.pyplot as plt
import numpy as np
import random as rand
import sys
import asteroidMenuClass as menu
import pdb

# Connecting to mongo database and obtain data
dest = "mongodb://schappus:unicornsSUM22@cmp4818.computers.nau.edu:27017"
client = MongoClient(dest)
db = client.ztf
mag18Data = db['mag18o8'] # changed from mag18o8 on 3.4.23
asteroid_data = db['asteroids_all']

# GLOBAL VARS
useMsg = "How this program works: \n\
The program accepts a number of asteroids to observe and value for where in the data \n\
to start. Then, it pulls data for each individual asteroid, and finds the most \n\
outlying point (min or max) and calculates the number of standard deviations away \n\
from the mean that point is. If it is above the mean, the number of sigmas is stored \n\
in the matrix. If it is below the mean, the negative number of sigmas is stored in \n\
the matrix. The final columns in the matrix are a row sum (of sigma multipliers) and \n\
a row sum of the absolute value of each matrix entry. The program then allows users \n\
to filter the data by features at specific user-given values. Then users can view \n\
histograms of all the sigma data and scatterplots for individual asteroids."

offset = 0 # for shifting data scope
wanted_attr = [ "elong", "rb", "H", "mag18omag8" ] # attributes we want to look at
numFeatures = len(wanted_attr)
filterLevel = 1 # default filtering intensity (none)
antIDS = list() # list for associated ztf id for observation
weightDict  = {
    "H": 1,
    "mag18omag8": 1,
    "elong": 1,
    "rb": 1
}


# FUNCTION DEFINITIONS

# clear: takes numerical input and prints that many new lines
# used for clearing the screen to help with readability
def clear(size):
    print("\n" * size)


# help: takes no inputs, prints help message
def help():
    print(useMsg)
    clear(1)


# exportFile: takes no inputs, exports data to either .html or .csv
def exportFile(fileType, filename, data):
    print("Exporting data...\n")

    if fileType == 1:
        data.to_html(buf=filename, index=False)
    if fileType == 2:
        data.to_csv(filename, index=False)

# function for stripping data of all 0 entries
def stripZeros(data):
    dataStrip = data.drop(data[data['rb'] == 0].index)
    dataStrip = dataStrip.drop(dataStrip[dataStrip['elong'] == 0].index)
    dataStrip = dataStrip.drop(dataStrip[dataStrip['H'] == 0].index)
    dataStrip = dataStrip.drop(dataStrip[dataStrip['mag18omag8'] == 0].index)
    return dataStrip
    

    
# fillSigmaMatrix: takes the name of an asteroid, its datatable, and an empty matrix to
# fill with sigma data. Computes sigmas for each attribute and stores them in the matrix.
# Returns the sigma matrix and data regarding the night of each observation's max sigma value
def fillSigmaMatrix(name, asteroid, sigmaMatrix, filterLevel):
    #sigmaMatrix = np.zeros([1, numFeatures + 2]) # two allows for row sum & absolute row sum

    
    attrData = []
    nightData = []

    # grab asteroid name
    #name = asteroidNames["ssnamenr"][ast_ct + offset]
    #name = asteroid

    # reset attributes looked at
    attr_ct = 0
    rowSum = absRowSum = 0

    while ( attr_ct < len(wanted_attr) ):

        # grab feature data and calculate mean and standard deviation
        feature = wanted_attr[attr_ct]
        try: 
            obj_stdev = stat.stdev(asteroid[feature])
            obj_mean = stat.mean(asteroid[feature])
        except Exception as e:
            print((name + " is the object causing error"), e)
            
        # grab weight for feature
        attr_weight = weightDict[feature]

        # sort specific asteroid data by feature
        dataSortedByFeature = pd.DataFrame(mag18Data.find({"ssnamenr": int(name)}).sort(feature))


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

        #if (name == "117581"):
            #pdb.set_trace()
        
        # add data to sigmaMatrix
        if (highSigma > lowSigma):
            # night of obs. used to determine if multiple anomalies occur simultaneously
            night = dataSortedByFeature["night"][maxIndex]

            #sigmaMatrix[ast_ct][attr_ct] = highSigma * attr_weight
            rowSum += highSigma * attr_weight
            absRowSum += highSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append(dataSortedByFeature['id'][maxIndex])
            attrData.append(highSigma * attr_weight)

        else:
            night = asteroid["night"][minIndex]
            #sigmaMatrix[ast_ct][attr_ct] = -lowSigma * attr_weight
            rowSum += -lowSigma * attr_weight
            absRowSum += lowSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append(dataSortedByFeature['id'][minIndex])
            attrData.append(-lowSigma * attr_weight)

        # update attribute count
        attr_ct += 1
        # add night of sigma value to list
        nightData.append(night)

    ####
    rowAttrs = []



    #print("Night Data: " + str(nightData))
    for night in range(len(nightData)):
        if nightData.count(nightData[night]) >= filterLevel:
            rowAttrs.append(attrData[night])
            #print("Night " + str(nightData[night]))
        else:
            rowAttrs.append(0)
    #print("Row Attrs: " + str(rowAttrs))
    # append row sums to sigmaMatrix
    rowAttrs.append(rowSum)
    rowAttrs.append(absRowSum)
    #sigmaMatrix[ast_ct][attr_ct] = rowSum
    #sigmaMatrix[ast_ct][attr_ct + 1] = absRowSum

    sigmaMatrix = rowAttrs

    return (sigmaMatrix, nightData)




# runProgram: runs the program from menu option 1. Lets users view as many asteroids
# as desired from any starting point in the data, then computes and fills the sigma
# matrix and runs data analytics on the results.
def runProgram():
    # total num of asteroids we want to look at
    maxIn = int(input("How many asteroids do you want to look at(-1 if all): "))

    if ( maxIn < 0 ) :
        maxIn = asteroid_data.count()
        allAstDecision = input("This will run all 32k+ asteroids through the system. What would you like to do? \n 1. Run and display output on screen \n 2. Run and export output to file \n 3. Cancel \n")
        if allAstDecision == 3:
            main()
        if allAstDecision == 2:
            exportFlg = 'y'
             
    #offset
    offset = int(input("Where to start in data:(-1 if random):  "))
    
    if ( offset < 0 and maxIn < asteroid_data.count() ):
        offset = rand.randint(0, asteroid_data.count() - maxIn - 1)

        
    exportFlg = input("Would you like to export the results (y/n)? ")

    if exportFlg == 'y':
        fileType =  int(input("Export as \n 1. .html \n 2. .csv \n"))
        filename = input("filename: ")


    filterLevel = int(input("Select level of intensity of filtering: \n 1. None \n 2. Low \n 3. Medium \n 4. High \n"))
        
    # num of asteroids we have looked at 
    ast_ct = 0

    # divider line for output
    divider = ("_" * 120)

    # get all asteroid names
    asteroidNames = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))

    # # list for associated ztf id for observation
    # antIDS = list()

    #Sigma Matrix
    sigmaMatrix = np.zeros([maxIn, numFeatures + 2]) # TEMP PLACEHOLDER NUMBER!!!!!


    # TOP 4 ATTR:
    # mag180mag8 : sigma value for difference in 18 aperture vs 8 aperture photos
    # elong: elong val > 1 means oblong object, if this changes it's interesting
    # rb (real-bogus):
    # H: another measurement of brightness

    # Loop through our collection of names
    while ( ast_ct < maxIn and ast_ct < len(asteroidNames)):
        
        # create temporary row variable to hold asteroid data for appending at the end
        attrData = []
        nightData = []

        # grab asteroid name
        name = asteroidNames["ssnamenr"][ast_ct + offset]

        # reset attributes looked at
        attr_ct = 0

        # loop through wanted attributes
        
        # while ( attr_ct < len(wanted_attr) ):
            # CREATE METHOD FOR THIS PROCCESS SO THAT IT CAN BE USED AGAIN
            # needs to take an asteroid as parameter

            # sort specific asteroid data by Julian Date
        asteroid = pd.DataFrame(mag18Data.find({"ssnamenr": int(name)}).sort("jd"))
        attrData, nightData = fillSigmaMatrix(name, asteroid, sigmaMatrix, filterLevel)
        

        # append attributes to attrData only if multiple occur on same night
        # rowAttrs = []
        # for night in range(len(nightData)):
        #     if nightData.count(nightData[night]) >= 2:
        #         rowAttrs.append(attrData[night])
        #     else:
        #         rowAttrs.append(0)

        # # append row sums to sigmaMatrix
        # rowSum = attrData[len(attrData) - 2]
        # absRowSum = attrData[len(attrData) - 1]
        # rowAttrs.append(rowSum)
        # rowAttrs.append(absRowSum)
        # #sigmaMatrix[ast_ct][attr_ct] = rowSum
        # #sigmaMatrix[ast_ct][attr_ct + 1] = absRowSum

        sigmaMatrix[ast_ct] = attrData

        # update asteroid count
        ast_ct += 1


    # Formatting data structures
    nameArray = np.array( asteroidNames['ssnamenr'])[offset: offset + ast_ct]
    listNames= np.array( antIDS )
    idArray = np.reshape(listNames, (maxIn, numFeatures))


    # DataFrame creation for main data display
    dataset = pd.DataFrame(
        {'Name': nameArray,
         'elong': sigmaMatrix[:, 0],
         'ZTF-ELONG': idArray[:, 0],
         'rb': sigmaMatrix[:, 1],
         'ZTF-RB': idArray[:, 1],
         'H': sigmaMatrix[:, 2],
         'ZTF-H': idArray[:, 2],
         'mag18omag8': sigmaMatrix[:, 3],
         'ZTF-MAG18OMAG8': idArray[:, 3],
         'Row Sum': sigmaMatrix[:, 4],
         'Abs Row Sum': sigmaMatrix[:, 5]
        })

    # User Testing:
    # if allAstDecision == 1:
    #     print(dataset)
    # elif allAstDecision == 2:
    #     exportFile()


    # EXPORT
    newData = stripZeros(dataset)
    if exportFlg == 'y':
        exportFile(fileType, filename, newData)
    else:
        print(newData)
    

    #### UNCOMMENT THIS!!!!! ####

    # This table finds the most outlying point (min or max) and calculates how many standard deviations away from the mean that point is. If it is above the mean, the number of sigmas is stored in the matrix. If it is below the mean, the negative number of sigmas is stored is the matrix. The final columns in the matrix are a row sum (of sigma multipliers) and a row sum of the absolute value of each matrix entry. 



    if ( input("Look at total data histogram (y/n): ") == 'y'):

        # print out all data on asteroid
        # allow user to fetch attributes???
        # menu for usability? (help, inspect specific asteroid, view all data, view selection of data, view data based on criteria, quit)

        totalHistFigs, plts = plt.subplots(2, 3, figsize=(15,15))
        totalHistFigs.suptitle("Histograms")

        # print("Row Sum Histogram")
        plts[0,0].hist(np.array( dataset["Row Sum"]))
        plts[0,0].set(xlabel = "number of sigmas", ylabel = "number of asteroids", title = "Row Sum")

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
        plts[0,1].hist(np.array( dataset["elong"]))
        plts[0,1].set(xlabel = "num sigmas", ylabel = "num asteroids", title = "ELONG")

        print("RB")
        print("Sum :" + str(rbTest))
        print("Mean:" + str(rbTestM))
        plts[0,2].hist(np.array( dataset["rb"]))
        plts[0,2].set(xlabel = "num sigmas", ylabel = "num asteroids", title = "RB")

        print("H")
        print("Sum :" + str(hTest))
        print("Mean:" + str(hTestM))
        plts[1,0].hist(np.array( dataset["H"]))
        plts[1,0].set(xlabel = "num sigmas", ylabel = "num asteroids", title = "H")

        print("MAG18OMAG8")
        print("Sum :" + str(mag18))
        print("Mean:" + str(mag18M))
        plts[1,1].hist(np.array( dataset["mag18omag8"]))
        plts[1,1].set(xlabel = "num sigmas", ylabel = "num asteroids", title = "MAG18OMAG8")

        # adjust the spacing so things don't overlap
        totalHistFigs.subplots_adjust(
                            wspace=0.4,
                            hspace=0.4)

        # delete currently unused 6th plot space
        totalHistFigs.delaxes(plts[1,2])

        # show the total histogram plots
        totalHistFigs.show()

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
            filterHighLimit = int(input("Data >  "))
            filterLowLimit = int(input("Data <  "))

            prevSet = filteredDataset
            filteredDataset = filteredDataset.loc[ ( filteredDataset[ filterInput ] > filterHighLimit ) & ( filteredDataset[ filterInput ] < filterLowLimit ) ]
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



                    
    if (input("Inspect Specific Asteroid(y/n): ") == "y"):
        viewOne()
    
    
###########################################################################################
def viewOne():
    astName = input("Asteroid Name:\n")
    #asteroidNames = pd.DataFrame(asteroid_data.find({},{ '_id': 0, 'ssnamenr' : 1}))
    #asteroidNames.to_html("astNames.html")
    #location = asteroidNames.index.get_loc(int(astName))
    #print("LOCATION: \n")
    #print(location)
    clear(10)
    asteroid = pd.DataFrame(mag18Data.find({"ssnamenr": int(astName)}).sort("jd"))

    menu2Dict = {0: 'Inspect Asteroid ' + str(astName) + ":",
                 1: 'View asteroid data',
                 2: 'Save/download asteroid data',
                 3: 'Filter asteroid data',
                 4: 'Return to Main Menu',
                 5: 'Quit'}

    menu2Choice = 0

    while menu2Choice != 4 or menu2Choice != 5:
        menu.display(menu2Dict)
        menu2Choice = int(input())
        clear(10)
        if menu2Choice == 1:
            print("Asteroid " + astName + " Stats:\n")
            astSigmaMatrix = np.zeros([1, numFeatures + 2])
            nightData = []
            #viewAsteroidData()
            fltrLvl = int(input("Filter Intensity (1: none, 2: low, 3: med, 4: high): "))
            sigmaMatrix, nightData = fillSigmaMatrix(astName, asteroid, astSigmaMatrix, fltrLvl)
            print(sigmaMatrix)
            print(nightData)
            #print("RB: " + str(asteroid["rb"]) + "\n")
            #print("RB: " + str(asteroid["rb"]) + "\n")
            #print("RB: " + str(asteroid["rb"]) + "\n")
            # print outliers for each attribute
            # print nights that each outlier occurred
            # print ZTF id for each outlier's observation
            pass
        elif menu2Choice == 2:
            #saveData(dataToSave)
            print("save all data\n")
            pass
        elif menu2Choice == 3:
            #runFiltering()
            print("run filtering system on individual asteroid observation data")
            pass
        elif menu2Choice == 4:
            main()
        else:
            exit()


    # settup for printing all plots later...
    astDataFigs, ((plt1, plt2), (plt3, plt4)) = plt.subplots(2, 2, figsize=(15,15))
    astDataFigs.suptitle("Asteroid " + astName)
    
    # rb vs. Julian Date scatterplot
    plt1.scatter(asteroid["jd"], asteroid['rb'], color = 'deeppink')
    plt1.set(xlabel = "jd", ylabel = "rb")
    # plt.scatter(asteroid["jd"], asteroid['rb'], color = 'deeppink')
    # plt.xlabel("jd")
    # plt.ylabel("rb")
    # plt.show()
    
    # mag18omag8 vs. Julian Date scatterplot
    plt2.scatter(asteroid["jd"], asteroid['mag18omag8'], color = 'gold')
    plt2.set(xlabel = "jd", ylabel = "mag18omag8")
    # plt.scatter(asteroid["jd"], asteroid['mag18omag8'], color = 'gold')
    # plt.xlabel("jd")
    # plt.ylabel("mag18omag8")
    # plt.show()
    
    # elong vs. Julian Date scatterplot
    plt3.scatter(asteroid["jd"], asteroid['elong'], color = 'blue')
    plt3.set(xlabel = "jd", ylabel = "elong")
    # plt.scatter(asteroid["jd"], asteroid['elong'], color = 'blue')
    # plt.xlabel("jd")
    # plt.ylabel("elong")
    # plt.show()
    
    # H vs. Julian Date scatterplot
    fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
    plt4.scatter(fidFiltered["jd"], fidFiltered['H'], color = 'green')
    fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
    plt4.scatter(fidFiltered["jd"], fidFiltered['H'], color = 'red')
    plt4.set(xlabel = "jd", ylabel = "H")
    
    # plt.scatter(fidFiltered["jd"], fidFiltered['H'], color = 'red')
    # plt.xlabel("jd")
    # plt.ylabel("H")
    # plt.show()
    
    if ( input("Show all plots? (y/n): ") == 'y'):

        astDataAllFigs, ((plt1, plt2, plt3), (plt4, plt5, plt6)) = plt.subplots(2, 3, figsize=(15,15))
        astDataAllFigs.suptitle("Asteroid " + astName)
        
        # mag18omag8 vs. rb scatterplot
        plt1.scatter(asteroid["mag18omag8"], asteroid['rb'], color = 'darkorange')
        plt1.set(xlabel = "mag18omag8", ylabel = "rb", title = "mag18omag8 vs. rb")
        
        # mag18omag8 vs. elong scatterplot
        plt2.scatter(asteroid["mag18omag8"], asteroid['elong'], color = 'mediumaquamarine')
        plt2.set(xlabel = "mag18omag8", ylabel = "elong", title = "mag18omag8 vs. elong")
        
        # mag18omag8 vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt3.scatter(fidFiltered["mag18omag8"], fidFiltered['H'], color = 'limegreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt3.scatter(fidFiltered["mag18omag8"], fidFiltered['H'], color = 'tomato')
        plt3.set(xlabel = "mag18omag8", ylabel = "H", title = "mag18omag8 vs. H")
        
        # rb vs. elong scatterplot
        plt4.scatter(asteroid["rb"], asteroid['elong'], color = 'forestgreen')
        plt4.set(xlabel = "rb", ylabel = "elong", title = "rb vs. elong")
        
        # rb vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt5.scatter(fidFiltered["rb"], fidFiltered['H'], color = 'darkgreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt5.scatter(fidFiltered["rb"], fidFiltered['H'], color = 'darkred')
        plt5.set(xlabel = "rb", ylabel = "H", title = "rb vs. H")
        
        # elong vs. H scatterplot
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 1) ]
        plt6.scatter(fidFiltered["elong"], fidFiltered['H'], color = 'seagreen')
        fidFiltered = asteroid.loc[ (asteroid["fid"] == 2) ]
        plt6.scatter(fidFiltered["elong"], fidFiltered['H'], color = 'firebrick')
        plt6.set(xlabel = "elong", ylabel = "H", title = "elong vs. H")


    #plt.show()


## MAIN PROGRAM:
    
# menu set up:
# view asteroid data
   # if they choose all, preceed with a warning that data is big and ask if they'd like to continue or generate a .csv or .html file
# view specific asteroid
# view data by attribute ??
# help displays use of program & meaning of menu items
def main():
    clear(20)
    menuDict = {0: 'SNAPS Menu',
                1: 'Run program',
                2: 'View specific asteroid',
                3: 'Help',
                4: 'Quit' }

    menuChoice = 0

    # display menu
    while menuChoice != 4:
        menu.display(menuDict)
        menuChoice = int(input())
        clear(10)
        if menuChoice == 1:
            runProgram()
        elif menuChoice == 2:
            viewOne()
        elif menuChoice == 3:
            help()
        else:
            exit()



# Run the program
main()
