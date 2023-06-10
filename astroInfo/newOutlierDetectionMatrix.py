#########################################################################################
### Program: SNAPS Anomaly Detection for Individual Asteroids
### Programmer: Savannah Chappus
### Last Update: 6.8.2023
#########################################################################################

## IMPORTS ##############################################################################
from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import statistics as stat
import matplotlib.pyplot as plt
import numpy as np
import random as rand
import pdb
# custom py file imports
import asteroidMenuClass as menu

## MONGO CONNECTION #####################################################################
# in the connection string below, format is:
# mongodb://YOURUSERNAME:YOURPASSWORD@YOURCOMPUTER.computers.nau.edu:27017
dest = "mongodb://schappus:unicornsSUM22@cmp4818.computers.nau.edu:27017"
client = MongoClient( dest )
db = client.ztf
mag18Data = db[ 'mag18o8' ] # all asteroids with mag18o8 data
asteroid_data = db[ 'asteroids_all' ]

## GLOBAL VARS ##########################################################################
useMsg = "How this program works: \n\
The program accepts a number of asteroids to observe and value for where in the data \n\
to start. Then, it pulls data for each individual asteroid, and finds the most \n\
outlying point (min or max ) and calculates the number of standard deviations away \n\
from the mean that point is. If it is above the mean, the number of sigmas is stored \n\
in the matrix. If it is below the mean, the negative number of sigmas is stored in \n\
the matrix. The final columns in the matrix are a row sum (of sigma multipliers ) and \n\
a row sum of the absolute value of each matrix entry. The program then allows users \n\
to filter the data by features at specific user-given values. Then users can view \n\
histograms of all the sigma data and scatterplots for individual asteroids."

offset = 0 # for shifting data scope
attrList = "ssnamenr, jd, fid, pid, diffmaglim, ra, dec, magpsf, sigmapsf, \
chipsf, magap, sigmagap, magapbig, sigmagapbig, distnr, magnr, fwhm, elong, rb, \
ssdistnr, ssmagnr, id, night, phaseangle, obsdist, heliodist, H, ltc, mag18omag8"

# Top 4 Attributes of Interest:
# mag180mag8 : sigma value for difference in 18" aperture vs 8" aperture photos
# elong: elong val > 1 means oblong object, if this changes it's interesting
# rb (real-bogus ): value to represent the "validity" or "trustworthiness" of the
# collected data
# H: another measurement of brightness
wantedAttrs = [ "elong", "rb", "H", "mag18omag8" ] # attributes we want to look at
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

# help: takes no inputs, prints the help message
def help( ):
    print( useMsg )
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
def getFilter( ):
    typeDict = { 0: 'Select Filter Type:',
                1: 'By number of outlier occurences per night',
                2: 'By overall asteroid anomaly rating',
                3: 'By weighted attribute filtering',
                4: 'None' }
    menu.display( typeDict )
    fltrType = int( input( ) )
    if fltrType == 1:
        clear( 2 )
        levelDict = { 0: 'Select Filter Intensity:',
                1: 'None',
                2: 'more than 2 outliers per night',
                3: 'more than 3 outliers per night',
                4: 'exactly 4 outliers per night' }
        menu.display( levelDict )
        fltrLvl = int( input( ) )
    elif fltrType == 2:
        fltrLvl = float( input( 
            "Rating Filter (ex. enter '90' for 90% chance or more of anomaly ): " ) )
    elif fltrType == 3:
        # TODO: add weighted attribute filtering
        print( "Defaulting to no filter..." )
        fltrLvl = 0
    else:
        fltrLvl = 0
        
    return [ fltrType, fltrLvl ]

# normValue: takes element to normalize, min, and max values and normalizes to [ 0,1 ]
def normValue( value, minVal, maxVal ):
    normVal = ( value - minVal )/( maxVal - minVal )
    return normVal

# normDataset: takes in dataset (need not be single-column ) and normalizes
# to range [ 0,1 ]
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

# rating: takes in data, night, outliers gives anomaly rating for individual night
def getNightRating( data, night ):
    ratings = [ ]
    for attr in wantedAttrs:
        sortedData = data.sort_values( by = [ attr ] )
        minVal = sortedData[ attr ].iloc[ 0 ]
        maxVal = sortedData[ attr ].iloc[ len( sortedData ) - 1 ]
        nightIdx = sortedData[ ( sortedData[ "night" ] == night ) ].index
        normVal = normValue( sortedData[ attr ][ nightIdx ], minVal, maxVal )
        for val in normVal:
            if val < 0:
                pdb.set_trace( )
            if attr in [ "elong", "mag18omag8" ]:
                ratings.append( float( val ) )
            else:
                ratings.append( float( 1 - val ) )

    nightRating = stat.mean( ratings ) * 100
    return nightRating

