#########################################################################################
### Program: SNAPS Anomaly Detection for Individual Asteroids
### Programmer: Savannah Chappus
### Last Update: 7.31.2024
#########################################################################################

## IMPORTS ##############################################################################
from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import matplotlib.pyplot as plt
from matplotlib import gridspec
import mplcursors
import numpy as np
import random as rand
import pdb
import sys
import configparser as cfp
#from line_profiler import profile
# custom py file imports
# import asteroidMenuClass as menu

## MONGO CONNECTION #####################################################################
def getSecrets():
    config = cfp.ConfigParser()
    config.read( 'config.ini' )
    user = config.get( 'Database', 'dbUser' )
    host = config.get( 'Database', 'dbHost' )
    port = config.get( 'Database', 'dbPort' )
    pswd = config.get( 'Database', 'dbPass' )

    return [ user, host, port, pswd ]
    
user, host, port, pswd = getSecrets()
dest = "mongodb://" + user + ":" + pswd + "@" + host + ":" + port
client = MongoClient( dest )
db = client.ztf
mag18Database = db[ 'mag18o8' ] # all asteroids with mag18o8 data
asteroid_data = db[ 'asteroids_all' ]

## GLOBAL VARS ##########################################################################
useMsg = "How this program works: \n\
The program accepts a number of asteroids \n\
to observe and value for where in the data \n\
to start. Then, it pulls data for each \n\
individual asteroid, and finds the most \n\
outlying point (min or max) and calculates \n\
the number of standard deviations away \n\
from the mean that point is. If it is above \n\
the mean, the number of sigmas is stored \n\
in the matrix. If it is below the mean, the \n\
negative number of sigmas is stored in \n\
the matrix. The final columns in the matrix \n\
are a row sum (of sigma multipliers ) and \n\
a row sum of the absolute value of each \n\
matrix entry. The program then allows users \n\
to filter the data by features at specific \n\
user-given values. Then users can view \n\
histograms of all the sigma data and \n\
scatterplots for individual asteroids. \n\n"

argsExpl = "Command Line Arguments Format & Meaning: \n\
\t\t python astOutleirMatNew.py maxIn offset fltrType fltrLvl plots exportFlg fileType fileName astName featFltr lB uB \n\
1. maxIn: number of asteroids to view (-1 to view all) \n\
2. offset: where to start in data (-1 if random) \n\
3. fltrType: type of filtering system to use on the selection of asteroids \n\
\t (1) number of outlier occurences per night \n\
\t (2) by overall asteroid anomaly rating \n\
\t (3) by weighted attribute filtering \n\
\t (4) none \n\
4. fltrLvl: the intensity of your chosen filter. \n\
\t for filter 1: 0, 2, 3, 4 (number of outliers per night) \n\
\t for filter 2: any number 0-99, 0 = not anomalous, 100 = very anomalous \n\
\t for filter 3: --> new prompt to get weights for each attribute \n\
5. plots: include plots and diagrams as well as written data \n\
6. exportFlg: export outputs to file. Note: if plots are included, \n\
\t plots will export as individual .png files and text will output to \n\
\t the desired file type. \n\
\n\
Optional Arguments: \n\
If exporting results, \n\
\t 1. file type: (1) .html, (2) .csv \n\
\t 2. file name (note: png files will export with this name as the prefix) \n\n\
When viewing only one asteroid, \n\
\t 1. asteroid name \n\
\t 2. feature to filter by (rb, elong, H, mag18, none) \n\
\t 3. lower filter bound (...) \n\
\t 4. upper filter bound (...) \n\
\n\
"

offset = 0 # for shifting data scope
attrList = "ssnamenr, jd, fid, pid, diffmaglim, ra, dec, magpsf, sigmapsf, \
chipsf, magap, sigmagap, magapbig, sigmagapbig, distnr, magnr, fwhm, elong, rb, \
ssdistnr, ssmagnr, id, night, phaseangle, obsdist, heliodist, H, ltc, mag18omag8"
# attrList is for users to choose attrs to filter by

# Top 4 Attributes of Interest:
# mag180mag8 : sigma value for difference in 18" aperture vs 8" aperture photos
# elong: elong val > 1 means oblong object, if this changes it's interesting
# rb (real-bogus ): value to represent the "validity" or "trustworthiness" of the
# collected data
# H: another measurement of brightness
wantedAttrs = [ "elong", "rb", "H", "mag18omag8" ] # attributes we want to look at
# wantedAttrs = [ ]
dataCols = wantedAttrs.copy()
dataCols.extend( [ 'jd', 'id', 'ssnamenr' ] ) # additional cols needed for processing
numFeatures = len( wantedAttrs )
antIDS = list( ) # list for associated ztf id for observation
weightDict = {
    "H": 1,
    "mag18omag8": 1,
    "elong": 1,
    "rb": 1
} # not currently used 

## FUNCTION DEFINITIONS #################################################################

# clear: takes numerical input and prints that many new lines
# used for clearing the screen to help with readability
def clear( size ):
    print( "\n" * size )

# getInputs: takes an dinput array and output array. Loops through
# input prompts and gets user input and stores in output array
def getInputs( inArray, outArray ):
    for prompt in inArray:
        value = input( prompt )
        outArray.append( value )

# help: takes no inputs, prints the help message
def help( ):
    print( useMsg )
    print( argsExpl )
    clear( 1 )

# leave: takes no inputs, prints exit message & ends program
def leave( ):
    print( "Thank you for using SNAPS!\n" )

# exportFile: takes fileType, filename, and data as inputs, exports
# data to either .html or .csv
### TODO: modify program so that getting fileType and filename happen inside
### this function
def exportFile( fileType, filename, data ):
    print( "Exporting data...\n" )
    if fileType == 1:
        data.to_html( buf=filename, index=False )
    if fileType == 2:
        data.to_csv( filename, index=False )

# this function has been commented out because there is a potential error
# later in the code that may require this to be reintroduced in some form
# # function for stripping data of all 0 entries
# def stripZeros(data, fltrLvl ):
#     #print(data.count(0.0 ) )
#     if int(data.count(0.0 ) ) >= fltrLvl:
#         return [ ]
#     return data

