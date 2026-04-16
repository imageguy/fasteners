
# actual fasteners and parts for fasteners
# By Nenad Rijavec.
# Distributed under MIT license.

from dimensions import *
from facets import *
from constructs import *
import math
import copy
import sys
from fractions import Fraction

# For the given screw, specified by a diameter, find it in the list and
# return a build screw. Original screw remains unmodified.
# if the screw can't be found, interpolate from the smaller and bigger
# next neighbors.
# diamstr can be either a float or a fraction.
def make_build_screw( am_metric, diamstr : str ) :
	if am_metric :
		screws = metric_screws
	else :
		screws = imperial_screws
	if '/' not in diamstr and not '#' in diamstr :
		diam = float( diamstr )
	elif not '#' in diamstr :
		parts = diamstr.strip().split(' ')
		if len(parts) == 1:
			diam = float(Fraction(parts[0]))
		elif len(parts) == 2:
			diam = int(parts[0]) + float(Fraction(parts[1]))
	else :
		# diam given as '#n', we just find it. return Nones if not
		# found
		for screw in screws :
			if screw.desc == diamstr :
				bld = copy.deepcopy(screw)
				bld.convert_to_metric()
				return [ screw, bld ]
		return [ None, None ]

	ii = 0
	lower = -1
	higher = -1
	bld = None
	# diam given as a number
	while ii < len(screws) and bld == None and higher == -1 :
		if math.fabs(screws[ii].diam - diam) < 1e-3 :
			orig = screws[ii]
			bld = copy.deepcopy(orig)
			if not bld.am_metric :
				bld.convert_to_metric()
			return [ orig, bld ]
		elif screws[ii].diam < diam :
			lower = ii
		elif higher == -1 and screws[ii].diam > diam :
			higher = ii
		ii += 1
	if bld == None and higher == -1 :
		# diam is larger than any in the list
		frac = diam / screws[lower].diam
		bld = copy.deepcopy(screws[lower])
		bld.diam = frac*bld.diam
		w = bld.pitches[bld.defpitch]
		if am_metric:
			w *= frac
			# 0.25mm increments
			bld.pitches = [ math.trunc(4*w)/4 ]
			bld.defpitch = 0
		else :
			w = w / frac
			if w < 5 :
				bld.pitches = [ math.trunc(4*w)/4 ]
			else :
				bld.pitches = [ math.trunc(w) ]
			bld.defpitch = 0

		bld.head_d = frac*bld.head_d
		bld.flat_h = frac*bld.flat_h
		bld.pan_h = frac*bld.pan_h
		w = frac*bld.hex_a
		if am_metric :
			# odd millimeter size
			bld.hex_a = 2 * math.trunc((w+1)/2) + 1
		else :
			# in 1/4 inch increments
			bld.hex_a = math.ceil(4*w)/4
		bld.hex_h = frac*bld.hex_h
		bld.shank_d = frac*bld.shank_d
		bld.cap_d = frac*bld.cap_d
		bld.cap_h = frac*bld.cap_h
		w = frac*bld.cap_s
		if am_metric :
			# odd millimeter size, rounded down
			bld.cap_s = 2 * math.trunc(w/2) + 1
		else :
			# in 1/4 inch increments, rounded up
			bld.cap_s = math.ceil(4*w)/4
		bld.cap_T = frac*bld.cap_T
		bld.M = frac*bld.M
		bld.T = frac*bld.T
		bld.N = frac*bld.N
		bld.desc = None
	elif bld == None and lower == -1 :
		# diam is smaller than any in the list
		frac = diam / screws[higher].diam
		bld = copy.deepcopy(screws[higher])
		bld.diam = frac*bld.diam
		w = bld.pitches[bld.defpitch]
		if am_metric:
			# 0.1mm increments
			w *= frac
			ww = math.trunc(10*w)/10 
			if ww < 0.1 :
				ww = 0.1
			bld.pitches = [ ww ]
			bld.defpitch = 0
		else :
			w = w / frac
			bld.pitches = [ math.trunc(w/frac) ]
			bld.defpitch = 0
		bld.head_d = frac*bld.head_d
		bld.flat_h = frac*bld.flat_h
		bld.pan_h = frac*bld.pan_h
		#bld.hex_a = frac*bld.hex_a just take it from the smallest
		bld.hex_h = frac*bld.hex_h
		bld.shank_d = frac*bld.shank_d
		# cap head remains taken from the lowest predefined
		bld.M = frac*bld.M
		bld.T = frac*bld.T
		bld.N = frac*bld.N
		bld.desc = None
	elif bld == None :
		# we average nearest neighbors
		# pitches are left from the lower neighbor
		dlow = screws[lower].diam
		dhigh = screws[higher].diam
		delta = dhigh-dlow
		frac = (dhigh-diam)/delta
		bld = copy.deepcopy(screws[lower])
		bld.diam = frac*bld.diam+(1-frac)*screws[higher].diam
		bld.head_d = frac*bld.head_d+(1-frac)*screws[higher].head_d
		bld.flat_h = frac*bld.flat_h+(1-frac)*screws[higher].flat_h
		bld.pan_h = frac*bld.pan_h+(1-frac)*screws[higher].pan_h
		# hex_a is taken from the larger neighbor
		bld.hex_a = screws[higher].hex_a
		bld.hex_h = frac*bld.hex_h+(1-frac)*screws[higher].hex_h
		# cap_s is the key hex_a, it stays taken from the lower
		bld.shank_d = frac*bld.shank_d+ \
				(1-frac)*screws[higher].shank_d
		bld.M = frac*bld.M+(1-frac)*screws[higher].M
		bld.T = frac*bld.T+(1-frac)*screws[higher].T
		bld.N = frac*bld.N+(1-frac)*screws[higher].N
		bld.desc = None
	bld.am_interpolated = True
	if bld.desc == None :
		# interpolated screw, set desc from diam
		if am_metric :
			bld.desc = 'M'+str("{:.5g}".format(bld.diam))
		else :
			#gives the inch + fraction, 1/64 precision
			d64 = int(bld.diam*64) #in 64ths of an inch
			bld.desc = ''
			# it might have not been specified as fraction, in
			# which case we use decimal.
			if math.fabs(bld.diam - math.trunc(d64/64)) > 1e-3 :
				# use decimal
				bld.desc = str("{:.3g}".format(bld.diam))
			else :
				# OK to use fraction
				d_int = int(d64/64)
				if d_int > 0 :
					bld.desc = str(d_int)
				d64 -= 64*d_int
				if d64 > 0 :
					bld.desc += str(Fraction(d64,64))
		orig = copy.deepcopy(bld)
		if not bld.am_metric :
			bld.convert_to_metric()
	return [ orig, bld ]

