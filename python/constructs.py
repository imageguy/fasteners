
# lower level constructs used for building parts.
# By Nenad Rijavec.

# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

import copy
import math
from facets import *

# facet_4vtx makes two facets to span four vertices. No three of the
# vertices can be colinear. The vertices have to be specified in the
# counter-clockwise direction looking from the desired "out" direction. The
# vertices need not be in the same plane. The two generated facets are
# added to the facets array.

# facet_polygon can be used instead, but this module produces simpler
# output - two facets instead of four, and doesn't add another vertex.

def facet_4vtx( v0, v1, v2, v3, facets ) :
	facets.append( Facet( v0, v1, v2 ) )
	facets.append( Facet( v0, v2, v3 ) )

# facet_polygon takes a list of vertices defining the polygon. Vertices should
# be in a counter-clockwise order so that "out" is up. Facets are added to
# the facets list.
# No three of any adjacent vertices can be colinear. Vertices don't have to
# be on the same plane but, if not, the resulting facets will not be
# planar.

# If desired, the generated center point can be moved vertically.

def facet_polygon( vertices, facets, mid_z = -1 ) :
	# compute center as the average of all the vertices
	x = 0
	y = 0
	z = 0
	for vt in vertices:
		x += vt.x
		y += vt.y
		z += vt.z
	nvts = len( vertices )
	if not mid_z == -1 :
		zz = mid_z
	else :
		zz = z/nvts
	center = Vertex( x/nvts, y/nvts, zz )
	for i in range(0,nvts):
		facets.append( Facet( \
			vertices[(i+1)%nvts], center, vertices[i] ) )
		
# Makes facets to cover a ring. The ring is defined with two polygons, inner
# and outer. They may have diferrent number of points, but are assumed not to
# cross each other and to be centered at (0,0). All points should have the
# same Z coordinate if the result is desired to be flat.

# Both rings should be sorted in the same order (clockwise or counter),
# whatever is required to get the right "out" direction. We assume that the
# angles are increasing or decreasing from zero in both lists.

# The clockwise (pointing down) or counterclockwise (pointing up) follows
# naturally from traversing the lists. We iterate over larger list. The point
# order in each facet is different if the larger list is inner or outer, so
# we need two cases.

# Note that angles are expressed in the range of [0, 2*PI].

def ring( inner, outer, facets ) :
	ni = len(inner)
	no = len(outer)
	if ni < no :
		# iterate over outer
		ii = 0
		ii_next = 1 
		io_next = 1 
		for io in range(0,no) :
			if math.fabs(outer[io].angle-inner[ii].angle) >= \
			   math.fabs(outer[io].angle-inner[ii_next].angle) :
				# advance to the next outer
				facets.append( Facet( outer[io], \
						inner[ii_next], inner[ii] ))
				#facets[len(facets)-1].print_xyz()
				ii += 1
				ii = ii % ni
				ii_next = ii + 1
				ii_next = ii_next % ni
			facets.append( \
				Facet( outer[io], outer[io_next], inner[ii] ))
			#facets[len(facets)-1].print_xyz()
			io_next += 1
			io_next = io_next % no
		# close the ring
		facets.append( Facet( outer[0], inner[0], inner[ni-1] ))
	elif ni > no :
		# iterate over inner
		ii_next = 1 
		io = 0
		io_next = 1 
		for ii in range(0,ni) :
			if math.fabs(inner[ii].angle-outer[io].angle) >= \
			   math.fabs(inner[ii].angle-outer[io_next].angle) :
				# advance to the next outer
				facets.append( Facet( inner[ii], \
						outer[io], outer[io_next] ))
				#facets[len(facets)-1].print_xyz()
				io += 1
				io = io % no
				io_next = io + 1
				io_next = io_next % no
			facets.append( \
				Facet( inner[ii], outer[io], inner[ii_next] ))
			#facets[len(facets)-1].print_xyz()
			ii_next += 1
			ii_next = ii_next % ni
		# close the ring
		facets.append( Facet( inner[0], outer[no-1], outer[0] ))
	else :
		# equal number of vertices, no need for logic
		for i in range(0,ni-1) : 
			facets.append( Facet(inner[i+1],inner[i],outer[i]) )
			facets.append( Facet(inner[i+1],outer[i],outer[i+1]) )
		facets.append( Facet( inner[0], inner[ni-1], outer[ni-1] ) )
		facets.append( Facet( inner[0], outer[ni-1], outer[0] ) )
				
