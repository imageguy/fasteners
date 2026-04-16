#!/usr/bin/env python

# based on boltgen.py

# generates STL files for a single bolt or screw at all lengths for all
# pitches for that dimension. All have the same head.

# By Nenad Rijavec.
# Distributed under MIT license.

import argparse
import sys
import math
from fractions import Fraction
from generate import *

# mkfraction converts the number of quarter-inches in to the usual
# imperial inch + fraction string for display
def mkfraction( l ) :
	i = math.floor(l/4)
	frac = l - 4 * i
	if i == 0 :
		if frac == 2 :
			val = '1/2'
		else :
			val = str(frac) + '/4'
	else :
		val = str(i)
		if frac > 0 :
			val += ' '
			if frac == 2 :
				val += '1/2'
			else :
				val += str(frac) + '/4'
	return( val )


# Define your custom HelpFormatter
class ColoredHelpFormatter(argparse.RawTextHelpFormatter):
    def _format_args(self, action, default_metavar=None):
        # Set the color for optional parameter values
        #optional_color = '\033[94m'  # Bright blue color
        optional_color = '\033[95m'  # Bright magenta color
        reset_color = '\033[0m'      # Reset color

        if action.nargs == 0:
            return ''

        # Use the default formatting
        metavar = super()._format_args(action, default_metavar)

        # Return the formatted string with color
        return f'{optional_color}{metavar}{reset_color}'

def parse_int(name, value: str) -> int:
	try:
		return int(value)
	except Exception:
		sys.exit(f'{name}: invalid number syntax: "{value}"')

def parse_number(name, value: str, units: str) -> float:
	try:
		if units == 'mm' or not '/' in value :
			return float(value)

		parts = value.strip().split(' ')
		if len(parts) == 1:
			return float(Fraction(parts[0]))
		elif len(parts) == 2:
			return int(parts[0]) + float(Fraction(parts[1]))
		else:
			raise ValueError
	except Exception:
		sys.exit(f'{name}: invalid number syntax: "{value}"')
		#raise argparse.ArgumentTypeError(f'invalid number syntax: '{value}'')


def positive(value: float, name: str):
	if value <= 0:
		sys.exit(f'Error: {name} must be > 0')