# For the given nut, specified by a diameter, find it in the list and
# return a build nut. Original nut remains unmodified.
# if the nut can't be found, interpolate from the smaller and bigger
# next neighbors.
# diamstr can be either a float or a fraction.
def make_build_nut( am_metric, diamstr : str ) :
	if am_metric :
		nuts = metric_nuts
	else :
		nuts = imperial_nuts
	if '/' not in diamstr and not '#' in diamstr :
		diam = float( diamstr )
	elif not '#' in diamstr :
		parts = diamstr.strip().split(' ')
		if len(parts) == 1:
			diam = float(Fraction(parts[0]))
		elif len(parts) == 2:
			diam = int(parts[0]) + float(Fraction(parts[1]))
	else :
		# diam given as '#n', we just find it. return None if not
		# found
		for nut in nuts :
			if nut.desc == diamstr :
				bld = copy.deepcopy(nut)
				orig = copy.deepcopy(nut)
				bld.convert_to_metric()
				return [ orig, bld ]
		return [None, None ]

	ii = 0
	lower = -1
	higher = -1
	bld = None
	while ii < len(nuts) and bld == None and higher == -1 :
		if math.fabs(nuts[ii].diam - diam) < 1e-3 :
			orig = nuts[ii]
			bld = copy.deepcopy(orig)
			if not bld.am_metric :
				bld.convert_to_metric()
			return [ orig, bld ]
		elif nuts[ii].diam < diam :
			lower = ii
		elif higher == -1 and nuts[ii].diam > diam :
			higher = ii
		ii += 1
	if bld == None and higher == -1 :
		# diam is larger than any in the list
		frac = diam / nuts[lower].diam
		bld = copy.deepcopy(nuts[lower])
		bld.diam = diam
		w = bld.pitches[bld.defpitch]
		if am_metric:
			w *= frac
			# 0.25mm increments
			bld.pitches = [ math.trunc(4*w)/4 ]
			bld.defpitch = 0
		else :
			w = w / frac
			if w < 5 :
				bld.pitches = [ math.trunc(4*w)/4 ]
			else :
				bld.pitches = [ math.trunc(w) ]
			bld.defpitch = 0
		w = frac*bld.hex_a
		if am_metric :
			# odd millimeter size
			bld.hex_a = 2 * math.trunc((w+1)/2) + 1
		else :
			# in 1/4 inch increments
			bld.hex_a = math.ceil(4*w)/4
		bld.hex_h = frac*bld.hex_h
		bld.desc = None
	elif bld == None and lower == -1 :
		# diam is smaller than any in the list
		frac = diam / nuts[higher].diam
		bld = copy.deepcopy(nuts[higher])
		bld.diam = frac*bld.diam
		w = bld.pitches[bld.defpitch]
		if am_metric:
			# 0.1mm increments
			w *= frac
			ww = math.trunc(10*w)/10 
			if ww < 0.1 :
				ww = 0.1
			bld.pitches = [ ww ]
			bld.defpitch = 0
		else :
			w = w / frac
			bld.pitches = [ math.trunc(w/frac) ]
			bld.defpitch = 0
		w = frac*bld.hex_a
		if am_metric :
			#  half millimeter size
			bld.hex_a = math.ceil(2*w)/2
		else :
			# in 1/16 inch increments
			bld.hex_a = math.ceil(16*w)/16
		bld.hex_h = frac*bld.hex_h
		bld.desc = None
	elif bld == None :
		# we average nearest neighbors
		# pitches are left from the lower neighbor
		dlow = nuts[lower].diam
		dhigh = nuts[higher].diam
		delta = dhigh-dlow
		frac = (dhigh-diam)/delta
		bld = copy.deepcopy(nuts[lower])
		bld.diam = frac*bld.diam+(1-frac)*nuts[higher].diam
		# hex is taken from the higher neighbor
		bld.hex_a = nuts[higher].hex_a
		bld.hex_h = frac*bld.hex_h+(1-frac)*nuts[higher].hex_h
		bld.desc = None
	bld.am_interpolated = True
	if bld.desc == None :
		# interpolated screw, set desc from diam
		if am_metric :
			bld.desc = 'M'+str("{:.5g}".format(bld.diam))
		else :
			#gives the inch + fraction, 1/64 precision
			d64 = int(bld.diam*64) #in 64ths of an inch
			bld.desc = ''
			# it might have not been specified as fraction, in
			# which case we use decimal.
			if math.fabs(bld.diam - math.trunc(d64/64)) > 1e-3 :
				# use decimal
				bld.desc = str("{:.3g}".format(bld.diam))
			else :
				# OK to use fraction
				d_int = int(d64/64)
				if d_int > 0 :
					bld.desc = str(d_int)
				d64 -= 64*d_int
				if d64 > 0 :
					bld.desc += str(Fraction(d64,64))
		orig = copy.deepcopy(bld)
		if not bld.am_metric :
			bld.convert_to_metric()
	return [ orig, bld ]