# Makes a flat surface with a cross recess for a top of a screw head.
# Construction is from below i.e., "out" is down.
# Note that this means the actual angles are in clockwise order.
# recess is centered at XY origin. We assume that the number of perimeter
# vertices in "outer" list is large enough that a ring can be built between
# it and the recess surface vertices without lines crossing.

# This module builds recesses that try to correspond to the geometry
# actually used in machine screws in the market. The recess is wider at the
# bottom and the flat surface much more extensive. Inner angles are
# rounded.

# If any parameters should be tweaked to account for the printing
# artifacts, this should be done by the caller.
def cross_recess_surface( T, d_M, d_N, facets, outer ):
	M_surf = d_M/2 # "surf" refers to surface
	N_surf = d_N/2 # N/2 is more convenient than N
	eff_T = 0.9 *T
	M2 = 0.5 * M_surf 
	M_int = 0.50 * M_surf # "int" refers to internal
	N_int = 0.7*N_surf
	angle = math.atan(N_surf/M_surf)
	angle_i = math.atan(N_int/M_int)
	angle2 = math.atan(N_surf/M2)
	angle3 = math.atan(N_int/M_int)
	beta_s = (math.pi/2-2*angle2)/3
	beta_i = (math.pi/2-2*angle3)/3
	base_a = 0
	r_s = M_surf/math.cos(angle)
	r2 = M2/math.cos(angle2)
	r3 = r2 * math.cos(3*beta_s)/math.cos(beta_s)
	r_i = M_int/math.cos(angle3)  # inner recess radius
	outer.sort(key=lambda Vertex: Vertex.angle, reverse = True )
	# surface vertices and facets
	surf_perim = []
	surf_angle = [] # inner angle on surface
	for i in range(0,4) :
		surf_angle.append( Vertex( r2,base_a+angle2,0,am_cyl=True))
		surf_perim.append( Vertex( r_s,base_a+angle,0,am_cyl=True))
		surf_perim.append( Vertex( r_s,base_a-angle,0,am_cyl=True))
		surf_angle.append( Vertex( r2,base_a-angle2,0,am_cyl=True))
		surf_angle.append( Vertex( r3, \
			base_a-angle2-beta_s, 0, am_cyl=True))
		surf_angle.append( Vertex( r3, \
			base_a-angle2-2*beta_s, 0, am_cyl=True))
		base_a -= math.pi/2
		if base_a < 0 :
			base_a += 2*math.pi
	for i in range(0,4) :
		i_n = (i+1)%4
		g = [surf_perim[2*i+1]]
		g = g+ surf_angle[4*i+1:4*i+4]
		g.append( surf_angle[4*i_n] )
		g.append( surf_perim[2*i_n] )
		g.sort(key=lambda Vertex: Vertex.angle, reverse = False )
		facet_polygon( g, facets )

	for vtx in surf_perim :
		if vtx.angle > 2*math.pi :
			vtx.angle -= 2*math.pi 
		if vtx.angle < 0 :
			vtx.angle += 2*math.pi
	for vtx in surf_angle :
		if vtx.angle > 2*math.pi :
			vtx.angle -= 2*math.pi 
		if vtx.angle < 0 :
			vtx.angle += 2*math.pi
	surf_perim.sort(key=lambda Vertex: Vertex.angle, reverse = True )
	ring( surf_perim, outer, facets )
	# internal vertices and facets
	base_a = 0
	int_perim = [] # all vertices go here
	for i in range(0,4) :
		int_perim.append( Vertex( r_i,base_a+angle3,eff_T,am_cyl=True))
		int_perim.append( Vertex( r_i,base_a-angle3,eff_T,am_cyl=True))
		int_perim.append( Vertex( 0.5*r_i, \
			base_a-angle3-beta_i, T, am_cyl=True))
		int_perim.append( Vertex( 0.5*r_i, \
			base_a-angle3-2*beta_i, T, am_cyl=True))
		base_a -= math.pi/2
		if base_a < 0 :
			base_a += 2*math.pi
	for vtx in int_perim :
		if vtx.angle > 2*math.pi :
			vtx.angle -= 2*math.pi 
		if vtx.angle < 0 :
			vtx.angle += 2*math.pi
	# bottom star
	int_perim.sort(key=lambda Vertex: Vertex.angle, reverse = True )
	surf_perim.sort(key=lambda Vertex: Vertex.angle, reverse = True )
	facet_polygon( int_perim, facets, mid_z = T )
	# edge ramps
	for i in range(0,4) :
		facet_4vtx( \
		int_perim[4*i], \
		int_perim[(4*i-1)%16], \
		surf_perim[(2*i-1)%8], \
		surf_perim[(2*i)%8], \
		facets )
	for i in range(0,4) :
	# outer verticals
		facets.append( Facet( \
		int_perim[4*i], \
		surf_perim[2*i], \
		surf_angle[(4*i+1)%16] \
		) )
		facets.append( Facet( \
		surf_perim[2*i+1], \
		int_perim[(4*i+3)%16], \
		surf_angle[(4*i+4)%16] \
		) )
	for i in range(0,4) :
	# inner verticals
		facet_4vtx( \
		int_perim[(4*i+1)%16], \
		int_perim[4*i], \
		surf_angle[(4*i+1)%16], \
		surf_angle[(4*i+2)%16], \
		facets )
		facet_4vtx( \
		int_perim[(4*i+2)%16], \
		int_perim[4*i+1], \
		surf_angle[(4*i+2)%16], \
		surf_angle[(4*i+3)%16], \
		facets )
		facet_4vtx( \
		int_perim[(4*i+3)%16], \
		int_perim[4*i+2], \
		surf_angle[(4*i+3)%16], \
		surf_angle[(4*i+4)%16], \
		facets )
	return [ r_s, r_i, eff_T ]

