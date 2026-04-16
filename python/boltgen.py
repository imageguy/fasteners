#!/usr/bin/env python3

# command line handling for bolt/screw generation
# By Nenad Rijavec.
# Distributed under MIT license.
# First draft was done by ChatGPT 5. Current code has been heavily
# modified and extended.

import argparse
import sys
from fractions import Fraction
from generate import *

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


def non_negative(value: float, name: str):
	if value < 0:
		sys.exit(f'Error: {name} must be >= 0')

def positive(value: float, name: str):
	if value <= 0:
		sys.exit(f'Error: {name} must be > 0')

def main():
	parser = argparse.ArgumentParser(
		description='Makes a bolt or screw. '
		'Use nutgen to make a nut.',
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
		help=( "diameter in chosen units.\n"
			"Number or (for imperial units) fraction" )
	)

	parser.add_argument(
		'length',
		help=( "length in chosen units.\n"
			"Number or (for imperial units) fraction" )
	)

	parser.add_argument(
		'head',
		nargs='?',
		choices=['none', 'hex', 'flat', 'pan', 'cap'],
		help=(
			"Defines the head for bolts and screws.\n"
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
		'--pitch',
		dest='pitch',
		help=( "Specify the pitch or TPI,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'-o', '--outfile',
		dest='outfile',
		help=( "Specify the output file,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--shank_d',
		dest='shank_d',
		help=( "Specify the shank diameter for the bolt,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--shank_l',
		dest='shank_l',
		help=( "Specify the shank length for the bolt,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--hex',
		dest='hex',
		help=( "Specify the hex wrench size if head is hex,\n"
			"or hex key size if head is cap,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--hex_h',
		dest='hex_h',
		help=( "Specify the height of the hex head,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--fn',
		dest='fn',
		default='50',
		help=("Number of segments for each cylinder."
		)
	)
	# *_adj are defaulted in generate_bolt based on diam
	parser.add_argument(
		'--cross_adj',
		dest='cross_adj',
		help=("Increase of cross-recess trench width in mm."
		)
	)
	parser.add_argument(
		'--diam_adj',
		dest='diam_adj',
		help=("Increase/decrease the thread diameter in mm."
		)
	)
	parser.add_argument(
		'--hex_adj',
		dest='hex_adj',
		help=("Increase/decrease the diam of hex head in mm."
		)
	)
	parser.add_argument(
		'--h_adj',
		dest='h_adj',
		help=( "Increase the height of pan, flat or cap head,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--prefix',
		dest='prefix',
		help=("File name prefix."
		)
	)

	args = parser.parse_args()

	if args.units == "mm" :
		am_metric = True
	else :
		am_metric = False
	# numeric parsing
	# diam is taken from bld, since it can be '#n'
	length = parse_number('length', args.length, args.units)
	fn = parse_int('fn', args.fn)

	# generate the build screw and diam
	[ orig, bld ] = make_build_screw( am_metric, args.diam )
	if orig == None :
		sys.exit(f"Error: diam {args.diam} not found and can't"+
			" be interpolated.")
	diam = orig.diam

	if bld.am_interpolated :
		print( f'{args.type} was interpolated' )
	if not args.pitch == None :
		pitch = parse_number('pitch', args.pitch, 'mm')
		if not am_metric :
			pitch = 25.4 / pitch
	    	# make sure pitch is not too coarse
		if bld.diam/2 < pitch * math.sqrt(3) / 2 + 0.1 :
			sys.exit(f'Error: pitch too coarse for diameter')
	else :
		if orig.am_interpolated :
			if am_metric :
				print( 'interpolated pitch: ' +
			str("{:.2f}".format(orig.pitches[orig.defpitch])))
			else :
				print( 'interpolated TPI: ' +
			str("{:.2f}".format(orig.pitches[orig.defpitch])))

		pitch = None

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

	if not args.h_adj == None :
		h_adj = parse_number('h_adj', args.h_adj, 'mm')
	else :
		h_adj = 0
	if not args.hex_h == None :
		hex_h_orig = parse_number('hex_h', args.hex_h, args.units )
		if am_metric :
			hex_h = hex_h_orig
		else :
			hex_h = 25.4 * hex_h_orig
	else :
		hex_h = bld.hex_h
		hex_h_orig = hex_h if am_metric else hex_h / 25.4

	positive(length, "length")
	positive(fn, "fn")
	positive(hex_h, "hex_h")
	non_negative(h_adj, "h_adj")
	if not cross_adj == None :
		non_negative(cross_adj, "cross_adj")

	# arguments have still not been converted to metric

	# shank_l is computed as metric, but the algorithm differs between
	# imperial and metric
	# we use half the thread length of standard.
	shank_l = None
	if args.shank_l is not None:
		shank_l = parse_number('shank_l',args.shank_l, args.units)
		if shank_l <= 0 or shank_l >= length:
			sys.exit("Error: shank_l must be > 0 and < length")
		if args.type != "bolt":
			shank_l = None
			print( "Warning: only bolts have a shank. ",
				"Ignored", file=sys.stderr)
		if not am_metric :
			shank_l *= 25.4
	elif args.type == "bolt" and not am_metric :
		thread_l = \
			0.5 * bolt_thread_length(length, diam, am_metric)
		shank_l = 25.4*(length - thread_l)
		if args.head == 'none' :
			shank_l -= thread_l
	elif args.type == "bolt" :
		thread_l = 0.5 * bolt_thread_length( length, diam, am_metric )
		shank_l = length - thread_l
		# if shanked rod, we have two lengths of thread
		if args.head == 'none' :
			shank_l -= thread_l

	if not shank_l == None  and shank_l <= 0 :
		sys.exit("Error: shank_l <= 0")
		
	# shank_d is computed as metric
	shank_d = None
	if args.shank_d is not None:
		shank_d = parse_number('shank_d',args.shank_d, args.units)
		if shank_d <= diam:
			sys.exit("Error: shank_d <= diam")
		if args.type != "bolt":
			shank_d = None
			print( "Warning: only bolts have a shank. ",
				"Ignored", file=sys.stderr)
		if not am_metric :
			shank_d *= 25.4
	elif args.type == 'bolt' :
		shank_d = bld.shank_d
	# hex is computed as metric
	hex = None
	if args.hex is not None:
		hex = parse_number('hex',args.hex, args.units)
		if not am_metric :
			hex *= 25.4
		if args.head == 'hex' :
			if hex < diam :
				sys.exit("Error: hex < diam")
		elif args.head == 'cap' :
			hex_d = 2 * hex / math.sqrt(3)
			if hex_d > bld.cap_d - 1 :
				sys.exit("Error: hex too large")
		else :
			hex = None
			print( "Warning: only hex and cup head use --hex. ",
				"Ignored", file=sys.stderr)

	# head validity rules
	if args.type in ("bolt", "screw") and args.head is None:
		sys.exit("Error: head is required for bolt and screw")


	# final output
	if args.verbose :
		if not am_metric :
			print( '====== original imperial =====' )
			orig.print_vars()
			print( '===== build metric =====' )
		bld.print_vars()
		print("Arguments received:")
		print(f"  units     : {args.units}")
		print(f"  type      : {args.type}")
		print(f"  diam      : {diam}")
		print(f"  length    : {length}")
		print(f"  head      : {args.head}")
		print(f"  shank_l   : {shank_l}")
		print(f"  shank_d   : {shank_d}")
		print(f"  hex	    : {hex}")
		print(f"  hex_h	    : "+ str("{:.2f}".format(hex_h_orig)))
		print(f"  fn        : {fn}")
		print(f"  cross_adj : {cross_adj}")
		print(f"  diam_adj  : {diam_adj}")
		print(f"  hex_adj   : {hex_adj}")
		print(f"  h_adj     : {h_adj}")

	if pitch == None : 
		# not given as an arg, use the default, given in mm
		pitch = bld.pitches[bld.defpitch]
         
	if args.head == "none" :
		if args.type == 'bolt' :
			type = "srod"
		else :
			type = "rod"
	else :
		type = args.type
	if args.outfile == None :
		fname = ""
		fname += f"{args.units}" + "_"
		if not args.head == "none" :
			fname += args.head + "_"
		fname += type + "_"
		fname += bld.desc.replace("/","f").replace(" converted","")
		fname += "X"
		if am_metric :
			fname += str("{:.2f}".format(pitch))
		elif 25.4/pitch < 5 :
			fname += str("{:.2f}".format(25.4/pitch))
		else :
			fname += str("{:.0f}".format(25.4/pitch))
		fname += f"-{args.length}"
		fname = fname.replace("/","f")
		fname = fname.replace(".","p")
		fname = fname.replace(" ","_")
		fname += ".stl"
	else :
		fname = str(args.outfile)
	# convert to metric what's imperial
	if not am_metric :
		length *= 25.4

	# we need 2.5 turns of the thread for the code to work
	# this accounts for chamfer and also for the fact we stop building
	# thread one segment below the top.
	w = 2.5 * pitch + bld.diam/16 + 2*pitch/fn + 0.1
	if shank_l == None and length < w :
		outstr = "Error: length too short for this pitch.\n"
		outstr += "Minimum is " + str("{:.2f}".format(w))
		sys.exit(outstr)
	elif not shank_l == None :
		ll = length - shank_l
		if type == 'srod' :
			# srod has two thread segments
			ll /= 2
		#if ll < 2.5 * pitch + 2*pitch/fn + 0.1 :
		if ll < w :
			outstr = "Error: length too short for this pitch.\n"
			outstr += "Minimum is " + str("{:.2f}".format(2*w+shank_l))
			sys.exit(outstr)


	print( fname )

	facets = []
	generate_bolt( am_metric, type, bld,
		pitch, length, args.head, hex, hex_h, fn,
		cross_adj, diam_adj, hex_adj, h_adj, shank_l, shank_d, facets)
	comment = fname + ' generated by boltgen'
	comment += ' cr=' + str("{:.2f}".format(cross_adj))
	comment += ' dia=' + str("{:.2f}".format(diam_adj))
	comment += ' hex=' + str("{:.2f}".format(hex_adj))
	if len(comment) > 80 :
		comment = comment[0:80]
	if not args.prefix == None :
		fname = args.prefix + fname

	write_binary_stl( fname, comment, facets )

if __name__ == "__main__":
	main()

