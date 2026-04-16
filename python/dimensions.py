
# Defines the known fasteners, i.e, dimensions and pitches. Any fastener
# not in the lists here is built by interpolating.
# By Nenad Rijavec.
# Distributed under MIT license.

import math

# Bolt thread lengths, d_nom means "nominal diameter" :
# imperial: L_thd = 2d_nom+1/4in if L <= 6in, 2d_nom+1/2in otherwise
# metric: L_thd = 2d_nom+6mm if L <=125mm, 2d_nom+12mm if 125<L<200mm, and
# 2d_nom+25mm otherwise

# computations are unit-agnostic, just the logic differs between mm and in

def bolt_thread_length( total_l, diam, am_metric ) :
	if am_metric :
		if total_l < 125 :
			return 2 * diam + 6
		elif total_l < 200 :
			return 2 * diam + 12
		else :
			return 2 * diam + 25
	else :
		if total_l <= 6 :
			return 2 * diam + 0.25
		else :
			return 2 * diam + 0.5


# machine screw with dimensions and cross recess data
# we only build screws with flat surface, "pan" has a flattened top, but
# different height than flat head and no countersinking.
# pitches go from coarse to fine
# shank_d is as defined in ASME for imperial bolts. The smallest specified
# bolt is 1/4 in. For number sizes, value is approximated from metric
# bolts of similar dimensions.

class Screw:
	def __init__(self, desc, diam, pitch, defpitch, head_d, 
			flat_h, pan_h, hex_a, hex_h,
			cap_d, cap_h, cap_s, cap_T,
			shank_d, M, T, N,
			am_metric = False) :
		self.desc = desc
		self.diam = diam
		self.pitches = pitch # array of TPI or pitches
		self.defpitch = defpitch # index of default pitch
		self.head_d = head_d
		self.flat_h = flat_h
		self.pan_h = pan_h
		self.hex_a = hex_a
		self.hex_h = hex_h
		self.cap_d = cap_d
		self.cap_h = cap_h
		self.cap_s = cap_s
		self.cap_T = cap_T
		self.desc = desc
		self.shank_d = shank_d
		self.M = M
		self.T = T
		self.N = N
		self.am_interpolated = False
		self.am_metric = am_metric
		if am_metric :
			self.flat_angle = math.pi / 2
		else :
			self.flat_angle = 80 * math.pi / 180

	# convert imperial screw to metric. All dimensions are converted to 
	# mm, while unc, unf and unef are converted from TPI to pitch.
	# "converted" is added to description
	def convert_to_metric( self ) :
		self.desc += ' converted'
		self.diam *= 25.4
		self.head_d *= 25.4
		for i  in range(0,len(self.pitches)) :
			self.pitches[i] = 25.4 / self.pitches[i] 
		self.flat_h *= 25.4
		self.pan_h *= 25.4
		self.hex_a *= 25.4
		self.hex_h *= 25.4
		self.cap_d *= 25.4
		self.cap_h *= 25.4
		self.cap_s *= 25.4
		self.cap_T *= 25.4
		self.shank_d *= 25.4
		self.M *= 25.4
		self.T *= 25.4
		self.N *= 25.4
		self.am_metric = True
	def print_vars( self ) :
		print(  'size: ', self.desc, \
		(lambda x : " metric" if x else " imperial")(self.am_metric),\
		' diam: ', str("{:.2f}".format(self.diam)))
		pitchstr= 'pitches : '
		for pitch in self.pitches :
			pitchstr += \
		str((lambda x,y :  str("{:.4f}".format(y)) if x else str(y))\
			(self.am_metric, pitch)) + ' '
		print( pitchstr )
		print( \
		'head_d: ', str("{:.6g}".format(self.head_d)), \
		'\nflat_h:', str("{:.6g}".format(self.flat_h)), \
		' pan_h: ', str("{:.6g}".format(self.pan_h)), \
		' hex_a: ', str("{:.6g}".format(self.hex_a)), \
		' hex_h: ', str("{:.6g}".format(self.hex_h)), \
		'\ncap_d: ', str("{:.6g}".format(self.cap_d)), \
		' cap_h: ', str("{:.6g}".format(self.cap_h)), \
		' cap_s: ', str("{:.6g}".format(self.cap_s)), \
		' cap_T: ', str("{:.6g}".format(self.cap_T)), \
		'\nM: ', str("{:.6g}".format(self.M)), \
		' T: ', str("{:.6g}".format(self.T)), \
		' N: ', str("{:.6g}".format(self.N)) )
		