# getAstRating: takes in asteroid data (in dataframe ) and collects night ratings for
# all observations and averages them to get the overall asteroid rating
def getAstRating( astData ):
    nightRatings = [ ]
    for night in astData[ "night" ]:
        nightRating = getNightRating( astData, night )
        nightRatings.append( nightRating )
    astRating = stat.mean( nightRatings )
    return astRating
    
# formatDataTable: takes in sigma matrix, antares IDs array, asteroid name array,
# number of asteroids, and number of features and formats the sigma matrix into
# a more reader-friendly table with headers
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
def fillSigmaMatrix( name, asteroid, sigmaMatrix, fltr, outFlag ):
    attrData = [ ]
    nightData = [ ]
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
            print( ( name + " is the object causing error" ), e )
            
        # grab weight for feature
        attr_weight = weightDict[ feature ]

        # sort specific asteroid data by feature & normalize
        dataSortedByFeature = pd.DataFrame( 
            mag18Data.find( { "ssnamenr": int( name ) } ).sort( feature ) )
        normData = normDataset( dataSortedByFeature )

        # calculate min, max, and ranges for highSigma and lowSigma values
        minIndex = 0
        maxIndex = len( dataSortedByFeature ) - 1

        minVal = ( dataSortedByFeature[ feature ][ minIndex ] )
        maxVal = ( dataSortedByFeature[ feature ][ maxIndex ] )

        upperRange = maxVal - obj_mean
        lowerRange = obj_mean - minVal

        highSigma = upperRange / obj_stdev
        lowSigma = lowerRange / obj_stdev

        featNightDF = dataSortedByFeature[ [ feature, "night" ] ]

        
        # add data to sigmaMatrix
        if ( highSigma > lowSigma ):
            # night of observation
            night = dataSortedByFeature[ "night" ][ maxIndex ]

            rowSum += highSigma * attr_weight
            absRowSum += highSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append( dataSortedByFeature[ 'id' ][ maxIndex ] )
            attrData.append( highSigma * attr_weight )

            # store outliers
            outliers.append( maxVal )

            # calculations for filtering ( opt 2 )
            outlierNorms.append( normData[ feature ][ maxIndex ] )

        else:
            night = dataSortedByFeature[ "night" ][ minIndex ]
            rowSum += -lowSigma * attr_weight
            absRowSum += lowSigma * attr_weight

            # keep track of ant id with specific observation
            antIDS.append( dataSortedByFeature[ 'id' ][ minIndex ] )
            attrData.append( -lowSigma * attr_weight )

            # store outliers
            outliers.append( minVal )

            # calculations for filtering ( opt 2 )
            outlierNorms.append( normData[ feature ][ minIndex ] )

        # update attribute count
        attr_ct += 1
        # add night of sigma value to list
        nightData.append( night )

    rowAttrs = [ ]
    numZeros = 0

    #### FILTERING DATA ####
    if fltrType == 1:
        # Option 1: filter by number of times outliers occur on specific night
        for night in range( len( nightData ) ):
            if nightData.count( nightData[ night ] ) >= fltrLevel:
                rowAttrs.append( attrData[ night ] )
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
        astRating = getAstRating( asteroid )
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
        return ( sigmaMatrix, nightData, outliers )

    return ( sigmaMatrix, nightData )

