import sys

file_path = sys.argv[1]
f = open(file_path, "r")
temp = f.readlines()

count = 0

for idx in range(0,len(temp)):
	if "last trade price" in temp[idx]:
		#print(temp[idx])
		#print(temp[idx-2].split()[10])
		time_stamp = temp[idx-2].split()[10].split('.')
		if(len(time_stamp) > 1):
			if (len(time_stamp[1]) == 9):
				print("{0} {1}".format(time_stamp[1], temp[idx].split()[5]))
		#print("{0} {1}".format(temp[idx-2].split()[10], temp[idx].split()[5]))
		count += 1

#print(count)
