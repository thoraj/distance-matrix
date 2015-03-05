# distancematrix
Example showing how to use Google Distance Matrix

Python script showing how to use the Google Distance Matrix API to compute a distance matrix for a set of nodes/coordinates taken from a csv 

##Examples:

**python distance-matrix.py --help**

Will produce:

	usage: distance-matrix.py [-h] [-g | -rptprefixed | -rptcsv]
							  [-prefixstring PREFIX_STRING] -key API_KEY -if
							  INPUT_FILE -of OUTPUT_FILE [-r] [-u] [-v]

	Get distances between nodes using Google Distance Matrix Api

	optional arguments:
	  -h, --help            show this help message and exit
	  -g, --get-distances   use google api to get distances for the nodes in the
							input file
	  -rptprefixed, --dump-report-prefixed-record
							use the results from running the file specified by the
							-if/--input-file argument to create a dump output file
							using a prefixed record format
	  -rptcsv, --dump-report-csv
							use the results from running the file specified by the
							-if/--input-file argument to create a dump output file
							in the csv format
	  -prefixstring PREFIX_STRING, --prefix-string PREFIX_STRING
							string which will be prefixed to records created in
							the "prefixed-record" format
	  -key API_KEY, --api-key API_KEY
							api key to use in requests to the distance matrix api
	  -if INPUT_FILE, --input-file INPUT_FILE
							Path and filename to the input csv file with
							nodes/points
	  -of OUTPUT_FILE, --output-file OUTPUT_FILE
							Path and filename to the output file
	  -r, --resume          Resume the job for the input file
	  -u, --undirected      Consider NodeA -> NodeB to be the same as NodeB ->
							NodeA
	  -v, --verbose         Produce verbose output when running



**python distance-matrix.py -if nodes.txt -of matrix.csv -u -key [API-KEY]**

Will create an (internal pickle) file with the distance matrix

**python distance-matrix.py -if nodes.txt -of matrix.csv -u -key [API-KEY] -rptcsv**

Will use the distance matrix created above and produce an output file in the csv format from the distance matrix created above

**python distance-matrix.py -if nodes.txt -of matrix.csv -u -key [API-KEY] -rptprefixed -prefixstring myprefix**

Will use the distance matrix created above and produce an output file in containing records prefixed with the string 'myprefix'


  
  

