
# Generates vertices and facets, reads and writes STL files.

# By Nenad Rijavec

# This is free and unencumbered software released into the public domain.

# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.

import math
import struct
import copy
import sys

MIN = 1e-13
vertices = []

# usual 2-norm
def norm2( x, y, z ):
	return( math.sqrt( x**2 + y**2 + z**2 ) )

# angle is stored as [0, 2*PI]. Note that atan, etc. yield [ -PI, PI ].
class Vertex:
	# constructor takes either  z,y,z (default) or r,angle,z if am_cyl
	def __init__(self, a,b,z, am_cyl=False ):
		if not am_cyl :
			self.x = a
			self.y = b
			self.z = z
			self.r = norm2( a, b, 0 ) # r is in XY plane
			self.angle = math.atan2( b, a )
			if self.angle < 0 :
				self.angle += 2 * math.pi
		else :
			self.z = z
			self.r = a
			self.angle = b
			self.x = a * math.cos(b)
			self.y = a * math.sin(b)
		vertices.append(self)
	#cartesian coordinates
	def str(self):
		outstr = \
			str("{:.6f}".format(self.x))+" "+\
			str("{:.6f}".format(self.y))+" "+\
			str("{:.6f}".format(self.z))
		return( outstr )
	def print_xyz(self):
		print(self.str())
	def write_binary(self, file):
		file.write( struct.pack('<f',self.x))
		file.write( struct.pack('<f',self.y))
		file.write( struct.pack('<f',self.z))
	# cylindric coordinates
	def str_cyl(self):
		outstr = \
			str("{:.6f}".format(self.r))+" "+\
			str("{:.6f}".format(self.angle))+" "+\
			str("{:.6f}".format(self.z))
		return( outstr )
	def print_cyl(self):
		print(self.str_cyl())
	def rotate( self, angle ) :
		self.angle += angle
		if self.angle > 2* math.pi :
			self.angle -= 2*math.pi
		elif self.angle < 0 :
			self.angle += 2*math.pi
		self.x = self.r * math.cos(self.angle)
		self.y = self.r * math.sin(self.angle)
	
	# changing cartesian x,y requires updating polar r, angle
	def change_cart( self, x, y ) :
			self.x = x
			self.y = y
			self.r = norm2( a, b, 0 ) # r is in XY plane
			self.angle = math.atan2( b, a )
			if self.angle < 0 :
				self.angle += 2 * math.pi
	
	# changing polar r, angle requires updating cartesian x, y
	def change_cyl( self, r, angle ) :
		self.r = r
		self.angle = angle
		self.x = r * math.cos(angle)
		self.y = r * math.sin(angle)
	
	def deepcopy(self) :
		new = copy.deepcopy(self)
		vertices.append(new)
		return new

class Facet:
	def __init__(self, vt0, vt1, vt2 ):
		self.vt0 = vt0
		self.vt1 = vt1
		self.vt2 = vt2
		# plane vectors
		a = [ vt1.x-vt0.x, vt1.y-vt0.y, vt1.z-vt0.z ]
		b = [ vt2.x-vt0.x, vt2.y-vt0.y, vt2.z-vt0.z ]
		nrm = [ a[1]*b[2]-a[2]*b[1], \
			   a[2]*b[0]-a[0]*b[2], \
			   a[0]*b[1]-a[1]*b[0] ]
		norm = norm2( nrm[0], nrm[1], nrm[2] )
		if norm == 0 :
		#if norm < MIN :
			sys.exit( 'zero norm for facet normal' )
		self.unitnorm = Vertex( nrm[0]/norm, nrm[1]/norm, nrm[2]/norm )
		vertices.remove(self.unitnorm)
	def reverse(self) :
		# reverses the facet so "out" is the other way
		# we reverse the normal and switch the first two vertices
		self.unitnorm.x = -self.unitnorm.x
		self.unitnorm.y = -self.unitnorm.y
		self.unitnorm.z = -self.unitnorm.z
		vv = self.vt0
		self.vt0 = self.vt1
		self.vt1 = vv
	def print_xyz(self):
		print( "  facet normal " + self.unitnorm.str() )
		print( "    outer loop" ) 
		print( "      vertex " + self.vt0.str() )
		print( "      vertex " + self.vt1.str() )
		print( "      vertex " + self.vt2.str() )
		print( "    endloop" ) 
		print( "  endfacet" ) 
	def write_ascii(self, file):
		file.write( "  facet normal " + self.unitnorm.str() + '\n' )
		file.write( "    outer loop\n" ) 
		file.write( "      vertex " + self.vt0.str() + '\n' )
		file.write( "      vertex " + self.vt1.str() + '\n' )
		file.write( "      vertex " + self.vt2.str() + '\n' )
		file.write( "    endloop\n" ) 
		file.write( "  endfacet\n" ) 
	def write_binary(self, file):
		self.unitnorm.write_binary(file)
		self.vt0.write_binary(file)
		self.vt1.write_binary(file)
		self.vt2.write_binary(file)
		file.write( struct.pack('<h',0))

def write_ascii_stl( filename, comment, facets ):
	ff = open( filename, 'w' )
	ff.write( 'solid ' + comment + '\n' )
	for f in facets:
		f.write_ascii( ff )
	ff.write( 'endsolid\n' )
	ff.close()

def write_binary_stl( filename, comment, facets ):
	ff = open( filename, 'wb' )
	ff.write( comment.encode("utf-8"))
	for i in range(len(comment),80 ):
		ff.write( '\0'.encode("utf-8") )
	ff.write( struct.pack('<I',len(facets)))
	for f in facets :
		f.write_binary(ff) 
	ff.close()

def read_vertex_binary( ff ) :
	x = struct.unpack('<f',ff.read(4))[0]
	y = struct.unpack('<f',ff.read(4))[0]
	z = struct.unpack('<f',ff.read(4))[0]
	return Vertex( x, y, z )
	
def read_facet_binary( ff ) :
	norm = read_vertex_binary(ff)
	vt0 = read_vertex_binary(ff)
	vt1 = read_vertex_binary(ff)
	vt2 = read_vertex_binary(ff)
	tmp = ff.read(2)
	return Facet( vt0, vt1, vt2 )

def read_binary_stl( filename ):
	ff = open( filename, 'rb' )
	facets = []
	comment = ''
	buff = ff.read(80)
	n = 79
	while n > 1 and buff[n] == 0 :
		n -=1
	for i in range(0,n+1) :
		comment += chr(buff[i])
	n_facets = struct.unpack('<I',ff.read(4))[0]
	for n in range(0,n_facets) :
		facets.append( read_facet_binary( ff ) )
	ff.close()
	return [comment, facets ]
