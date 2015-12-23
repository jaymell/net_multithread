#!/usr/bin/python

from __future__ import print_function
import os
import threading, Queue
import sys
import netaddr

import socket
import subprocess


# hey there, global!
safePrint = threading.Lock()

"""
def multiWrapper(func, redirect=None, *args):
	print('i was called')
	while not dataQueue.empty():
		item = dataQueue.get()
		if redirect:
			with open(redirect) as stdout:
				func(item, stdout=stdout, verbose=verbose)
		else:
			stdout = sys.stdout
			func(item, stdout=stdout, verbose=verbose)
"""

def pingIps(dataQueue, stdout, verbose=False):
	""" ping IPs function, 
		needs to be extended 
		to work in Windows also """

	while not dataQueue.empty():
		host = dataQueue.get()
		if 'linux' in sys.platform:
			command = ['/bin/ping', '-c', '1', '%s' % host]
			devnull = open(os.devnull, 'w')
		elif 'win' in sys.platform:
			command = ['c:/windows/system32/ping', '-n', '1', '%s' % host]
			devnull = open('nul', 'w')
		else:
			with safePrint:
				print("I don't know your OS -- exiting")
				return
		if verbose:
			with safePrint:
				print('from queue: %s' % host)
		try:
			subprocess.check_call(command, stdout=devnull, stderr=devnull)
			with safePrint:
				print('%s UP' % host, file=stdout)
		except subprocess.CalledProcessError as e:
			with safePrint:
				print('%s DOWN' % host, file=stdout)
		except Exception as e:
			with safePrint:
				print('%s "ERROR: %s"' % (host,e), stdout)

def testOpenPort(dataQueue, stdout, verbose=False):
	""" check if port is reachable """
	
	### assuming tcp for now, need to front-load protocols
	### and command-line arg for udp
	""""
	if protocol == 'tcp':
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	else:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	"""
	while not dataQueue.empty():
		host, port = dataQueue.get()
		try:
			socket.setdefaulttimeout(1)
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((unicode(host), int(port)))
		except (socket.error, socket.timeout):
			with safePrint:
				print('%s %s CLOSED' % (host, port), file=stdout)
		except Exception as e:
			with safePrint:
				print('%s %s "ERROR: %s"' % (host,port,e), file=stdout)
		else:
			with safePrint:
				print('%s %s OPEN' % (host, port), file=stdout)
		finally:
			s.close()

def initialize(func, dataArray, numThreads, verbose=False, stdout=sys.stdout):
	""" expects to be passed a function and an array of 
		data that is loaded into the queue and divied out
		to worker threads
	"""	

	dataQueue = Queue.Queue()
	# populate queue with data:
	[ dataQueue.put(item) for item in dataArray ]

	threads = []
	for i in range(numThreads):
		thread = threading.Thread(target=func, args=(dataQueue, stdout, verbose, ))
		threads.append(thread)
		thread.start()

	for thread in threads: thread.join()

def parseHostList(rawHostList):
	""" clean up host LIST (should be passed as such) 
		that may be IPs, host names, or some combination of both """
	hostList = []
	for item in rawHostList:
        # first, check if it can be turned into netaddr.IPNetwork object:
		try:
			hostList.extend([i for i in netaddr.IPNetwork(item)])
		# presumably, a hostname was passed rather than an IP / IP block:
		except netaddr.core.AddrFormatError:
			print("Error parsing %s: assuming it's a hostname" % item)
			hostList.append(item)
		# unknown exception:
		except Exception as e:
			print('Unknown exception: %s' % e)
	return hostList

def parsePortList(hostList, portList):
	""" take an already parsed list of hosts and create unique
		host-port tuples"""
	hostPortMap = []
	for host in hostList:
		for port in portList:
			# host-port tuple:
			hostPortMap.append((host, port))
	return hostPortMap
		
if __name__ == '__main__':

	import argparse

	NUMTHREADS = 10

	parser = argparse.ArgumentParser(description='Multi-threaded host ping and/or port check')
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
	parser.add_argument("hostList", nargs="+", help="specify IPs, subnet (in cidr), or hostnames")
	parser.add_argument("--ping", action="store_true", help="ping specified hosts ONLY (no port check)")
	parser.add_argument("--ports", nargs="+", help="ports to check: separated by spaces, no quotes")
	parser.add_argument("--threads", type=int, help="number of concurrent threads")
	parser.add_argument("--redirect", help="redirect to file")
	parser.add_argument("--append", action="store_true", help="append to redirect file, not overwrite")
	args = parser.parse_args()
		
	parsedHostList = parseHostList(args.hostList)
	numThreads = args.threads if args.threads else NUMTHREADS
	if args.redirect:
		if args.append: MODE = 'a'
		else: MODE = 'w'	
		stdout = open(args.redirect, MODE)
	else:
		stdout = sys.stdout
	if args.ports:
		hostPortMap = parsePortList(parsedHostList, args.ports)
		initialize(testOpenPort, hostPortMap, numThreads, args.verbose, stdout)
	elif 'ping' in args:
		initialize(pingIps, parsedHostList, numThreads, args.verbose, stdout)
	else:
		print("I can't figure out what you want me to do. Exiting")
		sys.exit(1)	
