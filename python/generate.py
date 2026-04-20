#! /usr/bin/python

# generate_bolt generates screw or bolt. generate_nut generates a nut.
# we assume all the arguments have been parsed and validated.
# By Nenad Rijavec.

# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

from facets import *
from dimensions import *
from constructs import *
from parts import *
from boltgen import *

def generate_bolt( am_metric,
		type,  # bolt, screw, rod, srod
		bld,
		pitch,
		length,
		head,
		hex,
		hex_h,
		fn,
		cross_adj,
		diam_adj,
		hex_adj,
		h_adj,
		shank_l,
		shank_d,
		facets
		) :
	if am_metric :
		units = 'metric'
	else :
		units = 'imperial'

	chamfer_h = bld.diam / 16
	length -= chamfer_h
	start_z = 0
	thread_l = 0 # used for srod
	recess_bottom = False

	# build the head, if any
	head_top = []
	if head == 'hex' :
		if hex == None:
			hex = bld.hex_a
		head_top = hex_head( hex, hex_h, hex_adj, facets )
		start_z = head_top[0].z
	elif head == 'flat' :
		if type == 'bolt' :
			dd = shank_d
		else :
			dd = bld.diam
		head_top = flat_head( bld.head_d, h_adj, bld.flat_angle, dd,
			bld.T , bld.M , bld.N +cross_adj, fn, facets )
		start_z = head_top[0].z
	elif head == 'pan' :
		head_top = pan_head( bld.head_d, bld.pan_h, h_adj, bld.T,
			bld.M, bld.N+cross_adj, fn, facets )
		start_z = head_top[0].z
	elif head == 'cap' :
		if hex == None:
			hex = bld.cap_s
		head_top = cap_head( bld.cap_d, bld.cap_h, h_adj,
			hex, bld.cap_T, hex_adj, fn, facets )
		start_z = head_top[0].z
	elif head == 'none' and type == 'srod' :
		# threaded rod with shank
		thread_l = (length+chamfer_h-shank_l)/2
		start_z = chamfer_h+thread_l
		length -= start_z
		# have to make another thread segment instead of the head
		# we chamfer on the bottom, but not on the top
		[bot2, head_top] = thread_segment( bld.diam+diam_adj, \
			pitch, \
			chamfer_h, thread_l, fn, \
			facets, recess_bottom = True )
		min_r = head_top[0].r
		for vt in head_top :
			if vt.angle > 2 * math.pi :
				vt.angle -= 2 * math.pi
			if min_r > vt.r :
				min_r = vt.r 
		head_top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		chamfer_r = min_r - math.sqrt(3)*chamfer_h
		ch_bot = []
		angle = bot2[0].angle
		for n in range(0,fn) :
			ch_bot.append( Vertex( chamfer_r, angle, \
			0, am_cyl=True))
			angle += 2*math.pi/fn
			if angle > 2*math.pi :
				angle -= 2*math.pi
		ch_bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		bot2.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		ring( bot2, ch_bot, facets )
		ch_bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
		facet_polygon( ch_bot, facets )
	elif head == 'none' : # threaded rod
		recess_bottom = True
		start_z = chamfer_h
		length -= chamfer_h
	
	# shank, if any
	s_top = []
	if type == 'bolt' or type == 'srod' :
		head_d = 2 * head_top[0].r
		[ s_bot, s_top ] = cylinder_body( shank_d, shank_l,
					start_z, fn, facets )
		s_bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		head_top.sort( key=lambda Vertex: Vertex.angle,reverse=False)
		if not head == 'flat' or not len(s_bot) == len(head_top) :
			ring( s_bot, head_top, facets )
		#ring( s_bot, head_top, facets )
		start_z += shank_l
		length -= shank_l

	# thread, always chamfered on top. If threaded rod, chamfer on
	# bottom as well. If threaded bolt (i.e., rod with shank), two
	# thread segments, the bottom one built earlier.
	[bot, top] = thread_segment( bld.diam+diam_adj, \
		pitch, \
		start_z, length, fn, \
		facets, recess_bottom = recess_bottom )
	min_r = top[0].r
	for vt in top :
		if vt.angle > 2 * math.pi :
			vt.angle -= 2 * math.pi
		if min_r > vt.r :
			min_r = vt.r 
	top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	chamfer_r = min_r - math.sqrt(3)*chamfer_h
	ch_top = []
	angle = 0
	for n in range(0,fn) :
		ch_top.append( Vertex( chamfer_r, angle, \
		length+start_z+chamfer_h, am_cyl=True))
		angle += 2*math.pi/fn
		if angle > 2*math.pi :
			angle -= 2*math.pi
	ch_top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	ring( ch_top, top, facets )
	facet_polygon( ch_top, facets )

	# if rod, chamfer on the bottom. For srod, bottom section of
	# thread was built and chamfered earlier.
	if type == 'rod' :
		ch_bot = []
		angle = bot[0].angle
		for n in range(0,fn) :
			ch_bot.append( Vertex( chamfer_r, angle, \
			0, am_cyl=True))
			angle += 2*math.pi/fn
			if angle > 2*math.pi :
				angle -= 2*math.pi
		ch_bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
		ring( bot, ch_bot, facets )
		ch_bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
		facet_polygon( ch_bot, facets )

	# connect to the head or shank, if any

	if len( s_top ) > 0 :
		ring( bot, s_top, facets )
	elif len( head_top ) > 0 :
		ring( bot, head_top, facets )

	return


def generate_nut( am_metric, bld, pitch, length, hex, fn,
				diam_adj, hex_adj, facets) :
	chamfer_h = 0.020 * hex 
	start_z = chamfer_h
	# thread
	n = len(facets)
	[bot, top] = thread_segment( bld.diam+diam_adj, \
		pitch, \
		start_z, length-2*chamfer_h, fn, \
		facets, recess_top = False, recess_bottom = False )
	# reverse the facets, so they face in
	for i in range( n, len(facets) ) :
		facets[i].reverse()
	# enclosing hex shell
	[h_bot, h_top] = hex_shell( hex+hex_adj, length, 0.07*hex,
			True, True, facets )

	ch_top = []
	ch_bot = []
	angle_d = 2 * math.pi / fn
	r_chamfer = 1.15 * bld.diam/2
	for n in range( 0, fn ) :
		ch_bot.append( Vertex( r_chamfer, n*angle_d, 0,
					am_cyl = True ) ) 
		ch_top.append( Vertex( r_chamfer, n*angle_d, length,
					am_cyl = True ) ) 
	ch_top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	h_top.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	ring( top, ch_top, facets )
	ring( ch_top, h_top, facets )
	ch_bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	h_bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring( bot, ch_bot, facets )
	ring( ch_bot, h_bot, facets )

	return [ diam_adj, hex_adj ]
