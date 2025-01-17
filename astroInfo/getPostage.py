# python script to download specific FITS files from the ALeRCE database:
# ALeRCE database link: https://alerce.online/
# Savannah Chappus
# 10.22.2024

import urllib.request as geturl
# import requests
import os
import sys
import pandas as pd
import functools as ft


def condenseCSV( urls, inFolder, outFile ):
    dfFull = pd.DataFrame()

    for url in urls:
        os.system("wget " + url)
        
    for fileName in os.listdir( inFolder ):
        if fileName.endswith( '.csv' ):
            filePath = os.path.join( inFolder, fileName )
            # Read the CSV file
            dfTemp = pd.read_csv( filePath )
            # dfs.append( dfTemp )
            dfFull = pd.concat( [dfFull, dfTemp] )

            
            dfFull.to_csv( '/home/nitefly/Desktop/CS453-S24/finalProj/out.csv', index=False )

            if fileName is not outFile:
                os.system( 'rm ' + fileName )

            

def readFile( filePath ):
    with open( filePath, 'r' ) as file:
        return file.readlines()


def fetchCSVs( urls ):
    for url in urls:
        os.system("wget " + url)


def getFileSizes( filePath ):
    sum = 0;
    for line in readFile( filePath ):
        val = line.strip()
        val = val.strip('K')
        sum += float(val)

    return sum

def main():
    if len( sys.argv ) > 1:
        fromFile = sys.argv[ 1 ] # enter as "True"
        filePath = "/home/sjc497/astroInfoResearch/astroInfo/ztfIds.txt"
        # might have user give the file path instead??
    else:
        fromFile = False
    #outFile = "SNOW4.csv"
    inFolder = "/home/sjc497/astroInfoResearch/astroInfo/stamps/"
    url = "https://www.ncei.noaa.gov/data/global-summary-of-the-year/access/"
    urlPrefix = "https://avro.alerce.online/get_stamp?oid="
    urlSpacer = "&candid="
    urlSuffix = "&type=difference&format=fits"
    #wantedCols = [ "STATION", "DATE", "LATITIUDE", "LONGITUDE",
    #               "ELEVATION", "DSND", "DSNW", "DX32", "DX70",
    #               "EMNT", "EMSD", "EMSN", "EMXT", "SNOW" ]
    urls = list()
    dfFull = pd.DataFrame()

    if fromFile:
        for line in readFile( filePath ):
            fileName = line.strip()
            print(fileName)
            ztfID, candID = line.split(', ')
            print(ztfID)
            print(candID)
            candID = candID.strip()
            newUrl = urlPrefix + ztfID + urlSpacer + candID + urlSuffix
            print(newUrl)

            os.system( "wget --remote-encoding=utf-8 " + newUrl )

    else:
        pass
        
        # filePath = os.path.join( inFolder, fileName )
        # Read the CSV file
        # dfTemp = pd.read_csv( filePath )
        # dfFull = pd.concat( [dfFull, dfTemp] ).reindex( columns = wantedCols )

        # dfFull.to_csv( "/scratch/sjc497/" + outFile, index=False )

        # os.system( 'rm ' + fileName )


main()
