for i in range(1,115):
	chnum=format(i,'03')
	with open('final-old/'+chnum) as infile,open('final/'+chnum,'w') as outfile:
		for line in infile:
			outfile.write(line.replace('۞',''))
