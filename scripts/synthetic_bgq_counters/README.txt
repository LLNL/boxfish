Author:  Collin McCarthy
Updated:  10/3/2013

The script 'generate_bgq_synthetic_data.py' creates the files 'bgq_synthetic_links.yaml' and 'bgq_synthetic_nodes.yaml' which contain the data for the meta file 'bgq_synthetic_meta.yaml'.  The meta file itself is created by hand, without the use of a script.  

The synthetic data is for a 5d torus of dimensions [a, b, c, d, e] = [6, 5, 4, 3, 2].  Each link has a source node, and a direction of +a, -a, +b, -c, ..., +e, -e.  The network traffic on each link is calculated based on the coordinates of it's source node as follows:

link_traffic = a * 10000 + b * 1000 + c * 100 + d * 10 + e .  

If any modifications are desired, see the method linkVal() in 'generate_bgq_synthetic_data.py'.

Update:  8/6/2014

Changed the linkVal() to have values increase moving away from the center node (3, 2, 2, 1, 0), for the paper figure showing the 2-dimensional projection.  
