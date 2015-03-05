# coding=utf-8
__author__ = 'thoraj'

import json
import csv
import cPickle as pickle
import httplib
import time
import locale
import sys


def addNodeIdIfMissing(node):
    if not node.has_key('NodeId'):
        node['NodeId'] = mkNodeId(node)
    return node


def readNodesFromFile(fname):

    locale.setlocale(locale.LC_ALL, "nor")

    f = file(fname)
    nodeReader = csv.DictReader(f, delimiter='\t')

    nodes = []
    for node in nodeReader:
        nodes.append(node)

    nodes = [addNodeIdIfMissing(node) for node in nodes]

    # create node id
    return nodes


def getNodeFragment(node):
    nodeFragment = node['Latitude'].strip() + ',' + node['Longitude'].strip()
    return nodeFragment


def buildQueryStringFromNodes(qry_str_base, originNode, targetNodes, api_key):
    qFragment = ''
    for node in targetNodes:
        qFragment += getNodeFragment(node)
        qFragment += '|'

    originNodeFragment = getNodeFragment(originNode)
    result = qry_str_base + '&origins=' + originNodeFragment + '&destinations=' + qFragment[:-1] + '&key=' + api_key
    return result


# Filter the nodes according to the command line arguments
def filter_nodes(cmdargs, distances, origin_node, node_slice):

    # remove nodes already in the result distances
    result_nodes = [node for node in node_slice if not [distance for distance in distances if (distance.OriginNode['NodeId'] == origin_node['NodeId'] and distance.DestinationNode['NodeId'] == node['NodeId'])]]

    # Remove origin -> origin computations
    result_nodes = [node for node in result_nodes if node['NodeId'] != origin_node['NodeId']]

    # Remove 'duplicates' if legs are undirectional (A->B = B->A)
    if result_nodes and cmdargs['undirected']:
        aliases = [distance for distance in distances if distance.DestinationNode['NodeId'] == origin_node['NodeId']]
        if aliases:
            result_nodes = [node for node in result_nodes if not [an for an in aliases if node['NodeId'] == an.OriginNode['NodeId']]]

    return result_nodes


def getDistanceMatrixFromGoogle(cmdargs, nodes, url, qry_str_base, api_key, max_nodes):
    # Break down nodes into something that pleases Google quotas

    # Iterate such that:  each query has < 100 nodes
    # no more than 100 nodes are processed per 10 seconds
    # no more than 2500 nodes are processed per 24 hours

    # TODO: Make this a bit smarter to better utilize the quotas
    
    node_cnt = len(nodes)

    if cmdargs['resume']:
        pickle_filename = cmdargs['input_file'] + '.pickle'
        infile = open(pickle_filename, "r")
        results = pickle.load(infile)
        infile.close()
    else:
        results = []

    for node in nodes:
        print 'processing origin ' + node['NodeId'] + (' -- (%s)' % node['Betegnelse'])
        slice_index = 0
        while 1:

            if slice_index + max_nodes > node_cnt:
                node_slice = nodes[slice_index:]
            else:
                node_slice = nodes[slice_index:slice_index + max_nodes]

            if len(node_slice) > 0:
                filtered_nodes = filter_nodes(cmdargs, results, node, node_slice)
                if len(filtered_nodes) != 0:
                    slice_qry_str = buildQueryStringFromNodes(qry_str_base, node, filtered_nodes, api_key)
                    if cmdargs['verbose']: print '\t' + slice_qry_str
                    sliceDistances = getDistancesFromGoogle(url, slice_qry_str, node, filtered_nodes)
                    results.extend(sliceDistances)
                    for new_node in sliceDistances:
                        print '\t' + str(new_node)
                    time.sleep(10)

                slice_index += max_nodes
            else:
                break

        # dump to a file
        pickle_filename = cmdargs['input_file'] + '.pickle'
        outfile = open(pickle_filename, "w+")
        pickle.dump(results, outfile)
        outfile.close()

    return results


class Distance:
    def __init__(self, origin_node, destination_node, distance_element):

        self.OriginNode = origin_node
        self.DestinationNode = destination_node
        self.DistanceElement = distance_element

        if distance_element['status'] == 'OK':
            self.Duration = distance_element['duration']['value']
            self.Distance = distance_element['distance']['value']
            self.AverageSpeed = self.Distance / (self.Duration * 1.0) if self.Duration else 0.0
        else:
            self.Duration = 999999
            self.Distance = 999999
            self.AverageSpeed = 999999

    def __str__(self):
        result = self.OriginNode['NodeId'] + ' --> ' + \
                 self.DestinationNode['NodeId'] + ' = ' + \
                 str(self.Distance) + ' at ' + str(round(self.AverageSpeed * 3.6, 1)) + 'km/h'

        return result


def do_query(url, qry_str):
    """

    :rtype : json string
    """
    conn = httplib.HTTPSConnection(url)
    conn.request("GET", qry_str)
    response = conn.getresponse()

    if response.status != 200:
        print "request failed:" + url + '/' + qry_str
        return None

    json_text = response.read()
    conn.close()

    return json_text


