# python fastener generator

Python modules and the shell script in this directory contain code for generating and manipulating fastener STL files. This code was used to generate all the STL files in the "fasteners" repository.

All modules were tried on Linux Fedora and MacOS. They run on a stock python3 install, except the stlpack.py utility, which needs numpy and scipy packages.

The main programs are as follows:

- boltgen.py : generates a single bolt or screw using given units, diameter, length and head.

- nutgen.py : generates a single nut using given units and diameter.

- boltgen_gui.py : a GUI that provides the same functions and options as boltgen.py and nutgen.py.

- batchbolt.py : generates fasteners of all lengths for all pitches for the given dimension. All have the same head.

- batchnut.py : Makes all the predefined nuts for the given unit (mm or in).

- stlpack.py : takes a list of fastener STL files and packs them into a single STL file for printing. The goal is to minimize the move times between fasteners. It also produces a list file with all names of all the files that were combined. Needs numpy and scipy.

Except for stlpack.py, -h or --help will give the help message describing all the parameters.

Shell script gen_head.sh calls batchbolt.py to generate all the fasteners of the same unit, type and head. For example:

gen_head.sh mm bolt hex

generates all the default metric bolts with hex head.

The rest of the .py files describe various modules:

- facets.py : defines facet classes and provides STL file reading and writing.

- constructs.py : low level constructs used in fastener construction.

- parts.py : fastener parts.

- generate.py : generates bolts and screws (generate_bolt) and nuts (generate_nut). Called by all the generation main programs.

- dimensions.py : initializes the arrays of predefined bolts and nuts. This file contains all the default sizes and pitches.

- pack.py : optimization module doing the main work in stlpack.py.