class Nut:
	def __init__(self, desc, diam, pitch, defpitch, hex_a, hex_h, \
			am_metric = False) :
		self.desc = desc
		self.diam = diam
		self.pitches = pitch # array of TPI or pitches
		self.defpitch = defpitch # index of default pitch
		self.hex_a = hex_a
		self.hex_h = hex_h
		self.am_interpolated = False
		self.am_metric = am_metric
	# convert imperial nut to metric. All dimensions are converted to mm,
	# while unc, unf and unef are converted from TPI to pitch.
	# "converted" is added to description
	def convert_to_metric( self ) :
		self.desc += ' converted'
		self.diam *= 25.4
		for i  in range(0,len(self.pitches)) :
			self.pitches[i] = 25.4 / self.pitches[i] 
		self.hex_a *= 25.4
		self.hex_h *= 25.4
		self.am_metric = True
	def print_vars( self ) :
		print(  'size: ', self.desc, \
		(lambda x : " metric" if x else " imperial")(self.am_metric),\
		' diam: ', str("{:.2f}".format(self.diam)))
		pitchstr= 'pitches : '
		for pitch in self.pitches :
			pitchstr += \
		str((lambda x,y :  str("{:.4f}".format(y)) if x else str(y))\
			(self.am_metric, pitch)) + ' '
		print( pitchstr )
		print( \
		'hex_a: ', str("{:.6g}".format(self.hex_a)), \
		' hex_h: ', str("{:.6g}".format(self.hex_h)) )
		
imperial_screws = [ 
Screw( '#5',0.1250,[40,44],0,0.237, #desc, diam, pitch, def, head_d
	0.075,0.085, 0.25, 0.07, # flat_h, pan_h, hex_a, hex_h
	0.2050,0.1250,0.0951,0.0570, # cap_d, cap_h, cap_s, cap_T
	0.14,0.169,0.094,0.035 ), # shank diam, M, T, N

Screw( '#6',0.1380,[32,40],0,0.262, #desc, diam, pitch, def, head_d
	0.083,0.095,0.3125, 0.10, # flat_h, pan_h, hex_a, hex_h
	0.2259,0.1379,0.1094,0.0640, # cap_d, cap_h, cap_s, cap_T
	0.15,0.188,0.106,0.038 ), # shank diam, M, T, N

Screw( '#8',0.1640,[32,36],0,0.312, #desc, diam, pitch, def, head_d
	0.100,0.112, 0.343, 0.11, # flat_h, pan_h, hex_a, hex_h
	0.2700,0.1640,0.1406,0.0770, # cap_d, cap_h, cap_s, cap_T
	0.175,0.224,0.124,0.043 ), # shank diam, M, T, N

Screw( '#10',0.19,[24,32],0,0.362, #desc, diam, pitch, def, head_d
	0.116,0.128, 0.375, 0.12, # flat_h, pan_h, hex_a, hex_h
	0.3120,0.1900,0.1562,0.0900, # cap_d, cap_h, cap_s, cap_T
	0.21,0.260,0.148,0.048 ), # shank diam, M, T, N

Screw( '#12',0.216,[24,28,32],0,0.412, #desc,diam,pitch,def,head_d, 
	0.132,0.145, 0.4375, 0.155, # flat_h, pan_h, hex_a, hex_h
	0.3392,0.2159,0.1875,0.1029, # cap_d, cap_h, cap_s, cap_T
	0.225,0.297,0.172,0.054 ), # shank diam, M, T, N

Screw( '1/4',0.25,[20,28,32],0,0.477, #desc, diam, pitch,def,head_d, 
	0.153,0.169, 0.4375, 0.19, # flat_h, pan_h, hex_a, hex_h
	0.3750,0.2500,0.1875,0.1200, # cap_d, cap_h, cap_s, cap_T
	0.26,0.344,0.195,0.061 ), # shank diam, M, T, N

Screw( '5/16',0.3125,[18,24,32],0,0.597, #desc,diam,pitch,def,head_d, 
	0.191,0.210, 0.5, 0.23, # flat_h, pan_h, hex_a, hex_h
	0.4690,0.3120,0.25,0.1509, # cap_d, cap_h, cap_s, cap_T
	0.324,0.432,0.252,0.074 ), # shank diam, M, T, N

Screw( '3/8',0.375,[16,24,32],0,0.717, #desc, diam,pitch,def,head_d, 
	0.230,0.253, 0.5625, 0.295, # flat_h, pan_h, hex_a, hex_h
	0.5620,0.3750,0.3125,0.1820, # cap_d, cap_h, cap_s, cap_T
	0.388, 0.509,0.302,0.086 ), # shank diam, M, T, N

Screw( '7/16',0.4375,[14,20,28],0,0.760, #desc, diam,pitch,def,head_d, 
	0.223,0.295, 0.6875, 0.3125,  # flat_h, pan_h, hex_a, hex_h
	0.6559,0.4415,0.375,0.2129, # cap_d, cap_h, cap_s, cap_T
	0.452,0.554, 0.332,0.092 ), # shank diam, M, T, N

Screw( '1/2',0.5,[13,20,28],0,0.815, #desc, diam, pitch, def, head_d
	0.223,0.336, 0.75, 0.364, # flat_h, pan_h, hex_a, hex_h
	0.7500,0.4379,0.4375,0.2450, # cap_d, cap_h, cap_s, cap_T
	0.515,0.593,0.358,0.098 ), # shank diam, M, T, N
]

