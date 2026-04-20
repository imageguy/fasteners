#!/usr/bin/env python3

# command line handling for nut generation
# modified from boltgen
# By Nenad Rijavec.

# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

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


def positive(value: float, name: str):
	if value <= 0:
		sys.exit(f'Error: {name} must be > 0')

def main():
	parser = argparse.ArgumentParser(
		description='Makes a nut. '
		'Use boltgen to make a bolt or screw',
		formatter_class=ColoredHelpFormatter
	)

	# positional arguments
	parser.add_argument(
		'units',
		choices=['mm', 'in'],
		help='units, mm (metric) or in (imperial)',
	)

	parser.add_argument(
		'diam',
		help=( "diameter in chosen units.\n"
			"Number or (for imperial units) fraction" )
	)
	
	# optional arguments

	parser.add_argument(
		'-v', '--verbose',
		action='store_true',
		help=( "Verbose output" )
	)
	parser.add_argument(
		'--length',
		dest = 'length',
		default = None,
		help=( "length in chosen units instead of default.\n"
			"Number or (for imperial units) fraction." )
	)

	parser.add_argument(
		'--pitch',
		dest='pitch',
		help=( "Specify the pitch or TPI, "
			"instead of using the default." )
	)
	parser.add_argument(
		'-o', '--outfile',
		dest='outfile',
		help=( "Specify the output file,\n"
			"instead of using the default." )
	)
	parser.add_argument(
		'--hex',
		dest='hex',
		help=( "Specify the wrench size, "
			"instead of using the default." )
	)
	parser.add_argument(
		'--fn',
		dest='fn',
		default='50',
		help=("Number of segments for each cylinder."
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
		help=("Increase/decrease the diam of hex nut in mm."
		)
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

	# generate the build nut
	[ orig, bld ] = make_build_nut( am_metric, args.diam )
	if bld == None :
		sys.exit(f"Error: diam {args.diam} not found and can't"+
			" be interpolated.")
	diam = bld.diam

	if bld.am_interpolated :
		print( 'nut was interpolated' )
	# numeric parsing
	fn = parse_int('fn', args.fn)
	if args.length == None :
		length = bld.hex_h
	else :
		length = parse_number('length', args.length, args.units )
	if args.pitch == None :
		if orig.am_interpolated :
			if am_metric :
				print( 'interpolated pitch: ' +
			str("{:.2f}".format(orig.pitches[orig.defpitch])))
			else :
				print( 'interpolated TPI: ' +
			str("{:.2f}".format(orig.pitches[orig.defpitch])))
		pitch = None
	else :
		pitch = parse_number('pitch', args.pitch, 'mm')
		if not am_metric :
			pitch = 25.4 / pitch
	    	# make sure pitch is not too coarse
		if bld.diam/2 < pitch * math.sqrt(3) / 2 + 0.1 :
			sys.exit(f'Error: pitch too coarse for diameter')
	if args.diam_adj == None :
		if bld.diam < 8 :
			diam_adj = 0.40
		elif bld.diam < 9.5 :
			diam_adj = 0.7
		else :
			diam_adj = 0.8
	else :
		diam_adj = parse_number('diam_adj', args.diam_adj, 'mm')
	if not args.hex_adj == None :
		hex_adj = parse_number('hex_adj', args.hex_adj, 'mm')
	else :
		hex_adj = -0.5
	if pitch == None : 
		# not given as an arg, use the default, given in mm
		pitch = bld.pitches[bld.defpitch]
	# hex is computed as metric
	if args.hex is None and not bld.am_interpolated :
		hex = bld.hex_a
	elif args.hex is None :
		hex = bld.hex_a
		hh = orig.hex_a
		hh32 = hh * 32
		if am_metric or math.fabs(hh - math.trunc(hh32/32)) > 1e-3 :
			print( 'interpolated hex size: ' +
			str("{:.2f}".format(hh)))
		else :
			w = hh
			whole = math.trunc(w)
			w -= whole
			den = 2
			while  w > 0 and math.trunc(w*den) == 0 :
				den *= 2
			w *= den
			outstr = f'interpolated hex size: {whole}'
			if w > 0 :
				wstr = str("{:.0f}".format(w))
				outstr += f' {wstr}/{den}'
			print( outstr + ' in' )
	else :
		hex = parse_number('hex',args.hex, args.units)
		if not am_metric :
			hex *= 25.4
		if hex < diam+0.5+pitch :
			sys.exit("Error: hex too small")

	positive(fn, "fn")

	# length is still imperial here if not am_metric
	w = 0.2 * hex
	f = 1
	if not am_metric :
		f *= 25.4
	if f * length < w :
		if not am_metric :
			w /= 25.4
		outstr = "Error: length too short for this diameter.\n"
		outstr += "Minimum is " + str("{:.2f}".format(w))
		sys.exit(outstr)

	# final output
	if args.verbose :
		if not am_metric :
			print( 'original imperial' )
			orig.print_vars()
			print( 'build metric' )
		bld.print_vars()
		diamstr = str("{:.2f}".format(bld.diam))
		print("Arguments received:")
		print(f"  units     : {args.units}")
		print(f"  diam      : " + diamstr)
		print(f"  length    : {length}")
		print(f"  fn        : {fn}")
		print(f"  diam_adj  : {diam_adj}")
		print(f"  hex_adj  : {hex_adj}")

	if args.outfile == None :
		fname = ""
		fname += f"{args.units}" + "_"
		fname += "nut_"
		fname += bld.desc.replace("/","f").replace(" converted","")
		fname += "X"
		if am_metric :
			fname += str("{:.2f}".format(pitch))
		else :
			fname += str("{:.0f}".format(25.4/pitch))
		if args.length == None :
			fname += '-def'
		else :
			fname += '-'
		fname += str("{:.2f}".format(length))
		fname = fname.replace("/","f")
		fname = fname.replace(".","p")
		fname = fname.replace(" ","_")
		fname += ".stl"
	else :
		fname = str(args.outfile)
	# convert to metric what's imperial
	if not am_metric and not args.length == None :
		length *= 25.4

	print( fname )

	facets = []

	generate_nut( am_metric, bld, pitch, length, hex, fn,
			diam_adj, hex_adj, facets)
	comment = fname + ' generated by nutgen'
	comment += ' diam_adj=' + str("{:.2f}".format(diam_adj))
	comment += ' hex_adj=' + str("{:.2f}".format(hex_adj))
	if len(comment) > 80 :
		comment = comment[0:80]
	if not args.prefix == None :
		fname = args.prefix + fname
	
	write_binary_stl( fname, comment, facets )

if __name__ == "__main__":
	main()