# sequence for each segment starts at the bottom of the trough and end on
# the bottom of the next trough. Even though it builds vertically, the
# algorithm variables are in the thread context, with height being the
# thread height, radial out as we build it.
def thread_segment( diam, pitch, start_z, length, fn, facets, \
	recess_top = True, recess_bottom = False ) :
	r_out = diam/2
	h = pitch * math.sqrt(3) / 2
	r_in = r_out - 5 * h / 8
	angle_d = 2 * math.pi / fn
	z_slope = 5 * pitch / 16
	z_peak = pitch / 8
	z_trough = pitch / 4
	z_step = pitch / fn
	slope = math.atan( pitch / (2*math.pi * r_out ) )
	top_z = start_z + length
	ctr = 0 # where we are in top and bottom arrays
	angle = 0 # curent angle
	sqrt3 = math.sqrt(3)
	
	# vertices to be used as the next pitch bottom
	prev_vtx = [ None, None, None, None, None ]
	# if not recess_bottom, used just in the first pitch, Z=start_z
	if not recess_bottom :
		curr_bottom = start_z - pitch
		vtx = [ Vertex( r_in, angle, curr_bottom, am_cyl = True ) ]
		vtx.append( Vertex( r_in, angle, vtx[0].z+z_trough, am_cyl = True ))
		vtx.append( Vertex( r_out, angle, vtx[1].z+z_slope, am_cyl = True ))
		vtx.append( Vertex( r_out, angle, vtx[2].z+z_peak, am_cyl = True ))
		vtx.append( Vertex( r_in, angle, start_z, am_cyl = True) )
		bottom_verts = [ vtx[4].deepcopy() ]
		
		angle += angle_d
		curr_bottom += z_step
		ctr = 1
	#initial segment
	while not recess_bottom and curr_bottom - 1e-6 <= start_z :
		for vt in vtx :
			vt.z += z_step 
			if math.fabs(vt.z - start_z) < MIN :
				vt.z = start_z
			vt.change_cyl( vt.r, angle )
		i = 0
		while i < 5 and vtx[i].z < start_z :
			i += 1
		# make the base vertex below
		wvt = vtx[i].deepcopy()
		wvt.z = start_z
		if i == 2 :
			wvt.change_cyl( wvt.r - (vtx[i].z-start_z)*sqrt3, \
				wvt.angle )
		elif i == 4 :
			wvt.change_cyl( wvt.r + (vtx[i].z-start_z)*sqrt3, \
				wvt.angle )
		bottom_verts.append( wvt )
		if i < 5 and prev_vtx[i] == None :
			# this is the first time this vertex is above the
			# base. Only one facet is below - a triangle,
			# instead of rectangle. Skip this if the current
			# vertex is right on the base height
			if vtx[i].z > start_z :
				facets.append( Facet( bottom_verts[ctr-1], \
					bottom_verts[ctr], \
					vtx[i].deepcopy() ) )
		elif prev_vtx[i].z > start_z :
			facet_4vtx( bottom_verts[ctr-1], \
				bottom_verts[ctr], \
				vtx[i].deepcopy(), \
				prev_vtx[i], \
				facets )
		else :
			facets.append( Facet( bottom_verts[ctr-1], \
				bottom_verts[ctr], \
					vtx[i].deepcopy() ) )

		# facets above the current facet
		for n in range(i,4) :
			if prev_vtx[n] == None :
				facet_4vtx( bottom_verts[ctr-1],
					vtx[n].deepcopy(), \
					vtx[n+1].deepcopy(), \
					prev_vtx[n+1], facets )
			else :
				facet_4vtx( prev_vtx[n], \
					vtx[n].deepcopy(), \
					vtx[n+1].deepcopy(), \
					prev_vtx[n+1], facets )

		for i in range(0,5) :
			if vtx[i].z >= start_z - 1e-5 :
				prev_vtx[i] = vtx[i].deepcopy()
			
		ctr += 1
		angle += angle_d
		curr_bottom += z_step
		if math.fabs( curr_bottom - start_z ) < MIN :
			curr_bottom = start_z
	fn_decr = int(fn/3)
	decr= (r_out-r_in) / fn_decr
	if recess_bottom :
