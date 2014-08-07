import numpy as np

link_data_file = open('bgq_synthetic_links.yaml', 'w')
node_data_file = open('bgq_synthetic_nodes.yaml', 'w')

def next(current, max, forward):
	if current == max-1:
		return (0 if forward else current - 1)
	elif current == 0:
		return (1 if forward else max - 1)
	else:
		return (current + 1 if forward else current - 1)

def linkVal(e, d, c, b, a):
	# return a * 10000 + b * 1000 + c * 100 + d * 10 + e   # standard bg/q synthetic data
	return (abs(a-2.5) + abs(c-1.5)) * 10000  # increasing outwards from the center when looking down the b-direction of a 3-d torus

# Write node data to an intermediate file
node_data_file.write('---\n')
node_data_file.write('key: TEST_5D_TORUS\n')
node_data_file.write('---\n')
node_data_file.write('- [nodeid, int32]\n')
node_data_file.write('- [a, int32]\n')
node_data_file.write('- [b, int32]\n')
node_data_file.write('- [c, int32]\n')
node_data_file.write('- [d, int32]\n')
node_data_file.write('- [e, int32]\n')
node_data_file.write('- [code_region, int32]\n')
node_data_file.write('...\n')

for j in [1,2]:
	count = 0
	for i in np.ndindex(2, 3, 4, 5, 6):
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) +  ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(j) + ' \n'
		node_data_file.write(s)
		count += 1
		
# Write link data to an intermediate file

link_data_file.write('---\n')
link_data_file.write('key: TEST_5D_TORUS\n')
link_data_file.write('---\n')
link_data_file.write('- [linkid, int32]\n')
link_data_file.write('- [sa, int32]\n')
link_data_file.write('- [sb, int32]\n')
link_data_file.write('- [sc, int32]\n')
link_data_file.write('- [sd, int32]\n')
link_data_file.write('- [se, int32]\n')
link_data_file.write('- [ta, int32]\n')
link_data_file.write('- [tb, int32]\n')
link_data_file.write('- [tc, int32]\n')
link_data_file.write('- [td, int32]\n')
link_data_file.write('- [te, int32]\n')
link_data_file.write('- [code_region, int32]\n')
link_data_file.write('- [packets, int32]\n')
link_data_file.write('...\n')

for j in [1,2]:
	count = 0
	for i in np.ndindex(2, 3, 4, 5, 6):
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(next(i[4], 6, True)) + ' ' + \
			str(i[3]) + ' ' + str(i[2]) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(next(i[4], 6, False)) + ' ' + \
			str(i[3]) + ' ' + str(i[2]) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + \
			str(next(i[3], 5, True)) + ' ' + str(i[2]) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + \
			str(next(i[3], 5, False)) + ' ' + str(i[2]) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + \
			str(next(i[2], 4, True)) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + \
			str(next(i[2], 4, False)) + ' ' + str(i[1]) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + \
			str(i[2]) + ' ' + str(next(i[1], 3, True)) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + \
			str(i[2]) + ' ' + str(next(i[1], 3, False)) + ' ' + str(i[0]) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		s = str(count) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + str(i[2]) + ' ' + \
			str(i[1]) + ' ' + str(i[0]) + ' ' + str(i[4]) + ' ' + str(i[3]) + ' ' + \
			str(i[2]) + ' ' + str(i[1]) + ' ' + str(next(i[0], 2, True)) + ' ' + \
			str(j) + ' ' + str(linkVal(*i)) + ' \n'
		link_data_file.write(s)
		count += 1
		