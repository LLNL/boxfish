Author:  Collin McCarthy (cmccarthy@ucdavis.edu)
Last Update: 9/29/2013

The script file ConvertBGQDataDir.py converts a directory containing BG/Q data in its raw format into another directory containing Boxfish compatible .yaml files.  This script file in turn calls ConvertBGQRun.py, which does the actual conversion, for easier maintainability.  Usage is described through an example.

Example:
This script file is placed in a directory with the BG/Q data of interest, itself being a directory called kneighbor_1k. This data directory, kneighbor_1k, has four sub-directories for different message sizes: size1, size64, size2048, and size524288.  Each sub-directory contains three tilings, each with 28 different runs.  Each run has two files of interest, the rank map file, i.e. map-1, and the link data file, i.e. map-1.cnt.  Runs for the first tiling are named map-1 to map-28, the second tiling mapT-1 to mapT-28, and the third tiling mapT2-1 to mapT2-28.  Each sub-directory (size1, size64, etc.) has identical run names, so the script ConvertBGQDataDir can be called passing the sub-directory names as an option, as follows.

$ ls
ConvertBGQDataDir.py	ConvertBGQDataRun.py	kneighbor_1k

$ ./ConvertBGQDataDir.py
*** Fatal Error: Too few arguments. ***
Usage: ConvertBGQDataDir.py [options] source_dir dest_dir tile1_first_map tile1_last_map [tile2_first_map tile2_last_map...]

Options:
  -h, --help            show this help message and exit
  -s SUB_DIRS, --subdir=SUB_DIRS
                        sub directories which hold data files
  -v, --verbose         print file name arguments passed to
                        ConvertBGQDataRun.py
  -d, --debug           print node and link data being output to .yaml files

$ ./ConvertBGQDataDir.py ./kneighbor_1k ./boxfish_kneighbor_1k map-1 map-2 mapT-1 mapT-2 --subdir=size1 --subdir=size64
Processing data for map ./kneighbor_1k/size1/map-1
Processing data for map ./kneighbor_1k/size1/map-2
Processing data for map ./kneighbor_1k/size1/mapT-1
Processing data for map ./kneighbor_1k/size1/mapT-2
Processing data for map ./kneighbor_1k/size64/map-1
Processing data for map ./kneighbor_1k/size64/map-2
Processing data for map ./kneighbor_1k/size64/mapT-1
Processing data for map ./kneighbor_1k/size64/mapT-2

$ ls ./boxfish_kneighbor_1k
size1	size64
$ ls -1 ./boxfish_kneighbor_1k/size1
map-1_links.yaml
map-1_meta.yaml
map-1_nodes.yaml
map-1_rank_map.yaml
map-2_links.yaml
map-2_meta.yaml
map-2_nodes.yaml
map-2_rank_map.yaml
mapT-1_links.yaml
mapT-1_meta.yaml
mapT-1_nodes.yaml
mapT-1_rank_map.yaml
mapT-2_links.yaml
mapT-2_meta.yaml
mapT-2_nodes.yaml
mapT-2_rank_map.yaml

$ exit

Now boxfish can read in the meta file for the mapping of your choice.  

Note that './' before the source and destination directories is optional, and the destination directory and subdirectories will be created if not found.  If the source directory cannot be found, a path error message is displayed and the program will exit.  Also, for the sub-directory option, '--subdir size1' will still work, however '--subdir = size1' and '--subdir= size1' will return the path '=' and '' respectively, and thus both would throw a path error for the missing map files and exit.

Lastly, if only one run needs to be converted, say map-20 in kneighbor_1k/size2048, that map name should be both the start and end map names, for example:
$ ./ConvertBGQDataDir.py kneighbor_1k boxfish_kneighbor_1k map-20 map-20 -s size2048
Processing data for map kneighbor_1k/size2048/map-20
$ # Or instead of using a sub-directory, specify the source and dest directories explicitly
$ ./ConvertBGQDataDir.py kneighbor_1k/size2048 boxfish_kneighbor_1k/size2048 map-20 map-20
Processing data for map kneighbor_1k/size2048/map-20
$ ls -1 ./boxfish_kneighbor_1k/size2048
map-20_links.yaml
map-20_meta.yaml
map-20_nodes.yaml
map-20_rank_map.yaml