imperial_nuts = [ 
#desc,diam,pitch, def_pitch,hex_a,hex_h 
Nut( '#5', 0.1250,[40,44],0,0.25,0.1 ), 
Nut( '#6', 0.1380,[32,40],0,0.312,0.11 ), 
Nut( '#8',0.1640,[32,36],0,0.343,0.125 ), 
Nut( '#10',0.19,[24,32],0,0.375,0.125 ), 
Nut( '#12',0.216,[24,28,32],0,0.435,0.1562 ), 
Nut( '1/4',0.25,[20,28,32],0,0.435,0.2187 ), 
Nut( '5/16',0.3124,[18,24,32],0,0.5,0.2656 ), 
Nut( '3/8',0.375,[16,24,32],0,0.562,0.3281 ), 
Nut( '7/16',0.4375,[14,20,28],0,0.687,0.375 ), 
Nut( '1/2',0.5,[13,20,28],0,0.75,0.4375 ) 
]

metric_screws = [

Screw( 'M3',3,[0.35,0.5],1,6.3, #desc, diam, pitch, def, head_d
	1.7,1.8,5.5,2.4, # flat_h, pan_h, hex_a, hex_h
	5.50,3.00,2.5,1.3, # cap_d, cap_h, cap_s, cap_T
	3.6,3.44,2.50,0.83, am_metric=True ), # shank diam, M, T, N
Screw( 'M4',4,[0.5,0.7],1,9.4, #desc, diam, pitch, def, head_d
	2.7,2.4,7,3.2, # flat_h, pan_h, hex_a, hex_h
	7.00,4.00,3,2, # cap_d, cap_h, cap_s, cap_T
	4.7,4.92,3.00,1.01, am_metric=True ), # shank diam, M, T, N
Screw( 'M5',5,[0.5,0.8],1,10.4, #desc, diam, pitch, def, head_d
	2.7,3,8,4.7, # flat_h, pan_h, hex_a, hex_h
	8.50,5.00,4,2.5, # cap_d, cap_h, cap_s, cap_T
	5.7,5.66,3.74,1.1, am_metric=True ), # shank diam, M, T, N
Screw( 'M6',6,[0.75,1],1,12.6, #desc, diam, pitch, def, head_d
	3.3,3.6,10,5.2, # flat_h, pan_h, hex_a, hex_h
	10.00,6.00,5,3, # cap_d, cap_h, cap_s, cap_T
	6.8,7.3,4.26,1.19, am_metric=True ), # shank diam, M, T, N
Screw( 'M8',8,[0.75,1,1.25],2,17.3, #desc, diam, pitch, def, head_d
	4.6,4.8,13,5.5, # flat_h, pan_h, hex_a, hex_h
	13.00,8.00,6,4, # cap_d, cap_h, cap_s, cap_T
	9.2,9.86,5.81,1.95, am_metric=True ), # shank diam, M, T, N
Screw( 'M10',10,[0.75,1,1.25,1.5],3,20, #desc, diam, pitch, def, head_d
	5,6,17,6.4, # flat_h, pan_h, hex_a, hex_h
	16.00,10.00,8,5, # cap_d, cap_h, cap_s, cap_T
	11.2,11.24,7.15,2.17, am_metric=True ), # shank diam, M, T, N
Screw( 'M12',12,[1,1.25,1.5,1.75],3,22, #desc, diam, pitch, def, head_d
	5.5,8,19,7.5, # flat_h, pan_h, hex_a, hex_h
	18.00,12.00,10,6, # cap_d, cap_h, cap_s, cap_T
	12.2,13.24,8.55,2.50, am_metric=True ), # shank diam, M, T, N
]

metric_nuts = [
#desc,diam,pitch, def_pitch,hex_a,hex_h 
Nut( 'M3',3,[0.35,0.5],1,5.5,2.4,am_metric=True),
Nut( 'M4',4,[0.5,0.7],1,7,3.2,am_metric=True),
Nut( 'M5',5,[0.5,0.8],1,8,4.7,am_metric=True),
Nut( 'M6',6,[0.75,1],1,10,5.2,am_metric=True),
Nut( 'M8',8,[0.75,1,1.25],2,13,7.2,am_metric=True),
Nut( 'M10',10,[0.75,1,1.25,1.5],3,17,7.9,am_metric=True),
Nut( 'M12',12,[1,1.25,1.5,1.75],3,19,9.9,am_metric=True)
]
