#! /usr/bin/env python
# -*- coding:utf-8 -*-
#
# simple shell interface for OGC API 
#
# 2017-01-22 created by S.Miyamoto@SPP
#
#
import argparse
from ogcsosapi import SOSAPI
from datetime import datetime, timedelta

# to prevent ArgumentParser to exit after printing help.
class AP(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        raise argparse.ArgumentError(None, '')


def parse_args():
    parser = argparse.ArgumentParser(description='Simple Shell Interface for OGC SOS API')
    parser.add_argument("--token", required=True, help="your Token to use SOS API")
    parser.add_argument("--endpoint", help="endpoint of SOS Server",
                        default='https://cs.listenfield.com/OGCAPIV2.jsp')
    #parser.add_argument("--remainfile", action="store_true", help="password for ftp server")
    args = parser.parse_args()
    return args

def print_help():
    print '''
    nodes                          : list all sensor nodes served by the server
    sensors [node]                 : list all sensors in the node
    measures -n [node] [sensors..] : get measurements of sensors of a node
    server                         : show server info
    provider                       : show provider info
    help                           : print this help
'''

def list_nodes(args, sosapi):
    parser = AP(prog='nodes')
    parser.add_argument('-l', action='store_true')
    try:
        opts = parser.parse_args(args)
    except:
        return 
    for i, node in enumerate(sosapi.observations):
        if opts.l:
            print '%2d: %s : %s' % (i+1, node.name, node.description)
        else:
            print '%2d: %s' % (i+1, node.name)

def show_server(sosapi):
    print '%s: ' % (sosapi.server.name)
    print ' service type   : %s' % (sosapi.server.service_type)
    print ' service version: %s' % (sosapi.server.service_version)
    print ' service fees   : %s' % (sosapi.server.fees)

def show_provider(sosapi):
    print '%s: ' % (sosapi.provider.name)
    print ' administrator  : %s' % (sosapi.provider.indiviual_name)
    print ' address:'
    print '    %s' % (sosapi.provider.point)
    print '    %s, %s, %s' % (sosapi.provider.city, sosapi.provider.pref, sosapi.provider.country)

def get_node_from_name_or_number(ind, nodes):
    the_node = None
    if ind.isdigit():
        # node number
        try:
            the_node = nodes[int(ind)-1]
        except IndexError:
            pass
    else:
        for node in nodes:
            if node.name == ind:
                the_node = node
                break
    return the_node

def get_prop_from_name_or_number(ind, node):
    the_prop = None
    if ind.isdigit():
        # sensor number
        try:
            the_prop = node.properties[int(ind)-1]
        except IndexError:
            pass
    else:
        for prop in node.properties:
            if prop == ind:
                the_prop = prop
                break
    return the_prop

def list_sensors(args, sosapi):
    parser = AP(prog='sensors')
    parser.add_argument('sensor', help='number or name of sensor')
    try:
        opts = parser.parse_args(args)
    except:
        return
    
    the_node = get_node_from_name_or_number(opts.sensor, sosapi.observations)
    if the_node:
        for i, prop in enumerate(the_node.properties):
            print '%2d: %s' % (i+1, prop)
    else:
        print 'No node was found !!'

def parse_cmd_datetime(dtstr):
    tries = [
        ('%Y%m%d%H%M%S', False),
        ('%Y%m%d%H%M', False),
        ('%Y-%m-%dT%H:%M:%S', False),
        ('%Y-%m-%dT%H:%M', False),
        ('%Y-%m-%d', False),
        ('%H:%M:%S', True),
        ('%H:%M', True),
        ('%H%M', True),
    ]

    for t in tries:
        try:
            dt = datetime.strptime(dtstr, t[0])
            if t[1]:
                # need to set date
                now = datetime.now()
                return dt.replace(year=now.year, month=now.month, day=now.day)
        except ValueError:
            pass

    raise ValueError

def get_measurements(args, sosapi):
    parser = AP(prog='measurements')
    parser.add_argument('-s', help='start datetime')
    parser.add_argument('-e', help='end datetime')
    parser.add_argument('-n', help='node name or number', required=True)
    #parser.add_argument('--header', action='store_true', help='with header')
    parser.add_argument('sensors', nargs='+', help='sensors to get')
    try:
        opts = parser.parse_args(args)
    except:
        return

    try:
        if opts.s:
            s_dt = parse_cmd_datetime(opts.s)
            if opts.e:
                e_dt = parse_cmd_datetime(opts.e)
            else:
                e_dt = datetime.now()
            if s_dt >= e_dt:
                print 'start datetime must be less than end datetime !'
                return
    except ValueError:
        print 'invalid datetime is specified. Please use format, 2016-10-26T00:00:00'
        return

    the_node = get_node_from_name_or_number(opts.n, sosapi.observations)
    if not the_node:
        print 'No node was found !!'
        return

    if not opts.s:
        e_dt = datetime.now()
        s_dt = e_dt - timedelta(seconds=10*60)

    properties = []
    for sensor in opts.sensors:
        prop = get_prop_from_name_or_number(sensor, the_node)
        if not prop:
            'No sensor was found in %s !!' % (the_node.name)
            return
        properties.append(prop)

    measurements = sosapi.get_observation(the_node, properties, [s_dt, e_dt])

    print 'time,%s' % (','.join(properties))
    for dt, measure in sorted(measurements.items()):
        line = []
        line.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
        for prop in properties:
            if prop in measure:
                line.append(str(measure[prop]['value']))
            else:
                line.append('')
        print ','.join(line)

def exec_command(cmd, sosapi):
    if len(cmd) == 0:
        return True

    args = cmd.split()
    if args[0] == 'h' or args[0] == 'help':
        print_help()
    elif args[0] == 'q' or args[0] == 'quit' or args[0] == 'exit':
        return False
    elif args[0] == 'server':
        show_server(sosapi)
    elif args[0] == 'provider':
        show_provider(sosapi)
    elif args[0] == 'nodes':
        list_nodes(args[1:], sosapi)
    elif args[0] == 'sensors':
        list_sensors(args[1:], sosapi)
    elif args[0] == 'measurements' or args[0] == 'measures':
        get_measurements(args[1:], sosapi)
    else:
        print_help()
        
    return True

def main():
    print 'Simple Shell Interface for OGC SOS API by Satoru MIYAMOTO\n'
    
    opts = parse_args()
    sosapi = SOSAPI(opts.endpoint, opts.token)
    sosapi.update_observation_capabilities()

    print 'Welcome to %s by %s !' % (sosapi.server.name, sosapi.provider.name)

    while True:
        cmd = raw_input('\n\033[1;32mSOS: \033[1;m')
        if not exec_command(cmd, sosapi):
            break

if __name__ == '__main__':
    main()
