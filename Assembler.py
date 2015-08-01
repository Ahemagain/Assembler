#!/usr/bin/env python

# Chris Wike 2015
# An assembler for a "toy" processor of my devising

import sys
import Parser

def main(argv):

	if (len(argv) == 1):
		print ("Not Enough Arguments")
		return

	elif (len(argv)==2):
		in_file = argv[1]
		out_file = "a.out"
	else : 
		in_file = argv[1]
		out_file = argv[2]

	in_fp = open(in_file,"r")
	out_fp = open(out_file, "wb")

	parser = Parser.Parser(in_fp)
	parser.run(out_fp)

	in_fp.close()
	out_fp.close()
	
main(sys.argv)