# getFilter: takes no inputs, gets filter type and level input from user
# def getFilter( ):
    # typeDict = { 0: 'Select Filter Type:',
    #             1: 'By number of outlier occurences per night',
    #             2: 'By overall asteroid anomaly rating',
    #             3: 'By weighted attribute filtering',
    #             4: 'None' }
    # menu.display( typeDict )
    # fltrType = int( input( ) )
    # if fltrType == 1:
    #     clear( 2 )
    #     levelDict = { 0: 'Select Filter Intensity:',
    #             1: 'None',
    #             2: 'more than 2 outliers per night',
    #             3: 'more than 3 outliers per night',
    #             4: 'exactly 4 outliers per night' }
    #     menu.display( levelDict )
    #     fltrLvl = int( input( ) )
    # elif fltrType == 2:
    #     fltrLvl = float( input( 
    #         "Rating Filter (ex. enter '90' for 90% chance or more of anomaly ): " ) )
    # elif fltrType == 3:
    #     # TODO: add weighted attribute filtering
    #     print( "Defaulting to no filter..." )
    #     fltrLvl = 0
    # else:
    #     fltrLvl = 0
        
    # return [ fltrType, fltrLvl ]

# normValue: takes element to normalize, min, and max values and normalizes to [ 0,1 ]
#@profile
def normValue( value, minVal, maxVal ):
    normVal = ( value - minVal ) / ( maxVal - minVal )
    return normVal

# normDataset: takes in dataset (need not be single-column ) and normalizes
# to range [ 0,1 ]
#@profile
def normDataset( astData ):
    normalizedData = astData.copy( )
    for col in wantedAttrs:
        sortedData = astData.sort_values( by = [ col ] )
        minVal = sortedData[ col ].iloc[ 0 ]
        maxVal = sortedData[ col ].iloc[ len( sortedData ) - 1 ]
        for row in range( len( astData[ col ] ) ):
            newVal = normValue( astData[ col ][ row ], minVal, maxVal )
            normalizedData.loc[ row, col ] = newVal
    return normalizedData

# getObsRating: helper function to getAllObsRatings responsible for getting the
# rating for a single observation for an asteroid
#@profile
def getObsRating( attr, row ):
    obsRating = 0
    for val in row:
        if attr in [ "elong", "mag18omag8" ]:
            obsRating += float( val )
        else:
            obsRating += float( 1 - val )
    # return obsRating
    return ( obsRating / 3 ) # hardcoded: needs to be number of wanted attributes

# getAllObsRatings: helper function to getAstRating responsible for getting
# the ratings for all observations for a given asteroid
#@profile
def getAllObsRatings( data, attr ):
    ratings = [ ]
    for ind, row in data.iterrows():
        obsRating = getObsRating( attr, row )
        ratings.append( obsRating )
    return ratings

# getAstRating: provides a rating for an asteroid based on highest observation
# rating for the asteroid based on outliers
#@profile
def getAstRating( inData, plots, export ):
    # plots = False
    ratings = [ ]
    frames = [ ]
    newAttrs = [ 'elong', 'rb', 'mag18omag8' ]
    data = inData[ dataCols ]
    for attr in newAttrs:
        sortedData = data.sort_values( by = [ attr ] )
        ratingsData = sortedData[ 'jd' ]
        normData = normDataset( sortedData )
        ratings = getAllObsRatings( normData[ newAttrs ], attr )

    ratingsDF = pd.DataFrame( data=ratings, columns=[ 'ratings' ] )
    ratingsData = pd.concat( [ ratingsDF, ratingsData ], axis=1, join='inner' )

    if plots:
        plotData = ratingsData.sort_values( by = ['jd'] )
        plotAstRatings( data[ 'ssnamenr' ][ 0 ], plotData[ 'jd' ], plotData[ 'ratings' ], "jd", "rating", export )

    astRating = max( ratings ) * 100
    print( "Max Rating Index: " + str( ratings.index( max( ratings ) ) ) )
    return ratings, astRating

# plotAstRating: plots the ratings for each observation of an asteroid as collected
# in getAllObsratings
#@profile
def plotAstRatings( name, xData, yData, xName, yName, export ):
    plt.clf()
    plt.title( "Asteroid " + str( name ) )
    plt.scatter( xData, yData, color = 'deeppink' )
    plt.xlabel( xName )
    plt.ylabel( yName )
    plt.ylim( 0, 1 )

    if export:
        savefile = str( name ) + "-ratings.png"
        plt.savefig( savefile )
    else:
        ### TODO ###
        # modify these two lines so that the annotation
        # on hover states the elong, mag18, and rb
        # values for that date. Maybe also include the
        # actual value of the rating...?
        # cursor = mplcursors.cursor( hover=True )
        # cursor.connect( "add", lambda sel: sel.annotation.set_text( data[ "jd" ].iloc[ sel.index ] ) )
        plt.show( block=True )
        plt.show()
        pass

# getAllObs: takes an asteroid and it's data and prints
# or exports each row in a nice neatly formatted way.
def getAllObs( name, data, exportFlg ):
    # if not exportFlg:
    #     print( "Asteroid " + str( name ) + ":" )
    #     for row in data:
    #         if row in [ "elong", "rb", "id", "night", "H", "mag18omag8" ]:
    #             miniDF = pd.concat( [ data[ "jd" ], data[ row ] ], axis=1, join='inner' )
    #             # print( str(row) )
    #             # print( str( data[ row ] ) )
    #             print( miniDF )
    # else:
    pass
            
  
