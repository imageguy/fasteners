#! /bin/bash

# generate all screws or bolts for given units and head

if [[ $# -ne 3 ]]
then
	echo usage $0 units type head
	exit 1
fi

units=$1
type=$2
head=$3
echo $units $type $head
if [[ $head == "none" ]]
then
	disphead="rod"
else
	disphead=$head
fi

prefix="bld/stl/$units/$type/$disphead/"

if [[ $units == "mm" ]]
then
	sizes="3 4 5 6 8 10 12"
else
	sizes="#5 #6 #8 #10 #12 1/4 5/16 3/8 7/16 1/2"
fi

for sz in `echo $sizes`
do
	if [[ $units == "mm" ]]
	then
		outdir=$prefix'M'$sz'/'
	else
		outdir=$prefix`echo $sz|sed -e "s/\//f/"`'/'
	fi
	echo starting $outdir
	batchbolt.py $units $type $sz $head --prefix=$outdir
done