# makes a cylinder of the specified diameter and height, dividing the
# perimeter into fn segments. Cylinder vertical axis is at [0,0], the base
# is at z=0.

# Vertical facets for the outer ring are made and appended to facets. Top
# and bottom faces are not made, but the vertices are stored in bottom and
# top lists and returned to the caller.

def cylinder_body( d, h, start_z, fn, facets ) :
	bottom = []
	top = []
	r = d/2
	angle_step = 2 * math.pi / fn
	for i in range(0,fn) :
		angle = i * angle_step
		bottom.append( Vertex( r, angle, start_z, am_cyl = True ) )
		top.append( Vertex( r, angle, start_z+h, am_cyl = True ) )
	for i in range(0,fn) : 
		facets.append( Facet( bottom[i], bottom[(i+1)%fn], top[i] ) )
		facets.append( Facet( bottom[(i+1)%fn],top[(i+1)%fn],top[i] ))
	return [ bottom, top ]

# hex_shell builds facet for a hex head or nut vertical six sided cylinder.
# the corners are optionally chamfered if delta is positive and either
# trunc_down or trunc_up or both are True.

# flat_diam is the distance between opposing flats (i.e., wrench size),
# height is the height of the cylinder and delta is the distance in each of
# the three sides of a vertex to which to make the chamfering triangle
# vertex.
def hex_shell( flat_diam, height, delta, trunc_down, trunc_up, facets ) :
	top_verts = []
	bottom_verts = []
	angle = 0
	diam = 2 * flat_diam / math.sqrt(3)
	eff_z = height

	if delta > 0 and (trunc_up or trunc_down) :
		# we'll truncate at least some corners.
		relax_d = diam/2 - delta
		y = delta * math.sqrt(3)
		angle_d = math.atan( y /relax_d )
		offvert_d = relax_d / math.cos(angle_d )
		vertical_d = delta
		top_tverts = []
		bottom_tverts = []
	elif delta < 1e-3 :
		trunc_down = False
		trunc_up = False

	# generate the points
	# if triangles are made, two points are on the plane and stored as
	# boundary points to be returned, but the third, located on the
	# corner vertical, is not and so is kept in a separate array.
	angle = 0
	for n in range( 0,6 ) :
		if not trunc_down :
			bottom_verts.append( Vertex( diam/2, angle, 0,\
					am_cyl = True ) )
		else :
			bottom_verts.append( \
				Vertex( offvert_d, angle-angle_d, 0, \
					am_cyl = True ) )
			bottom_verts.append( \
				Vertex( offvert_d, angle+angle_d, 0, \
					am_cyl = True ) )
			bottom_tverts.append( \
				Vertex( diam/2, angle, vertical_d, \
					am_cyl = True ) )
			
		if not trunc_up :
			top_verts.append( Vertex( diam/2, angle, height,\
					am_cyl = True ) )
		else :
			top_verts.append( \
				Vertex( offvert_d, angle-angle_d, height, \
					am_cyl = True ) )
			top_verts.append( \
				Vertex( offvert_d, angle+angle_d, height, \
					am_cyl = True ) )
			top_tverts.append( \
				Vertex( diam/2, angle, height-vertical_d, \
					am_cyl = True ) )
		angle += math.pi / 3
	
	# facets, depending on where we chamfer
	if not trunc_up and not trunc_down : # no chamfer
		for i in range( 0, 6 ) :
			facet_4vtx(
				bottom_verts[i], bottom_verts[(i+1)%6], \
				top_verts[(i+1)%6], top_verts[i], \
				facets ) 
	elif trunc_up and trunc_down : # chamfer both up and down
		ctr = 0
		# triangles first
		for i in range( 0, 6 ) :
			facets.append( \
				Facet( bottom_verts[ctr],bottom_verts[ctr+1],\
					bottom_tverts[i] ))
			facets.append( \
				Facet( top_verts[ctr+1],top_verts[ctr],\
					top_tverts[i] ))
			ctr += 2
		ctr = 0
		for i in range( 0, 6 ) :
			facet_4vtx(
				bottom_tverts[i], bottom_verts[(ctr+1)%12], \
				top_verts[(ctr+1)%12], top_tverts[i], \
				facets )
			facet_4vtx(
				bottom_verts[(ctr+1)%12], \
				bottom_verts[(ctr+2)%12], \
				top_verts[(ctr+2)%12], \
				top_verts[(ctr+1)%12], \
				facets )
			facet_4vtx(
				bottom_verts[(ctr+2)%12], \
				bottom_tverts[(i+1)%6], \
				top_tverts[(i+1)%6], \
				top_verts[(ctr+2)%12], \
				facets )
			ctr += 2

	elif trunc_down : # chamfer only down
		ctr = 0
		# triangles first
		for i in range( 0, 6 ) :
			facets.append( \
				Facet( bottom_verts[ctr],bottom_verts[ctr+1],\
					bottom_tverts[i] ))
			ctr += 2

		ctr = 0
		for i in range( 0, 6 ) :
			facets.append( \
				Facet( top_verts[i], bottom_tverts[i], \
					bottom_verts[(ctr+1)%12] ))
			facet_4vtx(
				bottom_verts[(ctr+1)%12], \
				bottom_verts[(ctr+2)%12], \
				top_verts[(i+1)%6], top_verts[i], \
				facets )
			facets.append( \
				Facet( bottom_verts[(ctr+2)%12], \
					bottom_tverts[(i+1)%6],\
					top_verts[(i+1)%6] ) )
			ctr += 2
	else : # chamfer only up
		ctr = 0
		# triangles first
		for i in range( 0, 6 ) :
			facets.append( \
				Facet( top_verts[ctr+1],top_verts[ctr],\
					top_tverts[i] ))
			ctr += 2

		ctr = 0
		for i in range( 0, 6 ) :
			facets.append( \
				Facet( top_verts[(ctr+1)%12], top_tverts[i], \
					bottom_verts[i] ))
			facet_4vtx(
				bottom_verts[i], bottom_verts[(i+1)%6], \
				top_verts[(ctr+2)%12], top_verts[(ctr+1)%12], \
				facets )
			facets.append( \
				Facet( top_tverts[(i+1)%6], \
					top_verts[(ctr+2)%12],\
					bottom_verts[(i+1)%6] ) )
			ctr += 2
	
	# need to fix any negative angles so the smallest angle is 0
	# otherwise, after sort, ring() won't connect properly at the end
	for vert in bottom_verts :
		if vert.angle < 0 :
			vert.angle += 2 * math.pi
	for vert in top_verts :
		if vert.angle < 0 :
			vert.angle += 2 * math.pi
	return [ bottom_verts, top_verts ] 