# formatDataTable: takes in sigma matrix, antares IDs array, asteroid name array,
# number of asteroids, and number of features and formats the sigma matrix into
# a more reader-friendly table with headers
#@profile
def formatDataTable( sigmaMatrix, antIDS, nameArray, maxIn, numFeatures ):
    listNames = [ ]
    idArray = [ ]
    listNames= np.array( antIDS )
    idArray = np.reshape( listNames, ( maxIn, numFeatures ) )
    if maxIn != 1:
        dataset = pd.DataFrame(
            { 'Name': nameArray,
             'elong': sigmaMatrix[ :, 0 ],
             'ZTF-ELONG': idArray[ :, 0 ],
             'rb': sigmaMatrix[ :, 1 ],
             'ZTF-RB': idArray[ :, 1 ],
             'H': sigmaMatrix[ :, 2 ],
             'ZTF-H': idArray[ :, 2 ],
             'mag18omag8': sigmaMatrix[ :, 3 ],
             'ZTF-MAG18OMAG8': idArray[ :, 3 ],
             'Row Sum': sigmaMatrix[ :, 4 ],
             'Abs Row Sum': sigmaMatrix[ :, 5 ],
             'Rating': sigmaMatrix[ :, 6 ]
            } )
    if maxIn == 1:
        ### ERROR: code below only works with 1 asteroid from "view one"
        ### not from 'run program' due to formatting. TODO: Fix this
        dataset = pd.DataFrame(
            { 'Name': nameArray,
             'elong': sigmaMatrix[ 0 ],
             'ZTF-ELONG': idArray[ :, 0 ],
             'rb': sigmaMatrix[ 1 ],
             'ZTF-RB': idArray[ :, 1 ],
             'H': sigmaMatrix[ 2 ],
             'ZTF-H': idArray[ :, 2 ],
             'mag18omag8': sigmaMatrix[ 3 ],
             'ZTF-MAG18OMAG8': idArray[ :, 3 ],
             'Row Sum': sigmaMatrix[ 4 ],
             'Abs Row Sum': sigmaMatrix[ 5 ],
             'Rating': sigmaMatrix[ 6 ]
            } )
        
    return dataset
    
# fillSigmaMatrix: takes the name of an asteroid, its data table, and an
# empty matrix to fill with sigma data. Computes sigmas for each attribute
# and stores them in the matrix. Returns the sigma matrix and data regarding
# the night of each observation's max sigma value
#@profile
def fillSigmaMatrix( name, asteroid, sigmaMatrix, fltr, outFlag, plot, export ):
    attrData = [ ]
    obsData = [ ]
    outliers = [ ]
    outliersLoc = [ ]
    outlierNorms = [ ]
    stripFlag = False
    fltrType = fltr[ 0 ]
    fltrLevel = fltr[ 1 ]

    # reset attributes looked at
    attr_ct = 0
    rowSum = absRowSum = 0

    while ( attr_ct < len( wantedAttrs ) ):
        # grab feature data and calculate mean and standard deviation
        feature = wantedAttrs[ attr_ct ]
        try: 
            obj_stdev = stat.stdev( asteroid[ feature ] )
            obj_mean = stat.mean( asteroid[ feature ] )
        except Exception as e:
            print( ( str(name) + " is the object causing error" ), e )
            
        # grab weight for feature
        attr_weight = weightDict[ feature ]

        # sort specific asteroid data by feature & normalize
        # dataSortedByFeature = pd.DataFrame( 
            # mag18Data.find( { "ssnamenr": int( name ) } ).sort( feature ) )
        # dataSortedByFeature = pd.DataFrame( 
            # mag18Data.find( { "ssnamenr": int( name ) } ) )
        asteroid.sort_values( by = [ feature ] )

        # print( asteroid )
        # normData = normDataset( dataSortedByFeature )

        # calculate min, max, and ranges for highSigma and lowSigma values
        minIndex = 0
        maxIndex = len( asteroid ) - 1

        minVal = ( asteroid[ feature ][ minIndex ] )
        maxVal = ( asteroid[ feature ][ maxIndex ] )

        upperRange = maxVal - obj_mean
        lowerRange = obj_mean - minVal

        highSigma = upperRange / obj_stdev
        lowSigma = lowerRange / obj_stdev

        featObsDF = asteroid[ [ feature, "jd" ] ]

        
        # add data to sigmaMatrix
        if ( highSigma > lowSigma ):
            # jd of observation
            obs = asteroid[ "jd" ][ maxIndex ]

            rowSum += highSigma * attr_weight
            absRowSum += highSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append( asteroid[ 'id' ][ maxIndex ] )
            attrData.append( highSigma * attr_weight )

            # store outliers
            outliers.append( maxVal )

            # calculations for filtering ( opt 2 )
            # outlierNorms.append( normData[ feature ][ maxIndex ] )

        else:
            obs = asteroid[ "jd" ][ minIndex ]
            rowSum += -lowSigma * attr_weight
            absRowSum += lowSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append( asteroid[ 'id' ][ minIndex ] )
            attrData.append( -lowSigma * attr_weight )

            # store outliers
            outliers.append( minVal )

            # calculations for filtering ( opt 2 )
            # outlierNorms.append( normData[ feature ][ minIndex ] )

        # update attribute count
        attr_ct += 1
        # add jd of sigma value to list
        obsData.append( obs )

    rowAttrs = [ ]
    numZeros = 0

    #### FILTERING DATA ####
    if fltrType == 1:
        # Option 1: filter by number of times outliers occur during single observation
        for obs in range( len( obsData ) ):
            if obsData.count( obsData[ obs ] ) >= fltrLevel:
                rowAttrs.append( attrData[ obs ] )
            else:
                rowAttrs.append( 0 )
                numZeros += 1
        if numZeros > fltrLevel:
            stripFlag = True        
    elif fltrType == 2:
        # Option 2: filter by specifications
        # assigns rating to each asteroid on how likely they are to be anomalous
        # each category is normalized to [ 0,1 ] and the outlying point is rated from
        # 1 to 100 for each category. Then, scores for each category are averaged to get
        # total score for the asteroid. ## TODO ( optional ): incorporate weighting system
        rowAttrs = attrData
        ratings, astRating = getAstRating( asteroid, plot, export )
        
        if astRating < fltrLevel:
            stripFlag = True
    elif fltrType == 3:
        # Option 3: filter by weight
        ### TODO: Write filter by weight option
        pass
    else:
        pass

    # setting rowAttrs and astRating
    if fltrType != 2:
        astRating = np.nan
    if fltrType in [ 3, 4 ]:
        rowAttrs = attrData

    rowAttrs.append( rowSum )
    rowAttrs.append( absRowSum )
    rowAttrs.append( astRating )
    
    sigmaMatrix = rowAttrs
    if stripFlag:
        sigmaMatrix = [ ]

    if outFlag:
        return ( sigmaMatrix, obsData, outliers )

    return ( sigmaMatrix, obsData )

