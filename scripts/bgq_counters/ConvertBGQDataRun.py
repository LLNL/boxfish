#!/usr/bin/python

'''
Author:  Collin McCarthy (cmccarthy@ucdavis.edu)
Last Update: 9/29/3013

About:  This script file converts data from a single BG/Q run into a Boxfish
   compatible .yaml format.  It takes two input files (i.e. map-1, map-1.cnt) 
   which hold the rank map and node/link data, respectively.  Outputs four .yaml 
   files for Boxfish (i.e. map-1_rank_map.yaml, map-1_nodes.yaml, map-1_links.yaml, 
   map-1_meta.yaml) which hold the correctly formatted mpi_rank map, node
   ids, link data, and the meta data file, respectively.  

   For command line arguments and more detailed information see README.txt.
'''

import sys
import os
import getopt  #using instead of optparse.OptionParser since no cmd-line options
import numpy as np

class DataConverter():
   ''' Converts data from a single run (i.e. map-1, map-1.cnt) into four files 
   for Boxfish (i.e. map-1_rank_map.yaml, map-1_nodes.yaml, map-1_links.yaml,
   map-1_meta.yaml).
   '''

   def __init__(self, argv):
      # class vars
      self.iMap = ''  # file name of input map, i.e. map-1
      self.iData = ''  # file name of input data, i.e. map-1.cnt
      self.oMap = ''  # file name of output rank_map, i.e. map-1_rank_map.yaml
      self.oNodes = ''  # file name of output node data, i.e. map-1_nodes.yaml
      self.oLinks = ''  # file name of output link data, i.e. map-1_links.yaml
      self.oMeta = ''   # file name of output meta data, i.e. map-1_meta.yaml
      self.shape = tuple() # number of coordinate values in each node dimension
      self.verboseMode = False  # print out what files currently processing
      self.debugMode = False # for debugging output data
      self.mpiRank = list()  # stores the mpi rank for thread (a, b, c, d, e, t)
      self.nodeData = list() # stores 10 LinkData obj. for node (a, b, c, d, e) 

      # initialize file names
      self.parseCommandLine(argv)

      # process the data
      self.processData()

   def getDestNode(self, node, link_num):
      if link_num == 0: # a_minus link
         return self.getNextNode(node, 0, False)
      elif link_num == 1: # a_positive link
         return self.getNextNode(node, 0, True)
      elif link_num == 2: # b_minus link
         return self.getNextNode(node, 1, False)
      elif link_num == 3: # b_positive link
         return self.getNextNode(node, 1, True)
      elif link_num == 4: # c_minus link
         return self.getNextNode(node, 2, False)
      elif link_num == 5: # c_positive link
         return self.getNextNode(node, 2, True)
      elif link_num == 6: # d_minus link
         return self.getNextNode(node, 3, False)
      elif link_num == 7: # d_positive link
         return self.getNextNode(node, 3, True)
      elif link_num == 8: # e_minus link
         return self.getNextNode(node, 4, False)
      elif link_num == 9: # e_positive link
         return self.getNextNode(node, 4, True)
      else:
         return [-1 for i in range(len(node))]
      
   def getNextNode(self, node, dim, inc = True):
      if inc and node[dim] == self.shape[dim]-1:
         return node[:dim] + [0] + node[dim+1:]
      elif inc:
         return node[:dim] + [node[dim]+1] + node[dim+1:]
      elif not inc and node[dim] == 0:
         return node[:dim] + [self.shape[dim]-1] + node[dim+1:]
      elif not inc:
         return node[:dim] + [node[dim]-1] + node[dim+1:]
      else:
         return [-1 for i in range(len(node))]

   def inputData(self):
      # for input map file, store mpi rank for each (a, b, c, d, e, t)
      # to get size/dimensions of numpy array, get max a, b, c, d, e, t - as of
      #     now this is just last line of iMap, but that may change so find max

      #with open(self.iMap) as iMapFile:
      with open(self.iData) as iMapFile:
         max_a = max_b = max_c = max_d = max_e = max_t = 0
         # iMap = <a b c d e t>, line_number = mpi_rank
         # find max node dimensions to set up numpy array
         for line in iMapFile:
            split_line = line.split(' ', 8)
            #split_line = line.split(' ', 5)
            #for i in range(len(split_line)):
            for i in range(len(split_line) - 1):
               split_line[i] = int(split_line[i])
            ignore, rank, a, b, c, d, e, t, cruft = split_line
            #a, b, c, d, e, t = split_line
            max_a = max(a, max_a)
            max_b = max(b, max_b)
            max_c = max(c, max_c)
            max_d = max(d, max_d)
            max_e = max(e, max_e)
            max_t = max(t, max_t)

         # initialize numpy array, move read ptr to start again
         self.shape = list([max_a+1, max_b+1, max_c+1, max_d+1, max_e+1])
         self.mpiRank = np.tile(0, self.shape + [max_t+1])
         iMapFile.seek(0)
         line_num = 0
         for line in iMapFile:
            split_line = line.split(' ', 8)
            #split_line = line.split(' ', 5)
            #for i in range(len(split_line)):
            for i in range(len(split_line) - 1):
               split_line[i] = int(split_line[i])
            ignore, rank, a, b, c, d, e, t, cruft = split_line
            #a, b, c, d, e, t = split_line
            self.mpiRank[(a, b, c, d, e, t)] = rank
            #self.mpiRank[(a, b, c, d, e, t)] = line_num
            #if self.debugMode:
            #   print 'mpiRank(',a,b,c,d,e,t,') = ', self.mpiRank[(a, b, c, d, e, t)]
            #line_num += 1
         
      # for input data file, store link data for each node (a, b, c, d, e)
      # link data stored as [a-, a+, b-, b+, c-, c+, d-, d+, e-, e+], where
      #  each element in the list is a linkData object, which stores 5 scalars
      #  for that link direction
      with open(self.iData) as iDataFile:
         temp_link_data = [-1 for i in range(5)]
         self.nodeData = np.tile([LinkData(temp_link_data) for i in range(10)],\
            self.shape + [1])
         for line in iDataFile:
            node_string, link_string = line.split('**', 1)
            node_string = node_string.split(' ')
            # don't include the empty string link_string[0], from space after **
            #   nor empty string at the end of link_string, from trailing space
            link_data = link_string.split(' ')[1:-1]

            # node coordinates abcdet are columns 2-7 (starting at 0)
            node = node_string[2:8]
            for i in range(len(node)):
               node[i] = int(node[i])
            node = tuple(node)

            # link data are 6 values per direction, 10 directions
            for i in range(len(link_data)):
               link_data[i] = int(link_data[i])

            # store the link data, ignore the 4th value, col_packets
            print '\n'
            for i in range(10):
               start = i*6
               if self.debugMode:
                  print 'Map = ' + str(self.iMap) + ', Setting node (a,b,c,d,e,t) = ' + \
                     str(node) + ', mpi_rank = ' + str(self.mpiRank[node]) + ', link_num = ' + str(i)
               single_link_data = link_data[start:start+3]+ \
                  link_data[start+4:start+6]
               self.nodeData[node[:-1]][i].setLinkData(single_link_data, self.debugMode)
       
   def outputData(self):
      #print 'OutputData, map = ' + str(self.iMap)

      with open(self.oMap, 'w') as oMapFile:
         # use the oMap file name (without extension) as the key
         key_string = '---\nkey: ' + 'bgq_'+os.path.basename(self.iMap) + '\n---\n- '\
            + '[mpirank, int32]\n- [nodeid, int32]\n...\n'
         oMapFile.write(key_string)
         rev_shape = list(self.shape)
         rev_shape.reverse()
         node_id = 0
         # node_id increases first in the a dim, then b, c, d, e
         #    ndindex iterates through last dim first, then second-last, etc
         #    so need to reverse order, iterate with ndindex, then reverse back
         for rev_node in np.ndindex(*tuple(rev_shape)):
            node = list(rev_node)
            node.reverse()
            # since the link data for each node is for the t = 0 thread, use 0
            mpi_rank = self.mpiRank[tuple(node)][0]
            oMapFile.write(str(mpi_rank) + ' ' + str(node_id) + ' \n')
            node_id += 1

      with open(self.oNodes, 'w') as oNodesFile:
         # use the oNodes file name (without extension) as the key
         key_string = '---\nkey: ' + 'bgq_'+os.path.basename(self.iMap) + '\n---\n- ' \
            + '[nodeid, int32]\n- [a, int32]\n- [b, int32]\n- [c, int32]\n- ' \
            + '[d, int32]\n- [e, int32]\n...\n'
         oNodesFile.write(key_string)
         rev_shape = list(self.shape)
         rev_shape.reverse()
         node_id = 0
         # node_id increases first in the a dim, then b, c, d, e
         #    ndindex iterates through last dim first, then second-last, etc
         #    so need to reverse order, iterate with ndindex, then reverse back
         for rev_node in np.ndindex(*tuple(rev_shape)):
            node = list(rev_node)
            node.reverse()
            node_str = ''
            for i in range(len(node)):
               node_str += str(node[i]) + ' '
            oNodesFile.write(str(node_id) + ' ' + node_str + '\n')
            node_id += 1

      with open(self.oLinks, 'w') as oLinksFile:
         # use the oLinks file name (without extension) as the key
         key_string = '---\nkey: ' + 'bgq_'+os.path.basename(self.iMap) + '\n---\n- ' \
            + '[linkid, int32]\n- [sa, int32]\n- [sb, int32]\n- [sc, int32]\n' \
            + '- [sd, int32]\n- [se, int32]\n- [ta, int32]\n- [tb, int32]\n' \
            + '- [tc, int32]\n- [td, int32]\n- [te, int32]\n- [sent_chunks, ' \
            + 'int64]\n- [dynamic_chunks, int64]\n- [deterministic_chunks, ' \
            + 'int64]\n- [recv_packets, int64]\n- [fifo_length, int64]\n...\n'
         oLinksFile.write(key_string)
         rev_shape = list(self.shape)
         rev_shape.reverse()
         node_id = 0
         # node_id increases first in the a dim, then b, c, d, e
         #    ndindex iterates through last dim first, then second-last, etc
         #    so need to reverse order, iterate with ndindex, then reverse back
         for rev_node in np.ndindex(*tuple(rev_shape)):
            node = list(rev_node)
            node.reverse()
            node_str = ''
            for i in range(len(node)):
               node_str += str(node[i]) + ' '

            for link_num in range(10):
               link_id = node_id*10 + link_num
               dest_node = self.getDestNode(node, link_num)
               dest_node_str = ''
               for i in range(len(dest_node)):
                  dest_node_str += str(dest_node[i]) + ' '
               node_t = tuple(node)
               oLinksFile.write(str(link_id) + ' ' + node_str + dest_node_str+\
                  str(self.nodeData[node_t][link_num].sentChunks) + ' ' + \
                  str(self.nodeData[node_t][link_num].dynamicChunks) + ' ' + \
                  str(self.nodeData[node_t][link_num].deterministicChunks) + \
                  ' ' + str(self.nodeData[node_t][link_num].recvPackets) + \
                  ' ' + str(self.nodeData[node_t][link_num].fifoLength) + ' \n')
            node_id += 1

      with open(self.oMeta, 'w') as oMetaFile:
         key_string = '---\nkey: ' + 'bgq_'+os.path.basename(self.iMap) + '\nhardware' \
            + ': {\n type: bgq,\n network: torus,\n nodes: ' + str(np.prod(self.shape)) \
            + ',\n coords: [a, b, c, d, e],\n coords_table: ' + os.path.basename(self.oNodes) \
            + ',\n dim: {a: ' + str(self.shape[0]) + ', b: ' + str(self.shape[1]) \
            + ', c: ' + str(self.shape[2]) + ', d: ' + str(self.shape[3]) \
            + ', e: ' + str(self.shape[4]) + '},\n source_coords: {a: sa, b: sb, ' \
            + 'c: sc, d: sd, e: se},\n destination_coords: {a: ta, b: tb, c: tc' \
            + ', d: td, e: te},\n link_coords_table: ' + os.path.basename(self.oLinks) \
            + '\n}\n'
         nodes_string = '---\nfiletype: table\nfilename: ' + os.path.basename(self.oNodes)\
            + '\ndomain: HW\ntype: NODE\nfield: nodeid\nflags: 0\n'
         links_string = '---\nfiletype: table\nfilename: ' + os.path.basename(self.oLinks)\
            + '\ndomain: HW\ntype: LINK\nfield: linkid\nflags: 0\n'
         rank_map_string = '---\nfiletype: projection\ntype: file\nfilename: ' + os.path.basename(self.oMap)\
            + '\nsubdomain:\n- { domain: HW, type: NODE, field: nodeid }\n- { '\
            + 'domain: COMM, type: RANK, field: mpirank }\nflags: 0\n'  
         node_link_string = '---\nfiletype: projection\ntype: node link\nnode_policy: Source'\
            + '\nlink_policy: Source\nsubdomain:\n- { domain: HW, type: NODE, '\
            + 'field: nodeid }\n- { domain: HW, type: LINK, field: linkid }'\
            + '\nflags: 0\n...\n'
         oMetaFile.write(key_string + nodes_string + links_string + rank_map_string
            + node_link_string)
   
   def parseCommandLine(self, argv):
      ''' Stores input and output file names for converting data.  Note
      this uses "options" even though they are required.  This is to make it
      more clear what each argument corresponds to.
      '''

      # local vars
      usageMessage = 'Usage: ' + sys.argv[0] + ' --imap <input_map_file> --idata' \
            + ' <input_data_file> --omap <output_rank_map_file> --onodes' \
            + ' <output_nodes_file> --olinks <output_links_file> --ometa' \
            + ' <output_data_file>\n'
      
      # store command line args
      try:
         opts, args = getopt.getopt(argv, "vd", ["imap=","idata=","omap=",
            "onodes=", "olinks=", "ometa="])
      except getopt.GetoptError:
         print "\n*** Fatal Error: Unknown command line argument given. ***"
         print usageMessage
         sys.exit(2)

      # first check if verbose mode
      for opt, arg in opts:
         if opt == '-v':
            self.verboseMode = True
         if opt == '-d':
            self.debugMode = True

      status_msg = ''
      if self.verboseMode:
         status_msg += '\nVerbose Mode is ON.'
      else:
         status_msg += '\nVerbose Mode is OFF.'
      if self.debugMode:
         status_msg += '  Debug Mode is ON.'
      else:
         status_msg += '  Debug Mode is OFF.'

      # now store input/output file names
      if self.verboseMode: 
         print status_msg
         print 'Command Line Arguments = ' + str(opts)

      for opt, arg in opts:
         if self.verboseMode: 
            print '\tOption = ' + str(opt) + ', Argument = ' + str(arg)

         if opt == "--imap":
            self.iMap = arg
            if self.verboseMode: print '\t\tInput map file = "' + self.iMap \
               + '"'
         elif opt == "--idata":
            self.iData = arg
            if self.verboseMode: print '\t\tInput data file = "' + self.iData \
               + '"'
         elif opt == "--omap":
            self.oMap = arg
            if self.verboseMode: print '\t\tOutput comm map file = "' + \
               self.oMap + '"'
         elif opt == "--onodes":
            self.oNodes = arg
            if self.verboseMode: print '\t\tOutput nodes data file = "' + \
               self.oNodes + '"'
         elif opt == "--olinks":
            self.oLinks = arg
            if self.verboseMode: print '\t\tOutput links data file = "' + \
               self.oLinks + '"'
         elif opt == "--ometa":
            self.oMeta = arg
            if self.verboseMode: print '\t\tOutput meta file = "' + \
               self.oMeta + '"'
      if self.verboseMode: print '\n'

      # check that all needed file names are provided
      for fileName in [self.iMap, self.iData, self.oMap, self.oNodes, self.oLinks, self.oMeta]:
         if fileName == '':
            print '\n*** Fatal Error: Too few command line arguments. ***'
            print usageMessage
            sys.exit(2)

   def processData(self):
      print 'Processing data for map ' + str(self.iMap)
      self.inputData()
      self.outputData()


class LinkData():
   ''' Struct to hold the link data. Attributes are sent_chunks, dynamic_chunks,
   deterministic_chunks, recv_packets, fifo_length.  

   The attribute col_packets are ignored as of now.  Each node in self.nodeData
   has a list of LinkData objects, one per dimension link, plus and minus.
   '''

   def __init__(self, data):
      self.setLinkData(data)

   def setLinkData(self, data, debug_mode = False):
      self.sentChunks = data[0]
      self.dynamicChunks = data[1]
      self.deterministicChunks = data[2]
      self.recvPackets = data[3]
      self.fifoLength = data[4]
      if debug_mode:
         print '\tsent_chunks =',self.sentChunks,', dynamic_chunks =', \
         self.dynamicChunks,', deterministic_chunks =',self.deterministicChunks\
         ,', recv_packets =',self.recvPackets,', fifo_length =',self.fifoLength

if __name__ == "__main__":
   runData = DataConverter(sys.argv[1:])
   runData.processData()