def getDistancesFromGoogle(url, qry_str, node, node_slice):

    json_text = do_query(url, qry_str)
    if json_text == None:
        # bail
        return None

    json_data = json.loads(json_text)

    if json_data['status'] != 'OK':
        # print something meaningful to the console
        print "Error:" + json_text

        # check if we have a quota overrun
        if json_data['status'] == 'OVER_QUERY_LIMIT':
            # mickey mouse retry strategy: sleep 24 hours and retry
            print "Error: Over quota, sleeping 24hours"
            time.sleep(24 * 60 * 60)
            json_text = do_query(url, qry_str)
            if json_text == None:
                # bail
                return None

            json_data = json.loads(json_text)
            if json_data['status'] != 'OK':
                # print something meaningful to the console
                print "Error - bailing:" + json_text
        else:
            # bail for all other errors
            return None

    # get the destination elements for the single origin node
    distance_elements = json_data['rows'][0]['elements']

    results = []
    destination_index = 0
    for destination in distance_elements:
        results.append(Distance(node, node_slice[destination_index], destination))
        destination_index += 1

    return results


# Create a output entry from canonical distance object
def mkNodeId(node):
    return '%.6f#%.6f' % (float(node['Longitude']), float(node['Latitude']))


def mkDict(entry):
    locale.setlocale(locale.LC_ALL, "nor")
    result = {}
    result['from'] = entry.OriginNode['NodeId']
    result['from text'] = entry.OriginNode['Betegnelse']
    result['to'] = entry.DestinationNode['NodeId']
    result['to text'] = entry.DestinationNode['Betegnelse']
    result['basis'] = time.strftime("%Hh%M", time.gmtime(entry.Duration))
    result['distance'] = entry.Distance
    result['speed'] = locale.format("%.2f", entry.AverageSpeed * 3.6)
    return result

def mk_prefixed_record_line(prefix, entry):
    locale.setlocale(locale.LC_ALL, "eng_can")
    distance = locale.format('%.3f', entry.Distance/1000.0)
    result = [prefix, entry.OriginNode['NodeId'], entry.DestinationNode['NodeId'],'', time.strftime("%Hh%M", time.gmtime(entry.Duration)),'', '', '', distance ]
    return result

# Write distances out to a csv file
def dump_distances_to_csv_file(args, distances=None):
    if distances == None:
        pickle_filename = args['input_file'] + '.pickle'
        import cPickle as pickle

        fin = open(pickle_filename, "r")
        input_distances = pickle.load(fin)
    else:
        input_distances = distances

    print 'Creating csv report for %d node distances -> %s' % (len(input_distances), args['output_file'])

    fout = open(args['output_file'], "w+")

    out_dicts = [mkDict(entry) for entry in input_distances]
    writer = csv.DictWriter(fout, ['from', 'from text', 'to', 'to text', 'basis', 'distance', 'speed'],
                            dialect=DistanceDialect())
    writer.writeheader()
    writer.writerows(out_dicts)
    fout.close()

# Write distances out to a file with prefixed records
def dump_distances_to_prefixed_record_file(args, distances=None):
    if distances == None:
        pickle_filename = args['input_file'] + '.pickle'
        import cPickle as pickle

        fin = open(pickle_filename, "r")
        input_distances = pickle.load(fin)
    else:
        input_distances = distances

    print 'Creating prefixed record report for %d node distances -> %s' % (len(input_distances), args['output_file'])

    fout = open(args['output_file'], "w+")

    out_list = [mk_prefixed_record_line(args['prefix_string'], entry) for entry in input_distances]
    writer = csv.writer(fout, dialect=DistanceDialect());
    writer.writerows(out_list);
    fout.close()

class DistanceDialect(csv.excel):
    lineterminator = '\n'
    delimiter = ';'


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Get distances between nodes using Google Distance Matrix Api')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-g', '--get-distances', help='use google api to get distances for the nodes in the input file',
                       action='store_true', default=True)
    group.add_argument('-rptprefixed', '--dump-report-prefixed-record',
                       help='use the results from running the file specified by the -if/--input-file argument to '
                            'create a dump output file using a prefixed record format', action='store_true')
    group.add_argument('-rptcsv', '--dump-report-csv',
                       help='use the results from running the file specified by the -if/--input-file argument to '
                            'create a dump output file in the csv format', action='store_true')
    parser.add_argument('-prefixstring', '--prefix-string',
                       help='string which will be prefixed to records created in the \"prefixed-record\" format')
    parser.add_argument('-key', '--api-key', help='api key to use in requests to the distance matrix api',
                        required=True)
    parser.add_argument('-if', '--input-file', help='Path and filename to the input csv file with nodes/points',
                        required=True)
    parser.add_argument('-of', '--output-file', help='Path and filename to the output file', required=True)
    parser.add_argument('-r', '--resume', help='Resume the job for the input file', action='store_true')
    parser.add_argument('-u', '--undirected', help='Consider NodeA -> NodeB to be the same as NodeB -> NodeA',
                        action='store_true')
    parser.add_argument('-v', '--verbose', help='Produce verbose output when running', action='store_true')

    cmdargs = vars(parser.parse_args())


    if cmdargs['dump_report_csv'] == True:
        dump_distances_to_csv_file(cmdargs)
        print "Done."
        return 0

    if cmdargs['dump_report_prefixed_record'] == True:
        dump_distances_to_prefixed_record_file(cmdargs)
        print "Done."
        return 0

    if cmdargs['get_distances'] == True:

        url = r'maps.googleapis.com'

        # Todo: build this from command line parameters
        qry_base_str = r'/maps/api/distancematrix/json?avoid=ferries&mode=driving'

        api_quota_max_nodes = 90

        # Get nodes from file
        nodes = readNodesFromFile(cmdargs['input_file'])

        # Use Google Distance Matrix APi to get distances between nodes
        getDistanceMatrixFromGoogle(cmdargs, nodes, url, qry_base_str, cmdargs['api_key'], api_quota_max_nodes)
        print "Done."
        return 0


if __name__ == "__main__":
    sys.exit(main())