########################################################################################
### RUNPROGRAM function
### Inputs: none
### Returns: none
### Use: runs the program from menu option 1. Lets users view as many asteroids
### as desired from any starting point in the data, then computes and fills the sigma
### matrix and runs data analytics on the results.
########################################################################################
def runProgram( ):
    # total num of asteroids we want to look at
    maxIn = int( input( "How many asteroids do you want to look at( -1 if all ): " ) )

    if ( maxIn < 0 ) :
        maxIn = asteroid_data.count( )
        print( "WARNING: This will run all 32k+ asteroids through the program." )
        print( "This process may take several hours depending on your system.\n" )
        allAstMenu = { 0: 'What would you like to do?',
                1: 'Run and display output on screen',
                2: 'Run and export output to file',
                3: 'Cancel' }
        menu.display( allAstMenu )
        allAstDecision = int( input( ) )
        if allAstDecision == 3:
            runProgram( )
        if allAstDecision == 2:
            exportFlg = 'y'
             
    offset = int( input( "Where to start in data:( -1 if random ):  " ) )
    
    if ( offset < 0 and maxIn < asteroid_data.count( ) ):
        offset = rand.randint( 0, asteroid_data.count( ) - maxIn - 1 )

    exportFlg = input( "Would you like to export the results ( y/n )? " )

    if exportFlg == 'y':
        fileType =  int( input( "Export as \n 1. .html \n 2. .csv \n" ) )
        filename = input( "filename: " )

    fltr = getFilter( )
        
    # num of asteroids we have looked at 
    ast_ct = 0

    # get all asteroid names
    asteroidNames = pd.DataFrame( asteroid_data.find( {},{ '_id': 0, 'ssnamenr' : 1 } ) )

    #Sigma Matrix
    extraCols = 3 # for: rowSum, absRowSum, asteroidRating
    sigmaMatrix = np.zeros( [ maxIn, numFeatures + extraCols ] )

    # Loop through our collection of names
    while ( ast_ct < maxIn and ast_ct < len( asteroidNames ) ):
        # create temporary row variable to hold asteroid data for appending at the end
        attrData = [ ]
        nightData = [ ]

        # grab asteroid name
        name = asteroidNames[ "ssnamenr" ][ ast_ct + offset ]

        # reset attributes looked at
        attr_ct = 0

        # sort specific asteroid data by Julian Date
        asteroid = pd.DataFrame( mag18Data.find( { "ssnamenr": int( name ) } ).sort( "jd" ) )
        attrData, nightData = fillSigmaMatrix( name, asteroid, sigmaMatrix, fltr, False )
        
        if len( attrData ) != 0:
            sigmaMatrix[ ast_ct ] = attrData

        # update asteroid count
        ast_ct += 1

    # Reset arrays for rerunning program
    nameArray = [ ]
    listNames = [ ]
    idArray = [ ]
        
    # Formatting data structures
    nameArray = np.array( asteroidNames[ 'ssnamenr' ] )[ offset: offset + ast_ct ]

    dataset = formatDataTable( sigmaMatrix, antIDS, nameArray, maxIn, numFeatures )

    # clear antIDS for next use
    antIDS.clear( )

    # EXPORT
    # drop all rows in data where zeros are present ( from filters )
    ### WARNING: I'm not sure if this works with the new filter system
    ### TODO: check if it works and fix if it doesn't
    newData = dataset.drop( 
        dataset.query( "rb==0 and elong==0 and H==0 and mag18omag8==0" ).index )
    if exportFlg == 'y':
        exportFile( fileType, filename, newData )
    else:
        print( newData )
    
    # first printout of relevant asteroid data
    if ( input( "Look at total data histogram ( y/n ): " ) == 'y' ):
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
    continueFlag = True

    while ( continueFlag and( not emptyFlag ) ):
        filterInput = input( "Enter feature to filter by( 'n' if None ): \n" )
        continueFlag = ( filterInput != 'n' )

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
    if ( input( "Inspect Specific Asteroid( y/n ): " ) == "y" ):
        viewOne( )
    