########################################################################################
### RUNPROGRAM function
### Inputs: none
### Returns: none
### Use: runs the program from menu option 1. Lets users view as many asteroids
### as desired from any starting point in the data, then computes and fills the sigma
### matrix and runs data analytics on the results.
########################################################################################
#@profile
def runProgram( maxIn, offset, exportFlg, exportArgs, fltrType, fltrLvl, plots ):
    # total num of asteroids we want to look at
    #maxIn = int( input( "How many asteroids do you want to look at( -1 if all ): " ) )
    
    # get all asteroid names
    asteroidNames = pd.DataFrame( asteroid_data.find( {},{ '_id': 0, 'ssnamenr' : 1 } ) )
    fileType, fileName = exportArgs

    featFltr = 'n'
    if ( maxIn < 0 ) :
        # print(asteroid_data)
        maxIn = asteroidNames.size
        print( "WARNING: This will run all " + str( maxIn ) + " asteroids through the program." )
        # print( "This process may take several hours depending on your system.\n" )
        # if ( input( "Continue (y/n)? " ) == 'n' ):
            # exit()
        # allAstMenu = { 0: 'What would you like to do?',
        #         1: 'Run and display output on screen',
        #         2: 'Run and export output to file',
        #         3: 'Cancel' }
        # menu.display( allAstMenu )
        # allAstDecision = int( input( ) )
        # if allAstDecision == 3:
        # runProgram( )
        # if allAstDecision == 2:
            # exportFlg = 'y'
             
    #offset = int( input( "Where to start in data:( -1 if random ):  " ) )
    
    if ( offset < 0 and maxIn < asteroid_data.count( ) ):
        offset = rand.randint( 0, asteroid_data.count( ) - maxIn - 1 )

    # exportFlg = input( "Would you like to export the results ( y/n )? " )

    # if exportFlg == 'y':
        # fileType =  int( input( "Export as \n 1. .html \n 2. .csv \n" ) )
        # filename = input( "filename: " )

    # fltr = getFilter( )
    fltr = [ fltrType, fltrLvl ]
        
    # num of asteroids we have looked at 
    ast_ct = 0

    #Sigma Matrix
    extraCols = 3 # for: rowSum, absRowSum, asteroidRating
    sigmaMatrix = np.zeros( [ maxIn, numFeatures + extraCols ] )

    # necessary data from database
    # print( "asteroidNames \n" )
    # astNamesArr = asteroidNames[ "ssnamenr" ][:maxIn].values.tolist()
    # print( astNamesArr )
    # mag18DataNew = pd.DataFrame( mag18Database.find( { "ssnamenr": { "$in": astNamesArr } }, { "id": 1, "ssnamenr": 1, "jd": 1, "elong": 1, "rb": 1, "H": 1, "mag18omag8": 1, "night": 1 } ) )
    # print( mag18DataNew )

    # Loop through our collection of names
    while ( ast_ct < maxIn and ast_ct < len( asteroidNames ) ):
        # create temporary row variable to hold asteroid data for appending at the end
        attrData = [ ]
        obsData = [ ]
        arrayOffset = ast_ct + offset

        # grab asteroid name
        name = asteroidNames[ "ssnamenr" ][ arrayOffset ]

        # reset attributes looked at
        attr_ct = 0

        # sort specific asteroid data by Julian Date
        mag18Data = pd.DataFrame( mag18Database.find( { "ssnamenr": int( name ) } ) )
        mag18Data = mag18Data[ dataCols ]
        # mag18Data = mag18DataNew
        asteroid = mag18Data.sort_values( by = [ "jd" ] )
        attrData, obsData = fillSigmaMatrix( name, asteroid, sigmaMatrix, fltr, False, plots, exportFlg )
        
        if len( attrData ) != 0:
            sigmaMatrix[ ast_ct ] = attrData

        # update asteroid count
        ast_ct += 1

        if plots:
            plot3Das2D( name, asteroid['rb'],
                        asteroid['elong'],
                        asteroid['mag18omag8'],
                        "rb", "elong", "mag18omag8",
                        asteroid, exportFlg )
        
            plot3Dand2D( name, asteroid['rb'],
                         asteroid['elong'],
                         asteroid['mag18omag8'],
                         "rb", "elong", "mag18omag8",
                         asteroid, exportFlg )

    # Reset arrays for rerunning program
    nameArray = [ ]
    listNames = [ ]
    idArray = [ ]
        
    # Formatting data structures
    arrayOffset = offset + ast_ct
    nameArray = np.array( asteroidNames[ 'ssnamenr' ] )[ offset: arrayOffset ]

    dataset = formatDataTable( sigmaMatrix, antIDS, nameArray, maxIn, numFeatures )

    # clear antIDS for next use
    antIDS.clear( )

    # EXPORT
    # drop all rows in data where zeros are present ( from filters )
    ### WARNING: I'm not sure if this works with the new filter system
    ### TODO: check if it works and fix if it doesn't
    newData = dataset.drop( 
        dataset.query( "rb==0 and elong==0 and H==0 and mag18omag8==0" ).index )
    if exportFlg:
        exportFile( fileType, fileName, newData )
    else:
        print( newData )
    
    # first printout of relevant asteroid data
    # if ( input( "Look at total data histogram ( y/n ): " ) == 'y' ):
    if ( plots ):
        totalHistFigs, plts = plt.subplots( 2, 3, figsize=( 15,15 ) )
        totalHistFigs.suptitle( "Histograms" )

        # print( "Row Sum Histogram" )
        plts[ 0,0 ].hist( np.array( dataset[ "Row Sum" ] ) )
        plts[ 0,0 ].set( xlabel = "num sigmas", ylabel = "num asteroids", title = "Row Sum" )

        elongTest = dataset[ 'elong' ].sum( )
        rbTest = dataset[ 'rb' ].sum( )
        hTest = dataset[ 'H' ].sum( )
        mag18 = dataset[ 'mag18omag8' ].sum( )

        elongTestM = dataset[ 'elong' ].mean( )
        rbTestM = dataset[ 'rb' ].mean( )
        hTestM = dataset[ 'H' ].mean( )
        mag18M = dataset[ 'mag18omag8' ].mean( )


        print( "ELONG" )
        print( "Sum :" + str( elongTest ) )
        print( "Mean:" + str( elongTestM ) )
        plts[ 0,1 ].hist( np.array( dataset[ "elong" ] ) )
        plts[ 0,1 ].set( xlabel = "num sigmas",
                      ylabel = "num asteroids",
                      title = "ELONG" )

        print( "RB" )
        print( "Sum :" + str( rbTest ) )
        print( "Mean:" + str( rbTestM ) )
        plts[ 0,2 ].hist( np.array( dataset[ "rb" ] ) )
        plts[ 0,2 ].set( xlabel = "num sigmas",
                      ylabel = "num asteroids",
                      title = "RB" )

        print( "H" )
        print( "Sum :" + str( hTest ) )
        print( "Mean:" + str( hTestM ) )
        plts[ 1,0 ].hist( np.array( dataset[ "H" ] ) )
        plts[ 1,0 ].set( xlabel = "num sigmas",
                      ylabel = "num asteroids",
                      title = "H" )

        print( "MAG18OMAG8" )
        print( "Sum :" + str( mag18 ) )
        print( "Mean:" + str( mag18M ) )
        plts[ 1,1 ].hist( np.array( dataset[ "mag18omag8" ] ) )
        plts[ 1,1 ].set( xlabel = "num sigmas",
                      ylabel = "num asteroids",
                      title = "MAG18OMAG8" )

        # adjust the spacing so things don't overlap
        totalHistFigs.subplots_adjust( 
                            wspace=0.4,
                            hspace=0.4 )

        # delete currently unused 6th plot space
        totalHistFigs.delaxes( plts[ 1,2 ] )

        # show the total histogram plots
        totalHistFigs.show( )

    ### FOR PROGRAMMERS: the below are "ideal" filter levels for each attribute
    ### this data is subjective and open to change. Additionally, this filtering
    ### method has essentially been replaced by the anomaly rating
    # rbLowFlag = dataset[ dataset[ 'rb' ] <= -4 ]
    # rbHighFlag = dataset[ dataset[ 'rb' ] >= 0 ]
    # HHighFlag = dataset[ dataset[ 'H' ] >= 3 ]
    # HLowFlag = dataset[ dataset[ 'H' ] <= -4 ]
    # elongHighFlag = dataset[ dataset[ 'elong' ] >= 4 ]

    # filtering loop for individual attributes
    filteredDataset = dataset
    emptyFlag = False
    continueFlag = ( featFltr != 'n' ) # will not start if no featFltr was given at start

    while ( continueFlag and( not emptyFlag ) ):
        # filterInput = input( "Enter feature to filter by( 'n' if None ): \n" )
        # continueFlag = ( filterInput != 'n' )

        if ( continueFlag ):
            filterHighLimit = int( input( "Data >  " ) )
            filterLowLimit = int( input( "Data <  " ) )

            prevSet = filteredDataset
            filteredDataset = filteredDataset.loc[ 
                ( filteredDataset[ filterInput ] > filterHighLimit ) &
                ( filteredDataset[ filterInput ] < filterLowLimit ) ]
            emptyFlag = filteredDataset.empty

            if ( not emptyFlag ):
                print( filteredDataset )

            else:
                print( "This returns an empty Data Set " )

                resetInput = int( input( 
                    "0 to continue, 1 to reset last filter, 2 to reset all filters" ) )

                if ( resetInput == 1 ):
                    filteredDataset = prevSet
                    emptyFlag = False
                    continueFlag = True

                if ( resetInput == 2 ):
                    filteredDataset = dataset
                    emptyFlag = False
                    continueFlag = True

    # prompt for inspecting specific asteroid after running program on multiple
    # if ( input( "Inspect Specific Asteroid( y/n ): " ) == "y" ):
        # viewOne( )
    