#		For recessed bottom start thread, we start with the bottom
#		point at start_z-z_through, since we want to start with the
#		slope, not trough. This requires all the extra logic below,
#		so we connect the end of the first pitch properly. Each
#		thread segment is connected to the bottom edge and this
#		connection is what has to be done properly when the
#		connection rectangle abuts the start of the thread. The
#		first connection is a Facet, not a rectangle.
		curr_bottom = start_z
		wrk_r = r_in
		angle = 0
		bottom_verts = []
		for i in range(0,fn) :
			bottom_verts.append( \
			Vertex( r_in, i*angle_d, start_z, am_cyl = True ))
		# we start the points for iteration
		vtx = [ Vertex( r_in, angle, curr_bottom-z_trough, am_cyl = True ) ]
		vtx.append( Vertex( r_in, angle, vtx[0].z+z_trough, am_cyl = True ))
		vtx.append( Vertex( r_in+decr, angle, vtx[1].z+z_slope, am_cyl = True ))
		vtx.append( Vertex( r_in+decr, angle, vtx[2].z+z_peak, am_cyl = True ))
		vtx.append( Vertex( r_in, angle, vtx[3].z+z_slope, am_cyl = True) )
		# first facet line
		facets.append( Facet( bottom_verts[fn-1], \
			vtx[1].deepcopy(), vtx[2].deepcopy() ))
		facets.append( Facet( bottom_verts[fn-1], \
			vtx[2].deepcopy(), vtx[3].deepcopy() ))
		facets.append( Facet( bottom_verts[fn-1], \
			vtx[3].deepcopy(), vtx[4].deepcopy() ))
		
		for i in range(0,5) :
			prev_vtx[i] = vtx[i].deepcopy()
		ctr = 0 # prev is on ctr = 0
		angle += angle_d
		while curr_bottom < start_z + pitch - 1e-6 :
			wrk_r += decr
			if wrk_r > r_out :
				wrk_r = r_out
			for i in range(0,5) :
				vtx[i].z += z_step
				if i==2 or i == 3 :
					vtx[i].change_cyl( wrk_r, angle )
				else :
					vtx[i].change_cyl( r_in, angle )
			# connect to bottom
			if ctr > 0 and ctr < fn-1 :
				if prev_vtx[0].z < start_z :
					facet_4vtx(
					bottom_verts[ctr], \
					bottom_verts[ctr+1],\
						vtx[1].deepcopy(), \
						prev_vtx[1].deepcopy(), \
						facets )
				elif prev_vtx[0].z < start_z + z_step :
					facets.append( Facet(
					bottom_verts[ctr], \
					bottom_verts[ctr+1],\
						vtx[0].deepcopy() ) )
					facet_4vtx(
						bottom_verts[ctr], \
						vtx[0].deepcopy(),\
						vtx[1].deepcopy(), \
						prev_vtx[1].deepcopy(), \
						facets )
				else :
					facet_4vtx(
					bottom_verts[ctr], \
					bottom_verts[ctr+1],\
						vtx[0].deepcopy(), \
						prev_vtx[0].deepcopy(), \
						facets )
			elif ctr == 0 :
				facets.append( \
				Facet( bottom_verts[0], bottom_verts[1], \
				vtx[1].deepcopy() ))


			if  vtx[0].z >=start_z + 2* z_step :
				facet_4vtx( prev_vtx[0], \
					vtx[0].deepcopy(), \
					vtx[1].deepcopy(), \
					prev_vtx[1], facets )
			for n in range(1,4) :
				#breakpoint()
				#if  vtx[n].z >=start_z + z_step :
				#if vtx[n].z >=start_z + 2*z_step :
				facet_4vtx( prev_vtx[n], \
					vtx[n].deepcopy(), \
					vtx[n+1].deepcopy(), \
					prev_vtx[n+1], facets )
			save_prev = prev_vtx[0]
			for i in range(0,5) :
				prev_vtx[i] = vtx[i].deepcopy()
		
			ctr += 1
			ctr = ctr % fn
			angle += angle_d
			if angle > 2 * math.pi :
				angle -= 2 * math.pi
			curr_bottom += z_step
		if vtx[0].z >= start_z :
			facets.append( Facet( bottom_verts[fn-1], \
				vtx[0].deepcopy(), save_prev.deepcopy() ))
			

	else :
		# the point at angle = 0 = 2*pi is twice in bottom, remove dupe
		bottom_verts.remove( bottom_verts[len(bottom_verts)-1] )

	# inner threads
	
	ctr = 0
	decr= (r_out-r_in) / fn_decr
	pitch_trigger = (1 + fn_decr/fn)*pitch
	wrk_r = r_out
	save_verts = []
	while  vtx[4].z + z_step < top_z - 1e-6 : # regular iterations
		if recess_top and top_z - curr_bottom < pitch_trigger :
			wrk_r -= decr
			if wrk_r < r_in :
				wrk_r = r_in
		for i in range(0,5) :
			vtx[i].z += z_step 
			if recess_top and (i == 2 or i == 3 ) :
				vtx[i].change_cyl( wrk_r, angle )
			else : 
				vtx[i].change_cyl( vtx[i].r, angle )
		if top_z - vtx[4].z < pitch  + 1e-6 :
			save_verts.append(vtx[4].deepcopy() )
		for n in range(0,4) :
			vv = vtx[n+1].deepcopy()
			if vv.z > top_z and not recess_top :
				vv.z = top_z
			ww = vtx[n].deepcopy()
			facet_4vtx( prev_vtx[n], \
				ww, \
				vv, \
				prev_vtx[n+1], facets )
		saved_vtx = prev_vtx[4].deepcopy()
		for i in range(0,5) :
			prev_vtx[i] = vtx[i].deepcopy()
		
		ctr += 1
		ctr = ctr % fn
		angle += angle_d
		if angle > 2 * math.pi :
			angle -= 2 * math.pi
		curr_bottom = vtx[0].z


	# end operations to finish the top

	top_verts = []
	angle0 = angle

	if recess_top :
		for n in range(0,fn) :
			top_verts.append( \
				Vertex( r_in, \
				angle, top_z, am_cyl=True ))
			angle += angle_d
			if angle > 2*math.pi :
				angle -= 2*math.pi
		facets.append( Facet( \
			vtx[0], save_verts[0], top_verts[0] ) )
		facets.append( Facet( \
			vtx[1], vtx[0], top_verts[0] ) )
		facets.append( Facet( \
			vtx[2], vtx[1], top_verts[0] ) )
		facets.append( Facet( \
			vtx[3], vtx[2], top_verts[0] ) )
		facets.append( Facet( \
			vtx[4], vtx[3], top_verts[0] ) )
		for n in range(0,fn-1) :
			facet_4vtx( save_verts[n], \
				save_verts[n+1], \
				top_verts[n+1],
				top_verts[n], facets )
		facets.append( Facet(  \
		save_verts[fn-1], \
		top_verts[0], \
			top_verts[fn-1] ))

		return [ bottom_verts,top_verts ]


	# top is not recessed
	ctr = 0
	ignore = 5
	if prev_vtx[4].z > top_z :
		prev_vtx[4].z = top_z
	decr = 0
	eff_bottom = curr_bottom
	while ctr < fn :
		for i in range(0,5) :
			vtx[i].z += z_step 
			vtx[i].change_cyl( vtx[i].r, angle )
		i = ignore-1
		while i >= 0 and vtx[i].z >= top_z  :
			i -= 1
		if i < ignore-1 and vtx[i].z < top_z : 
			i += 1
		if vtx[i].z > top_z :
			if i == 2 :
				vtx[i].change_cyl( \
					vtx[i].r + (top_z-vtx[i].z)*sqrt3, \
					vtx[i].angle )
			elif i == 4 :
				vtx[i].change_cyl( \
					vtx[i].r - (top_z-vtx[i].z)*sqrt3, \
					vtx[i].angle )
		vtx[i].z = top_z

		top_verts.append( vtx[i].deepcopy() )
		
		if i < ignore - 1 : 
			# new point, add facet to the left
			facets.append( Facet( \
				top_verts[ctr], \
				top_verts[ctr-1], \
				prev_vtx[i] ) )
			ignore -= 1

		for n in range(0,i) :
			facet_4vtx( prev_vtx[n], \
				vtx[n].deepcopy(), \
				vtx[n+1].deepcopy(), \
				prev_vtx[n+1], facets )
		for n in range(0,ignore) :
			prev_vtx[n] = vtx[n].deepcopy()
		
		ctr += 1
		#ctr = ctr % fn
		angle += angle_d
		if angle > 2 * math.pi :
			angle -= 2 * math.pi
		curr_bottom += z_step
	# add the last facet
	facets.append( Facet( vtx[0], top_verts[0], \
		top_verts[len(top_verts)-1] ) )
	return [ bottom_verts, top_verts ]

