#!/usr/bin/python

'''
Author:  Collin McCarthy (cmccarthy@ucdavis.edu)
Last Update: 9/29/3013

About:  This script file converts BG/Q data into a Boxfish compatible format.
    For example, the user provides, via command line args, the source directory 
    path of the data folder kneighbor_1k, which contains four sub-directories 
    for different message sizes: size1, size64, size2048, size524288.  Each
    sub-directory is converted using the class DataDirConverter below.  Let
    each sub-directory contain the same format of runs:  there exist three
    different tilings, and 28 different runs per tiling.  Each run has a map
    file (i.e. map-1) and a data file (i.e. map-1.cnt) that are needed for the
    conversion.  Let the file names be as follows: first tiling, map-1 to 
    map-28, second tiling, mapT-1 to mapT-28, and third tiling, mapT2-1 to 
    mapT2-28.  Then the map names will be passed as six command line arguments 
    to this script file: map-1, map-28, mapT-1, mapT-28, mapT2-1, mapT2-28.
    Since there must be at least one tiling, with at least one run, a minimum
    of two map names will be passed as command line arguments, and if there is
    only one run they will be the same map name.  Note also that each 
    sub-directory must contain the same map names, otherwise this script
    must be called individually on each sub-directory to provide the map names.

    A DataDirConverter object will be created for each of the four 
    sub-directories.  The map names will be passed to the constructor, and
    DataDirConverter.convertDir() will convert all the runs in this
    sub-directory to the destination directory, with the same
    sub-directory structure as the source directory kneighbor_1k.
    
    DataDirConverter.convertDir() will call ConvertBGQDataRun() for each run, 
    using the run file name appended with _rank_map.yaml, _nodes.yaml, 
    _links.yaml and _meta.yaml.  

    If no sub-directories are provided, the script assumes the source directory
    contains all the runs with the given map names.  

    For command line arguments and more detailed information see README.txt.
'''

import os
import sys
from optparse import OptionParser
import numpy as np
import ConvertBGQDataRun

def convertAllData(source_dir, dest_dir, subdir_names, map_names, verbose, debug, print_help):
    ''' Converts all data for this source directory and destination directory.
    If source directory consists of sub directories, they are converted instead
    of the source directory itself.  Cannot convert both the source directory
    and sub directories, only one or the other.
    '''  

    if subdir_names == None: # only convert source_dir
        dirData = DataDirConverter(source_dir, dest_dir, map_names,
            verbose, debug)
        dirData.convertDir(print_help)
    else:
        for name in subdir_names:
            src_path = os.path.join(source_dir, name)
            dst_path = os.path.join(dest_dir, name)
            dirData = DataDirConverter(src_path, dst_path, map_names,
            verbose, debug)
            dirData.convertDir(print_help)

def parseCommandLine(parser):
    ''' Returns a list containing source directories, and destination directory.
    '''
    # when action is append or store, dest is printed in print_help as all uppercase
    #   so to make it look nice, use _ instead of camelCase
    parser.add_option("-s", "--subdir", dest="sub_dirs", action = "append",
            help="sub directories which hold data files")
    parser.add_option("-v", "--verbose", dest="verboseMode", action = "store_true",
        default=False, help = "print file name arguments passed to ConvertBGQDataRun.py")
    parser.add_option("-d", "--debug", dest="debugMode", action = "store_true",
        default=False, help = "print node and link data being output to .yaml files")
    options, args = parser.parse_args()

    if len(args) < 4:
        # instead of parser.error print own error statement, since we want
        #   the options to be printed (parser.error only prints usage)
        print '*** Fatal Error: Too few arguments. ***'
        parser.print_help() # to print options too
        sys.exit(1)

    if options.sub_dirs == None:
        if not os.path.exists(args[0]):
            # error if the source directory does not exist
            print '*** Fatal Error: Path name ' + os.path.abspath(args[0]) + ' does not exist. ***'
            parser.print_help()
            sys.exit(1)
    else:
        for path_name in options.sub_dirs:
            if not os.path.exists(os.path.join(args[0],path_name)):
                # error if the source directory does not exist
                print '*** Fatal Error: Path name ' + os.path.abspath(os.path.join(args[0],path_name)) + ' does not exist. ***'
                parser.print_help()
                sys.exit(1)
            if not os.path.exists(os.path.join(args[1], path_name)):
                # make directory if dest directory does not exist
                os.makedirs(os.path.join(args[1], path_name))
                if options.verboseMode:
                    print 'Creating destination directory: ' + str(os.path.join(args[1], path_name))

    return (args[0], args[1], options.sub_dirs, args[2:], 
        options.verboseMode, options.debugMode)