########################################################################################
### VIEWONE function
### Inputs: none
### Returns: none
### Use: Allows user to specific the name ( numerical 'ssnamenr' from database ) of an
### asteroid they wish to analyze more in depth than in runProgram. 
########################################################################################
def viewOne( astArgs, exportFlg, exportArgs, fltrType, fltrLvl, plots ):
    astName = astArgs[ 0 ]
    featFltr = astArgs[ 1 ]
    lB = astArgs[ 2 ]
    uB = astArgs[ 3 ]
    fltr = [ fltrType, fltrLvl ]
    asteroid = pd.DataFrame( mag18Database.find( { "ssnamenr": int( astName ) } ).sort( "jd" ) )

    # menu2Dict = { 0: 'Inspect Asteroid ' + str( astName ) + ":",
    #              1: 'View asteroid data',
    #              2: 'Save/download asteroid data',
    #              3: 'View Data by Attribute',
    #              4: 'Return to Main Menu',
    #              5: 'Quit' }
    # menu2Choice = 0
    
    # while menu2Choice != 4 or menu2Choice != 5:
    #     menu.display( menu2Dict )
    #     menu2Choice = int( input( ) )
    #     clear( 2 )

    menu2Choice = 1 # hardcoded for testing purposes - move this to shell later!
    
    if menu2Choice == 1:
        print( "Asteroid " + str( astName ) + " Stats:\n" )
        astSigmaMatrix = np.zeros( [ 1, numFeatures + 2 ] )
        obsData = [ ]
        sigmaMatrix, obsData, outliers = fillSigmaMatrix( astName, asteroid, astSigmaMatrix, fltr, True, plots, exportFlg )
        if len( sigmaMatrix ) == 0:
            print( "ERROR: Your chosen filter level yielded an empty matrix!" )
            antIDS.clear( )
            # viewOne( )
            # THIS FUNCTIONALITY IS DEPRECATED

        #breakpoint( )
        table = formatDataTable( sigmaMatrix, antIDS, [ astName ], 1, numFeatures )
        astRating = float( table[ "Rating" ] )

        # reset antIDS for reruns of program
        ### ERROR: This works for the most part, but still errors out upon quitting
        ### the program - not sure why
        antIDS.clear( )

        print( table.transpose( ) )
        print( "\n\n" )

        displayAll = False # hardcoded for testing purposes - move this to shell later! 
        if ( displayAll ):
        # if ( input( "Display all data for asteroid " + str( astName ) + "? ( y/n )\n" ) != 'n' ):
            print( "\n\n" )
            print( "Asteroid Rating: " + str( round( astRating, 2 ) ) + "%" )
            print( "\n" )

            print( "ELONG:" )
            print( "    Sigma: ............. " + str( float( table[ "elong" ] ) ) )
            print( "    Outlier Value: ..... " + str( outliers[ 0 ] ) )
            print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "elong" ] ) ) )
            print( "    Mean: .............. " + str( stat.mean( asteroid[ "elong" ] ) ) )
            print( "    JD: ................ " + str( int( obsData[ 0 ] ) ) )
            print( "    ZTF ID: ............ " + str( antIDS[ 0 ] ) )

            print( "RB:" )
            print( "    Sigma: ............. " + str( float( table[ "rb" ] ) ) )
            print( "    Outlier Value: ..... " + str( outliers[ 1 ] ) )
            print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "rb" ] ) ) )
            print( "    Mean: .............. " + str( stat.mean( asteroid[ "rb" ] ) ) )
            print( "    JD: ................ " + str( int( obsData[ 1 ] ) ) )
            print( "    ZTF ID: ............ " + str( antIDS[ 1 ] ) )            

            print( "H:" )
            print( "    Sigma: ............. " + str( float( table[ "H" ] ) ) )
            print( "    Outlier Value: ..... " + str( outliers[ 2 ] ) )
            print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "H" ] ) ) )
            print( "    Mean: .............. " + str( stat.mean( asteroid[ "H" ] ) ) ) 
            print( "    JD: ................ " + str( int( obsData[ 2 ] ) ) )
            print( "    ZTF ID: ............ " + str( antIDS[ 2 ] ) )            

            print( "MAG18:" )
            print( "    Sigma: ............. " + str( float( table[ "mag18omag8" ] ) ) )
            print( "    Outlier Value: ..... " + str( outliers[ 3 ] ) )
            print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "mag18omag8" ] ) ) )
            print( "    Mean: .............. " + str( stat.mean( asteroid[ "mag18omag8" ] ) ) )
            print( "    JD: ................ " + str( int( obsData[ 3 ] ) ) )
            print( "    ZTF ID: ............ " + str( antIDS[ 3 ] ) )                            
            print( "\n\n" )
            print( asteroid[ [ "jd", "elong", "H", "rb", "mag18omag8", "fid" ] ] )



        ###### NEW PLOTTING ######
        if plots:
            plot3Das2D( astName, asteroid['rb'],
                        asteroid['elong'],
                        asteroid['mag18omag8'],
                        "rb", "elong", "mag18omag8",
                        asteroid, exportFlg )

            plot3Dand2D( astName, asteroid['rb'],
                        asteroid['elong'],
                        asteroid['mag18omag8'],
                        "rb", "elong", "mag18omag8",
                        asteroid, exportFlg )

        # call function to print all observations of
        # this asteroid
        getAllObs( astName, asteroid, exportFlg )

        # plot3D( astName, asteroid['rb'],
        #             asteroid['elong'],
        #             asteroid['mag18omag8'],
        #             "rb", "elong",
        #             "mag18omag8", exportFlg )


            
        # setup for printing all plots later...
        astDataFigs, ( ( plt3, plt2 ), ( plt1, plt4 ) ) = plt.subplots( 2, 2, figsize=( 15,15 ) )
        astDataFigs.suptitle( "Asteroid " + str( astName ) )

        # rb vs. Julian Date scatterplot
        plt1.scatter( asteroid[ "jd" ], asteroid[ 'rb' ], color = 'deeppink' )
        outlierRB = ( asteroid[ asteroid[ "rb" ] == outliers[ 1 ] ] ).index
        plt1.scatter( asteroid[ "jd" ][ outlierRB ],
                     asteroid[ "rb" ][ outlierRB ],
                     color = 'white',
                     marker = "." )
        plt1.annotate( '%s' % obsData[ 1 ],
                      xy = ( asteroid[ "jd" ][ outlierRB ],
                            asteroid[ "rb" ][ outlierRB ] ) )
        plt1.set( xlabel = "jd", ylabel = "rb" )

        # mag18omag8 vs. Julian Date scatterplot
        plt2.scatter( asteroid[ "jd" ], asteroid[ 'mag18omag8' ], color = 'gold' )
        outlierMAG18 = ( asteroid[ asteroid[ "mag18omag8" ] == outliers[ 3 ] ] ).index
        plt2.scatter( asteroid[ "jd" ][ outlierMAG18 ],
                     asteroid[ "mag18omag8" ][ outlierMAG18 ],
                     color = 'white',
                     marker = "." )
        plt2.annotate( '%s' % obsData[ 3 ],
                      xy = ( asteroid[ "jd" ][ outlierMAG18 ],
                            asteroid[ "mag18omag8" ][ outlierMAG18 ] ) )
        plt2.set( xlabel = "jd", ylabel = "mag18omag8" )

        # elong vs. Julian Date scatterplot
        plt3.scatter( asteroid[ "jd" ], asteroid[ 'elong' ], color = 'blue' )
        outlierELONG = ( asteroid[ asteroid[ "elong" ] == outliers[ 0 ] ] ).index
        plt3.scatter( asteroid[ "jd" ][ outlierELONG ],
                     asteroid[ "elong" ][ outlierELONG ],
                     color = "white",
                     marker = "." )
        plt3.annotate( '%s' % obsData[ 0 ],
                      xy = ( asteroid[ "jd" ][ outlierELONG ],
                            asteroid[ "elong" ][ outlierELONG ] ) )
        plt3.set( xlabel = "jd", ylabel = "elong" )

        # H vs. Julian Date scatterplot
        # ERROR HERE!!!!!!!!!! - not showing up, may be reasoning for error in saving file
        fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 1 ) ]
        # print(fidFiltered)
        plt4.scatter( fidFiltered[ "jd" ], fidFiltered[ 'H' ], color = 'green' )
        outlierH = ( asteroid[ asteroid[ "H" ] == outliers[ 2 ] ] ).index
        # print(outlierH)
        fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 2 ) ]
        # print(fidFiltered)
        plt4.scatter( fidFiltered[ "jd" ], fidFiltered[ 'H' ], color = 'red' )
        plt4.scatter( asteroid[ "jd" ][ outlierH ],
                     asteroid[ "H" ][ outlierH ],
                     color = "white",
                     marker = "." )
        plt4.annotate( '%s' % obsData[ 2 ],
                      xy = ( asteroid[ "jd" ][ outlierH ],
                            asteroid[ "H" ][ outlierH ] ) )
        plt4.set( xlabel = "jd", ylabel = "H" )

        
        # if plots:
        #     savefile = "ast" + str( astName ) + "-dataplots.png"
        #     if exportFlg:
        #         savefile = str( exportArgs[ 1 ] ) + "-dataplots.png"
                
        #     astDataFigs.savefig( savefile )

        ### TODO: add prompt for showing or exporting data
        # astDataFigs.show( )

        if ( plots ):
            astDataAllFigs, ( ( plt5, plt6, plt7 ),
                             ( plt8, plt9, plt10 ) ) = plt.subplots( 2, 3, figsize=( 15,15 ) )
            astDataAllFigs.suptitle( "Asteroid " + str( astName ) )

            # mag18omag8 vs. rb scatterplot
            plt5.scatter( asteroid[ "mag18omag8" ],
                         asteroid[ 'rb' ],
                         color = 'darkorange' )
            plt5.set( xlabel = "mag18omag8",
                     ylabel = "rb",
                     title = "mag18omag8 vs. rb" )

            # mag18omag8 vs. elong scatterplot
            plt6.scatter( asteroid[ "mag18omag8" ],
                         asteroid[ 'elong' ],
                         color = 'mediumaquamarine' )
            plt6.set( xlabel = "mag18omag8",
                     ylabel = "elong",
                     title = "mag18omag8 vs. elong" )

            # mag18omag8 vs. H scatterplot
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 1 ) ]
            plt7.scatter( fidFiltered[ "mag18omag8" ],
                         fidFiltered[ 'H' ],
                         color = 'limegreen' )
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 2 ) ]
            plt7.scatter( fidFiltered[ "mag18omag8" ],
                         fidFiltered[ 'H' ],
                         color = 'tomato' )
            plt7.set( xlabel = "mag18omag8",
                     ylabel = "H",
                     title = "mag18omag8 vs. H" )

            # rb vs. elong scatterplot
            plt8.scatter( asteroid[ "rb" ],
                         asteroid[ 'elong' ],
                         color = 'forestgreen' )
            plt8.set( xlabel = "rb",
                     ylabel = "elong",
                     title = "rb vs. elong" )

            # rb vs. H scatterplot
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 1 ) ]
            plt9.scatter( fidFiltered[ "rb" ],
                         fidFiltered[ 'H' ],
                         color = 'darkgreen' )
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 2 ) ]
            plt9.scatter( fidFiltered[ "rb" ],
                         fidFiltered[ 'H' ],
                         color = 'darkred' )
            plt9.set( xlabel = "rb",
                     ylabel = "H",
                     title = "rb vs. H" )

            # elong vs. H scatterplot
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 1 ) ]
            plt10.scatter( fidFiltered[ "elong" ],
                          fidFiltered[ 'H' ],
                          color = 'seagreen' )
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 2 ) ]
            plt10.scatter( fidFiltered[ "elong" ],
                          fidFiltered[ 'H' ],
                          color = 'firebrick' )
            plt10.set( xlabel = "elong",
                      ylabel = "H",
                      title = "elong vs. H" )

            # if ( input( "Export all plots as .png ( y/n )?" ) ):
            # if plots:
            #     savefileAll = "ast" + str( astName ) + "-alldataplots.png"
            #     if exportFlg:
            #         savefileAll = str( exportArgs[ 1 ] ) + "-alldataplots.png"

            #     astDataFigs.savefig( savefileAll )

            ### TODO: Add prompt for showing or exporting plots
            # when the above code is fixed, these two statements will be in the else for the exportFlg
            # plt.show(block=True)
            # astDataAllFigs.show( )

    elif menu2Choice == 2:
        print( "TODO: save data" )
    elif menu2Choice == 3:
        #filter by attribute
        attr = featFltr
        # if attr == 'l':
        #     print( attrList )
        #     attr = input( 
        #         "Attribute to filter by ( press 'l' for list of available attributes ): " )

        # attrData = input( "Desired attribute value: " )
        attrData = 0 # hardcoded - this part is kinda outdated too...

        # converting datatype as necessary
        if attr == "id":
            attrData = str( attrData )
        else:
            attrData = float( attrData )

        filteredData  = asteroid.loc[ ( asteroid[ attr ] == attrData ) ]

        print( filteredData[ [ "ssnamenr", "jd", "elong", "rb", "H", "mag18omag8", "id" ] ] )

        if attr == "jd":
            # print new plot with vertical line on plot for viewing one night specifically
            # astDataFigs.show( )
            jdAtObs = [ ]
            obsData = asteroid.loc[ ( asteroid[ attr ] == attrData ) ]
            for obs in range( len( obsData[ "jd" ] ) ):
                jdAtObs.append( float( obsData[ "jd" ].iloc[ obs ] ) )

            for obs in range( len( jdAtObs ) ):
                # rb line
                plt1.axvline( x = jdAtObs[ obs ], color = 'pink' )
                # mag18 line
                plt2.axvline( x = jdAtObs[ obs ], color = 'khaki' )
                # elong line
                plt3.axvline( x = jdAtObs[ obs ], color = 'skyblue' )
                # H line
                plt4.axvline( x = jdAtObs[ obs ], color = 'palegreen' )

            astDataFigs.show( )


    elif menu2Choice == 4:
        main( )
    else:
        pass