# hex_head builds a hex_shell with chamfer on the bottom. Bottom is set at
# z=0 and closed. Top is left open, but the perimeter is returned. Given
# dimensions are not modified - any changes needed to account for printing
# are assumed to have been handled by the caller.
# Top perimeter vertex list should not be assumed to be in a particular
# order.
def hex_head( hex_a, hex_h, hex_adj, facets ) :
	[bot, top] = hex_shell( hex_a+hex_adj, hex_h, 0.07*hex_a,
						True, False, facets )
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	facet_polygon( bot, facets )
	return top

# cap_head builds a cap_shell with chamfer on the bottom. Bottom is set at
# z=0 and closed. Top is left open, but the perimeter is returned. Given
# dimensions are not modified - any changes needed to account for printing
# are assumed to have been handled by the caller.
# Top perimeter vertex list should not be assumed to be in a particular
# order.
def cap_head( cap_d, cap_h, h_adj, cap_s, cap_T, hex_adj, fn, facets ) :
	n1 = len(facets)
	cap_h += h_adj
	[h_bot, h_top] = hex_shell( cap_s+hex_adj, 1.2*cap_T, 0,
						False, False, facets )
	# reverse the shell so it faces in
	for n in range(n1, len(facets) ) :
		facets[n].reverse()
	# close the hex on top
	h_top.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	facet_polygon( h_top, facets, mid_z = 1.5*cap_T )
	# head body
	[bot_cyl, top_cyl] = cylinder_body( cap_d, cap_h, 0, fn, facets )
	h_bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	bot_cyl.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring( h_bot, bot_cyl, facets )
	return top_cyl

