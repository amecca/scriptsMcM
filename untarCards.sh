#!/bin/sh

######################################################
# Extracts the input cards from a Madgraph gridpack  #
#                                                    #
# Author: A. Mecca (amecca@cern.ch)                  #
######################################################

[ $# -eq 1 ] || { echo "Error: specify exactly 1 argument (path to tarball)" 2>&1 ; exit 1 ;}
tar -xa -f $1 InputCards || tar -xa -f $1 ./InputCards