########################################################################################
### PLOTTING FUNCTIONS
### Use: plots specified data in 1D, 2D or 3D plots
########################################################################################
def plot1D():
    pass
    
def plot2D( astName, xdata, ydata,
            data, xname, yname, export ):
    plt.title( "Asteroid " + str( astName ) )
    plt.scatter( xdata, ydata, color = 'deeppink' )
    plt.xlabel( xname )
    plt.ylabel( yname )

    if export:
        fig.savefig( str(astName) + "plots2D.png" )
    else:
        cursor = mplcursors.cursor( hover=True )
        cursor.connect( "add", lambda sel: sel.annotation.set_text( data[ "jd" ].iloc[ sel.index ] ) )
        plt.show( block = True )
        plt.show()

def plot3D( astName, xdata, ydata, zdata,
            xname, yname, zname, export ):
    
    # fig, ax = plt.subplots( projection='3d' )
    # fig.suptitle( "Asteroid " + str( astName ) )
    # ax.scatter( xdata, ydata, zdata,
    #             color = 'deeppink' )
    # ax.set_xlabel( xname )
    # ax.set_ylabel( yname )
    # ax.set_zlabel( zname )

    # if export:
    #     fig.savefig( str(astName) + "plot3D.png" )
    # else:
    #     plt.show( block=True )
    #     fig.show()

    pass
    