class DataDirConverter():
    ''' Converts a directory of runs with a list of (start_run_str, end_run_str)
    tuples for each tiling, which generally consists of many runs.
    '''

    def __init__(self, src_path, dst_path, map_names, verbose, debug):
        self.runFileNames = list()
        self.destPath = dst_path
        self.verboseMode = verbose
        self.debugMode = debug
        self.formatFileNames(src_path, map_names)

        # process data
        #self.convertDir()

    def formatFileNames(self, src_path, map_names):
        ''' Creates a list of 2-tuples for the file name extends of each tiling.
        '''
        first = True
        single_run_names = list()
        for name in map_names:
            #print 'src_path = ' + str(src_path) + ', map = ' + str(name) + ', joined = ' + str(os.path.join(src_path, name))
            if first:
                single_run_names.append(os.path.join(src_path, name))
                first = False
            else:
                single_run_names.append(os.path.join(src_path, name))
                self.runFileNames.append(tuple(single_run_names))
                single_run_names = list()
                first = True

    def convertDir(self, print_help):
        ''' Converts a directory of runs with a list of (start_run_str, end_run_str)
        tuples for each tiling, which generally consists of many runs.  Need the
        parser print_help function in case the map name does not exist.  This could
        happen if user types '--subdir= size1 size64' instead of '--subdir=size1 size64'
        '--subdir size1 size64'. 
        '''
        for start_name, end_name in self.runFileNames:
             # strip the right-most integers for calculating intermediate file names
             # first get the start number
             pos = len(start_name)-1
             while pos >= 0:
                if start_name[pos:].isdigit():
                   pos -= 1
                else:
                   start_num_pos = pos+1
                   start_num = int(start_name[start_num_pos:])
                   break

             # second get the end number
             pos = len(end_name)-1
             while pos >= 0:
                if end_name[pos:].isdigit():
                   pos -= 1
                else:
                   end_num = int(end_name[pos+1:])
                   break

             for num in np.arange(start_num, end_num+1):
                imap_str = start_name[:start_num_pos] + str(num)
                idata_str = imap_str + '.cnt'
                for input_filename in [imap_str, idata_str]:
                    # last minute check to prevent a IOError and traceback later
                    if not os.path.exists(input_filename):
                        print '*** Fatal Error: Path name ' + os.path.abspath(input_filename) + ' does not exist. ***'
                        print_help()
                        sys.exit(1)
                        
                omap_str = os.path.join(self.destPath, os.path.basename(imap_str)) + '_rank_map.yaml'
                onodes_str = os.path.join(self.destPath, os.path.basename(imap_str))  + '_nodes.yaml'
                olinks_str = os.path.join(self.destPath, os.path.basename(imap_str))  + '_links.yaml'
                ometa_str = os.path.join(self.destPath, os.path.basename(imap_str))  + '_meta.yaml'
                argv = ["--imap", imap_str, "--idata", idata_str, "--omap", \
                    omap_str, "--onodes", onodes_str, "--olinks", olinks_str, \
                    "--ometa", ometa_str]
                if self.debugMode:
                    argv.append("-d")
                if self.verboseMode: 
                    argv.append("-v")
                    print '\nConvertBGQDataRun(argv), argv = ' + str(argv)

                runData = ConvertBGQDataRun.DataConverter(argv)

if __name__ == "__main__":
    usage = "Usage: " + sys.argv[0] + " [options] source_dir dest_dir tile1_first_map tile1_last_map [tile2_first_map tile2_last_map...]"
    parser = OptionParser(usage)
    source_dir, dest_dir, subdir_names, map_names, verbose, debug = parseCommandLine(parser)
    convertAllData(source_dir, dest_dir, subdir_names, map_names, verbose, debug, parser.print_help)