# pan_head builds a modified pan head with a cross recess. The bottom is set at
# z=0 and closed. Top is left open, but the perimeter is returned. Given
# dimensions are not modified - any changes needed to account for printing
# are assumed to have been handled by the caller.
# Top perimeter vertex list should not be assumed to be in a particular
# order.
# Real pan head has a curved top, so it's unsuitable to be a base for a
# 3d-printed screw. We flatten the top for better adhesion.
def pan_head( head_d, pan_h, h_adj, T, M, N, fn, facets ) :
	delta = (head_d-M)/2
	pan_h += h_adj
	T_mod = 0.8 * T # we make cross-recces a "little" shallower
	r_bot = M/2 + delta/2
	r1 = M/2 + 0.6 * delta
	r2 = M/2 + 0.95 * delta
	z1 = pan_h/12
	z2 = 0.3*pan_h
	zc = 9*pan_h/16
	bot = []
	ring1 = []
	ring2 = []
	for n in range(0,fn) :
		bot.append( Vertex( r_bot, 2*n*math.pi/fn, 0, am_cyl=True))
		ring1.append( Vertex( r1, 2*n*math.pi/fn, z1, am_cyl=True))
		ring2.append( Vertex( r2, 2*n*math.pi/fn, z2, am_cyl=True))
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	[r_s, r_i, eff_T ] = cross_recess_surface( T_mod, M, N, facets, bot )
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring1.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring( bot, ring1, facets )
	ring2.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring( ring1, ring2, facets )
	[bot_cyl, top] = cylinder_body( head_d, pan_h-zc, zc, fn, facets )
	bot_cyl.sort( key=lambda Vertex: Vertex.angle, reverse = True)
	ring( ring2, bot_cyl, facets )
	return top