def plot3Das2D( astName, xdata, ydata, zdata,
                    xname, yname, zname, data, export ):

    fig, ax = plt.subplots( 3, layout="constrained" )
    fig.suptitle( "Asteroid " + str( astName ) )

    # first subplot
    ax[0].scatter( xdata, ydata, color="deeppink" )
    ax[0].set_xlabel( xname )
    ax[0].set_ylabel( yname )

    # second subplot
    ax[1].scatter( xdata, zdata, color="slateblue" )
    ax[1].set_xlabel( xname )
    ax[1].set_ylabel( zname )

    # third subplot
    ax[2].scatter( zdata, ydata, color="teal" )
    ax[2].set_ylabel( yname )
    ax[2].set_xlabel( zname )


    if export:
        fig.savefig( str(astName) + "plots3-2D.png" )
    else:
        cursor = mplcursors.cursor( hover=True )
        cursor.connect( "add", lambda sel: sel.annotation.set_text( data[ "jd" ].iloc[ sel.index ] ) )
        plt.show( block=True )
        # fig.show()
        
    
    
def plot3Dand2D( astName, xdata, ydata, zdata,
                    xname, yname, zname, data, export ):

    # export = False
    
    fig = plt.figure( figsize=(12, 8) )
    gs = gridspec.GridSpec( 1, 2, width_ratios=[ 1, 1.5 ] )
    fig.suptitle( "Asteroid " + str( astName ) )


    ax3d = fig.add_subplot( gs[0,0], projection='3d' )
    ax3d.scatter( xdata, ydata, zdata,
                  color = 'darkorchid' )
    ax3d.set_xlabel( xname )
    ax3d.set_ylabel( yname )
    ax3d.set_zlabel( zname )

    gs_right = gridspec.GridSpecFromSubplotSpec( 3, 1, subplot_spec=gs[0,1],
                                        height_ratios=[1, 1, 1], hspace=0.4 )

    ax2d1 = fig.add_subplot( gs_right[0] )
    ax2d2 = fig.add_subplot( gs_right[1] )
    ax2d3 = fig.add_subplot( gs_right[2] )

    gs.update( wspace=0.4, hspace=0.4 )

    ax2d1.scatter( xdata, ydata, color = 'deeppink' )
    ax2d1.set_xlabel( xname )
    ax2d1.set_ylabel( yname )

    ax2d2.scatter( xdata, zdata, color = 'slateblue' )
    ax2d2.set_xlabel( xname )
    ax2d2.set_ylabel( zname )

    ax2d3.scatter( zdata, ydata, color = 'teal' )
    ax2d3.set_xlabel( zname )
    ax2d3.set_ylabel( yname )

    if export:
        fig.savefig( str(astName) + "plots3D+2D.png" )
    else:
        cursor = mplcursors.cursor( hover=True )
        cursor.connect( "add", lambda sel: sel.annotation.set_text( data[ "jd" ].iloc[ sel.index ] ) )
        plt.show( block=True )
        fig.show()
        
    # pass


    