########################################################################################
### VIEWONE function
### Inputs: none
### Returns: none
### Use: Allows user to specific the name ( numerical 'ssnamenr' from database ) of an
### asteroid they wish to analyze more in depth than in runProgram. 
########################################################################################
def viewOne( ):
    astName = input( "Asteroid Name:\n" )
    clear( 2 )
    asteroid = pd.DataFrame( mag18Data.find( { "ssnamenr": int( astName ) } ).sort( "jd" ) )

    menu2Dict = { 0: 'Inspect Asteroid ' + str( astName ) + ":",
                 1: 'View asteroid data',
                 2: 'Save/download asteroid data',
                 3: 'View Data by Attribute',
                 4: 'Return to Main Menu',
                 5: 'Quit' }
    menu2Choice = 0
    
    while menu2Choice != 4 or menu2Choice != 5:
        menu.display( menu2Dict )
        menu2Choice = int( input( ) )
        clear( 2 )
        if menu2Choice == 1:
            fltr = getFilter( )
            print( "Asteroid " + astName + " Stats:\n" )
            astSigmaMatrix = np.zeros( [ 1, numFeatures + 2 ] )
            nightData = [ ]
            sigmaMatrix, nightData, outliers = fillSigmaMatrix( astName,asteroid,
                                                               astSigmaMatrix,
                                                               fltr, True )
            if len( sigmaMatrix ) == 0:
                print( "ERROR: Your chosen filter level yielded an empty matrix!" )
                antIDS.clear( )
                viewOne( )

            #breakpoint( )
            table = formatDataTable( sigmaMatrix, antIDS, [ astName ], 1, numFeatures )
            astRating = float( table[ "Rating" ] )

            # reset antIDS for reruns of program
            ### ERROR: This works for the most part, but still errors out upon quitting
            ### the program - not sure why
            antIDS.clear( )

            print( table.transpose( ) )
            print( "\n\n" )

            if ( input( "Display all data for asteroid " + astName + "? ( y/n )\n" ) != 'n' ):
                print( "\n\n" )
                print( "Asteroid Rating: " + str( round( astRating, 2 ) ) + "%" )
                print( "\n" )
                
                print( "ELONG:" )
                print( "    Sigma: ............. " + str( float( table[ "elong" ] ) ) )
                print( "    Outlier Value: ..... " + str( outliers[ 0 ] ) )
                print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "elong" ] ) ) )
                print( "    Mean: .............. " + str( stat.mean( asteroid[ "elong" ] ) ) )
                print( "    Night: ............. " + str( int( nightData[ 0 ] ) ) )
                print( "    ZTF ID: ............ " + str( antIDS[ 0 ] ) )

                print( "RB:" )
                print( "    Sigma: ............. " + str( float( table[ "rb" ] ) ) )
                print( "    Outlier Value: ..... " + str( outliers[ 1 ] ) )
                print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "rb" ] ) ) )
                print( "    Mean: .............. " + str( stat.mean( asteroid[ "rb" ] ) ) )
                print( "    Night: ............. " + str( int( nightData[ 1 ] ) ) )
                print( "    ZTF ID: ............ " + str( antIDS[ 1 ] ) )            

                print( "H:" )
                print( "    Sigma: ............. " + str( float( table[ "H" ] ) ) )
                print( "    Outlier Value: ..... " + str( outliers[ 2 ] ) )
                print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "H" ] ) ) )
                print( "    Mean: .............. " + str( stat.mean( asteroid[ "H" ] ) ) ) 
                print( "    Night: ............. " + str( int( nightData[ 2 ] ) ) )
                print( "    ZTF ID: ............ " + str( antIDS[ 2 ] ) )            

                print( "MAG18:" )
                print( "    Sigma: ............. " + str( float( table[ "mag18omag8" ] ) ) )
                print( "    Outlier Value: ..... " + str( outliers[ 3 ] ) )
                print( "    Std Dev: ........... " + str( stat.stdev( asteroid[ "mag18omag8" ] ) ) )
                print( "    Mean: .............. " + str( stat.mean( asteroid[ "mag18omag8" ] ) ) )
                print( "    Night: ............. " + str( int( nightData[ 3 ] ) ) )
                print( "    ZTF ID: ............ " + str( antIDS[ 3 ] ) )                            
                print( "\n\n" )
                print( asteroid[ [ "night", "elong", "H", "rb", "mag18omag8", "fid" ] ] )
            
            # setup for printing all plots later...
            astDataFigs, ( ( plt3, plt2 ), ( plt1, plt4 ) ) = plt.subplots( 2, 2, figsize=( 15,15 ) )
            astDataFigs.suptitle( "Asteroid " + astName )

            # rb vs. Julian Date scatterplot
            plt1.scatter( asteroid[ "jd" ], asteroid[ 'rb' ], color = 'deeppink' )
            outlierRB = ( asteroid[ asteroid[ "rb" ] == outliers[ 1 ] ] ).index
            plt1.scatter( asteroid[ "jd" ][ outlierRB ],
                         asteroid[ "rb" ][ outlierRB ],
                         color = 'white',
                         marker = "." )
            plt1.annotate( '%s' % nightData[ 1 ],
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
            plt2.annotate( '%s' % nightData[ 3 ],
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
            plt3.annotate( '%s' % nightData[ 0 ],
                          xy = ( asteroid[ "jd" ][ outlierELONG ],
                                asteroid[ "elong" ][ outlierELONG ] ) )
            plt3.set( xlabel = "jd", ylabel = "elong" )

            # H vs. Julian Date scatterplot
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 1 ) ]
            plt4.scatter( fidFiltered[ "jd" ], fidFiltered[ 'H' ], color = 'green' )
            outlierH = ( asteroid[ asteroid[ "H" ] == outliers[ 2 ] ] ).index
            fidFiltered = asteroid.loc[ ( asteroid[ "fid" ] == 2 ) ]
            plt4.scatter( fidFiltered[ "jd" ], fidFiltered[ 'H' ], color = 'red' )
            plt4.scatter( asteroid[ "jd" ][ outlierH ],
                         asteroid[ "H" ][ outlierH ],
                         color = "white",
                         marker = "." )
            plt4.annotate( '%s' % nightData[ 2 ],
                          xy = ( asteroid[ "jd" ][ outlierH ],
                                asteroid[ "H" ][ outlierH ] ) )
            plt4.set( xlabel = "jd", ylabel = "H" )

            if ( input( "Export plots as .png ( y/n )?" ) ):
                savefile = "ast-" + astName + "-dataplots.png"
                astDataFigs.savefig( savefile )

            ### TODO: add prompt for showing or exporting data
            #astDataFigs.show( )

            if ( input( "Show all plots? ( y/n ): " ) == 'y' ):
                astDataAllFigs, ( ( plt5, plt6, plt7 ),
                                 ( plt8, plt9, plt10 ) ) = plt.subplots( 2, 3, figsize=( 15,15 ) )
                astDataAllFigs.suptitle( "Asteroid " + astName )

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

                if ( input( "Export all plots as .png ( y/n )?" ) ):
                    savefileAll = "ast-" + astName + "-alldataplots.png"
                    astDataFigs.savefig( savefileAll )                    

                ### TODO: Add prompt for showing or exporting plots
                #astDataAllFigs.show( )

        elif menu2Choice == 2:
            print( "TODO: save data" )
        elif menu2Choice == 3:
            #filter by attribute
            attr = input( 
                "Attribute to filter by ( press 'l' for list of available attributes ): " )
            if attr == 'l':
                print( attrList )
                attr = input( 
                    "Attribute to filter by ( press 'l' for list of available attributes ): " )
                
            attrData = input( "Desired attribute value: " )

            # converting datatype as necessary
            if attr == "id":
                attrData = str( attrData )
            else:
                attrData = float( attrData )

            filteredData  = asteroid.loc[ ( asteroid[ attr ] == attrData ) ]
            
            print( filteredData[ [ "ssnamenr", "night", "elong", "rb", "H", "mag18omag8", "id" ] ] )

            if attr == "night":
                # print new plot with vertical line on plot for viewing one night specifically
                ### TODO: Add prompt for showing or exporting plots
                # astDataFigs.show( )
                jdAtNight = [ ]
                night = asteroid.loc[ ( asteroid[ attr ] == attrData ) ]
                for obs in range( len( night[ "jd" ] ) ):
                    jdAtNight.append( float( night[ "jd" ].iloc[ obs ] ) )

                for nght in range( len( jdAtNight ) ):
                    # rb line
                    plt1.axvline( x = jdAtNight[ nght ], color = 'pink' )
                    # mag18 line
                    plt2.axvline( x = jdAtNight[ nght ], color = 'khaki' )
                    # elong line
                    plt3.axvline( x = jdAtNight[ nght ], color = 'skyblue' )
                    # H line
                    plt4.axvline( x = jdAtNight[ nght ], color = 'palegreen' )

                astDataFigs.show( )
                

        elif menu2Choice == 4:
            main( )
            break
        else:
            break

########################################################################################
### MAIN PROGRAM:
### Inputs: none
### Returns: none
### Use: provides SNAPS menu for navigating through multiple options, including
### run program, view specific asteroid, help, and quit. Allows user to view, analyze,
### and export data on asteroids pulled from the mongo database.
########################################################################################
def main( ):
    clear( 20 )
    menuDict = { 0: 'SNAPS Menu',
                1: 'Run program',
                2: 'View specific asteroid',
                3: 'Help',
                4: 'Quit' }

    menuChoice = 0

    while menuChoice != 4:
        menu.display( menuDict )
        menuChoice = int( input( ) )
        clear( 2 )
        if menuChoice == 1:
            runProgram( )
        elif menuChoice == 2:
            viewOne( )
            break
        elif menuChoice == 3:
            help( )
        else:
            break

## Run the program #####################################################################
main( )
leave( )