# flat_head builds a flat head with a cross recess. The bottom is set at
# z=0 and closed. Top is left open, but the perimeter is returned. Given
# dimensions are not modified - any changes needed to account for printing
# are assumed to have been handled by the caller.
# Top perimeter vertex list should not be assumed to be in a particular
# order.
# Note that metric screws have 90 deg recess angle, while imperial screws
# have 80 deg angle. The head height is computed so the specified angle
# meets the specified screw body or shank diam.
# If an extra height is specified via h_adj, the head_d is increased to
# keep the same head angle.
def flat_head( head_d, h_adj, head_angle, diam, T, M, N, fn, facets ) :
	T_mod = 0.8 * T # we make cross-recces a "little" shallower
	top = []
	bot = []
	bot2 = []
	lower_cyl_h = 0.2
	angle = 0
	angle_d = 2 * math.pi / fn
	R = head_d / 2
	r_d = diam / 2 # screw or shank radius
	z_orig = (R-r_d) / math.tan(head_angle/2)
	z = z_orig + h_adj
	fac = z/z_orig
	R *= fac
	for n in range( 0, fn ) :
		bot.append( Vertex( R, angle, 0, am_cyl = True ) )
		bot2.append( Vertex( R, angle, lower_cyl_h, am_cyl = True ) )
		angle += angle_d
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = False)
	[r_s, r_i, eff_T ] = cross_recess_surface( T_mod, M, N, facets, bot )
	#z = (R-r_d) / math.tan(head_angle/2)
	r_c = r_d 
	angle = 0
	for n in range( 0, fn ) :
		top.append( Vertex( r_c, angle, z, am_cyl = True ) )
		angle += angle_d
	
	bot.sort( key=lambda Vertex: Vertex.angle, reverse = True )
	bot2.sort( key=lambda Vertex: Vertex.angle, reverse = True )
	ring( bot, bot2, facets )
	bot2.sort( key=lambda Vertex: Vertex.angle, reverse = False )
	top.sort( key=lambda Vertex: Vertex.angle, reverse = False )
	ring( top, bot2, facets )

	# eff_T gives the z where the actual recess ends. This is
	# generally higher than the actual head height, so it intrudes
	# into the screw or bolt body. This makes for a weak point. The
	# commented-out code below adds a intermediate collar between the
	# head and screw body. However, this really doesn't add any extra
	# meat to the cylinder and also makes a flat-headed bolt not fully
	# fit into the shank_d-sized hole.

	""" #b
	eff_T += 0.2
	if z < eff_T : 
		collar = []
		angle = 0
		for n in range( 0, fn ) :
			collar.append( 
				Vertex( 0.1+diam/2, angle, eff_T,
					am_cyl = True ) )
			angle += angle_d
		collar.sort( key=lambda Vertex: Vertex.angle, reverse=False )
		ring( collar, top, facets )
		return collar
	else :
		return top
	""" #e
	return top