########################################################################################
### MAIN PROGRAM:
### Inputs: none
### Returns: none
### Use: provides SNAPS menu for navigating through multiple options, including
### run program, view specific asteroid, help, and quit. Allows user to view, analyze,
### and export data on asteroids pulled from the mongo database.
########################################################################################
def main( ):
    maxIn = int( sys.argv[ 1 ] )
    offset = int( sys.argv[ 2 ] )
    fltrType = int( sys.argv[ 3 ] )
    fltrLvl = int( sys.argv[ 4 ] )
    plots = sys.argv[ 5 ]
    exportFlg = sys.argv[ 6 ]
    # wantedAttrs = sys.argv[ 7 ]
    
    # defaults of these for the versions that don't set them themselves
    exportArgs = [2, ""]
    astArgs = [0, 'n', 0, 0]

    # annoying handling of boolean inputs - may change this later
    exportFlg = [ False, True ][ exportFlg.lower()[0] == "t" ]
    plots = [ False, True ][ plots.lower()[0] == "t" ]

    print(exportFlg)
    if len(sys.argv) <= 7:
        pass
        # exportArgs = [ 2, "" ]
        # astArgs = [ 0, 'n', 0, 0 ]
    else:
        help()
        if exportFlg:
            exportArgs = [ int( sys.argv[ 7 ] ),
                           sys.argv[ 8 ] ]
            if maxIn == 1:
                astArgs = [ int( sys.argv[ 9 ] ),
                            sys.argv[ 10 ],
                            int( sys.argv[ 11 ] ),
                            int( sys.argv[ 12 ] ) ]
        else:
            astArgs = [ int( sys.argv[ 7 ] ),
                        sys.argv[ 8 ],
                        int( sys.argv[ 9 ] ),
                        int( sys.argv[ 10 ] ) ]
    
    if maxIn == 1:
        viewOne( astArgs, exportFlg, exportArgs, fltrType, fltrLvl, plots )
    else:
        runProgram( maxIn, offset, exportFlg, exportArgs, fltrType, fltrLvl, plots )

## Run the program #####################################################################
main( )
leave( )