def main():
	parser = argparse.ArgumentParser(
		description='Makes a set of bolts or screws.',
		formatter_class=ColoredHelpFormatter
	)

	# positional arguments
	parser.add_argument(
		'units',
		choices=['mm', 'in'],
		help='units, mm (metric) or in (imperial)',
	)

	parser.add_argument(
		'type',
		choices=['bolt', 'screw'],
		help='what to produce: bolt or screw',
	)

	parser.add_argument(
		'diam',
		help=( "diameter in chosen units. "
			"Number or (for imperial units) fraction" )
	)

	parser.add_argument(
		'head',
		nargs='?',
		choices=['none', 'hex', 'flat', 'pan', 'cap'],
		help=(
			"Defines the head for bolts and screws. "
			"Use 'none' for threaded rod. "
		),
	)

	# optional arguments
	parser.add_argument(
		'-v', '--verbose',
		action='store_true',
		help=( "Verbose output" )
	)
	parser.add_argument(
		'--fn',
		dest='fn',
		default='50',
		help=("Number of segments for each cylinder"
		)
	)
	# *_adj are defaulted in generate_bolt based on diam
	parser.add_argument(
		'--cross_adj',
		dest='cross_adj',
		help=("Increase of cross-recess trench width in mm"
		)
	)
	parser.add_argument(
		'--diam_adj',
		dest='diam_adj',
		help=("Increase/decrease the thread diameter in mm"
		)
	)
	parser.add_argument(
		'--hex_adj',
		dest='hex_adj',
		help=("Increase/decrease the diam of hex head/nut/etc in mm"
		)
	)
	parser.add_argument(
		'--prefix',
		dest='prefix',
		help=("File name prefix"
		)
	)

	args = parser.parse_args()

	if args.units == "mm" :
		am_metric = True
	else :
		am_metric = False
	# numeric parsing
	fn = parse_int('fn', args.fn)
	
	# generate the build screw and diam
	[ orig, bld ] = make_build_screw( am_metric, args.diam )
	if orig == None :
		sys.exit(f'Error: diam {args.diam} not found')
	diam = orig.diam

	# we can now parse diam-related defaults

	if not args.cross_adj == None :
		cross_adj = parse_number('cross_adj', args.cross_adj, 'mm')
	else :
		if bld.diam < 5 :
			cross_adj = 0.3
		elif bld.diam < 7 :
			cross_adj = 0.5
		else :
			cross_adj = 0.7
	if not args.diam_adj == None :
		diam_adj = parse_number('diam_adj', args.diam_adj, 'mm')
	else :
		if bld.diam < 3.75 :
			diam_adj = -0.15
		elif bld.diam < 9 :
			diam_adj = -0.3
		else :
			diam_adj = -0.5
	if not args.hex_adj == None :
		hex_adj = parse_number('hex_adj', args.hex_adj, 'mm')
	else :
		if args.head == 'cap' :
			if bld.diam < 4.5 :
				hex_adj = 0.3
			else :
				hex_adj = 0.5
		else :
			hex_adj = -0.5

	positive(fn, "fn")
	if not cross_adj == None :
		positive(cross_adj, "cross_adj")

	# arguments have still not been converted to metric

	# head validity rules
	if args.type in ("bolt", "screw") and args.head is None:
		sys.exit("Error: head is required for bolt and screw")

	# generate the build screw
	[ orig, bld ] = make_build_screw( am_metric, args.diam )
	if orig == None :
		sys.exit(f'Error: diam {args.diam} not found')
	bld.print_vars()
	diam = orig.diam

	# final output
	if args.verbose :
		print("Arguments received:")
		print(f"  units     : {args.units}")
		print(f"  type      : {args.type}")
		print(f"  diam      : {diam}")
		print(f"  head      : {args.head}")
		print(f"  fn        : {fn}")
		print(f"  cross_adj : {cross_adj}")
		print(f"  diam_adj  : {diam_adj}")
		print(f"  hex_adj  : {hex_adj}")


	# generate the range of sizes
	
	lengths = []
	shanklengths = None
	dsplengths = []
	if args.head == "none" :
		if args.type == 'bolt' :
			type = "srod"
		else :
			type = "rod"
	else :
		type = args.type
	if args.type == "bolt" and not am_metric :
		shanklengths = []
		thread_l = \
			0.5 * bolt_thread_length(6, diam, am_metric)
		if type == 'srod' :
			thread_l *= 2
		lower = 1 + math.ceil(thread_l/0.25)
		upper = math.ceil(7*diam/0.25)
		if upper < lower +1 :
			upper = lower +1 
		for l in range( lower, upper ) :
			lengths.append( 25.4*0.25*l)
			shanklengths.append( 25.4*(0.25*l-thread_l))
			# display length in fractions
			dsplengths.append( mkfraction(l) )
			#dsplengths.append( str("{:.2f}".format(0.25*l)))
	elif args.type == "bolt" :
		shanklengths = []
		thread_l = 0.5 * bolt_thread_length( 120, diam, am_metric )
		if args.head == 'none' :
			thread_l *= 2 # rod has two threads
		lower = 1 + math.ceil(thread_l/5)
		upper = math.ceil(7*diam/5)
		if upper < lower + 1 :
			upper = lower + 1 
		for l in range( lower, upper ) :
			lengths.append( 5*l)
			shanklengths.append( 5*l-thread_l)
			dsplengths.append( 5*l ) # int, no need to fmt
	elif am_metric :
		lower = math.ceil(diam/5)
		upper = math.ceil(7*diam/5)
		for l in range( lower, upper ) :
			lengths.append( 5*l)
			dsplengths.append( 5*l ) # int, no need to fmt
	else:
		lower = math.ceil(diam/0.25)
		upper = math.ceil(7*diam/0.25)
		for l in range( lower, upper ) :
			lengths.append( 25.4*0.25*l)
			# display length in fractions
			dsplengths.append( mkfraction(l) )
			#dsplengths.append( str("{:.2f}".format(0.25*l)))
	# lengths are now all metric
	print( f'{len(lengths)} lengths per pitch will be generated' )

	# loop over pitches and lengths
	for pitch in bld.pitches :
		for i in range( 0, len(lengths) ) :
			length = lengths[i]
			if args.type == 'bolt' :
				shank_l = shanklengths[i]
			else :
				shank_l = 0
			dsplength = dsplengths[i]
			fname = ""
			fname += f"{args.units}" + "_"
			if not args.head == 'none' :
				fname += args.head + "_"
			fname += type + "_"
			fname += bld.desc.replace("/","f").replace(" converted","")
			fname += "X"
			if am_metric :
				fname += str("{:.2f}".format(pitch))
			else :
				fname += str("{:.0f}".format(25.4/pitch))
			fname += f"-{dsplength}"
			fname = fname.replace("/","f")
			fname = fname.replace(".","p")
			fname = fname.replace(" ","_")
			fname += ".stl"
			comment = fname + ' generated by boltgen'
			comment += ' cr=' + str("{:.2f}".format(cross_adj))
			comment += ' dia=' + str("{:.2f}".format(diam_adj))
			comment += ' hex=' + str("{:.2f}".format(hex_adj))
	
			if not args.prefix == None :
				fname = args.prefix + fname

			print( fname )

			facets = []
			generate_bolt( am_metric, type, bld,
				pitch, length, args.head, None, fn,
				cross_adj, diam_adj, hex_adj,
				shank_l, bld.shank_d, facets)
			write_binary_stl( fname, comment, facets )
			""" #b
			""" #e

if __name__ == "__main__":
	main()

