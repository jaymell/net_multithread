#!/usr/bin/python

import os
import threading, Queue
import sys
import netaddr

import socket
import subprocess

safePrint = threading.Lock()

def pingIps(dataQueue, verbose=False):
	""" ping IPs function, 
		needs to be extended 
		to work in Windows also """
	while not dataQueue.empty():
		host = dataQueue.get()
		command = ['/bin/ping', '-c', '1', '%s' % host]
		devnull = open(os.devnull, 'w')
		if verbose:
			with safePrint:
				print('from queue: %s' % host)
		try:
			subprocess.check_call(command, stdout=devnull, stderr=devnull)
			with safePrint:
				print('In use: %s' % host)
		except subprocess.CalledProcessError as e:
			with safePrint:
				print('Unreachable: %s' % host)
		except Exception as e:
			with safePrint:
				print('Unknown error: %s: %s' % (host,e))

def testOpenPort(dataQueue, verbose=False):
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
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((unicode(host), int(port)))
		except socket.error:
			with safePrint:
				print('Unreachable: %s port %s' % (host, port))
		except Exception as e:
			with safePrint:
				print('Unknown error: %s port %s: %s' % (host,port,e))
		else:
			with safePrint:
				print('Open: %s port %s' % (host, port))
	
def initialize(func, dataArray, numThreads, verbose=False):
	""" expects to be passed a function and an array of 
		data that is loaded into the queue and divied out
		to worker threads
	"""	

	# populate queue with data:
	dataQueue = Queue.Queue()
	[ dataQueue.put(item) for item in dataArray ]

	threads = []
	for i in range(numThreads):
		thread = threading.Thread(target=func, args=(dataQueue, verbose))
		threads.append(thread)
		thread.start()

	for thread in threads: thread.join()

def parseHostList(rawHostList):
	""" clean up host list that may be IPs, host names,
	or some combination of both """
	hostList = []
	for item in rawHostList:
        # first, check if it can be turned into netaddr.IPNetwork object:
		try:
			hostList.extend([i for i in netaddr.IPNetwork(item)])
		# presumably, a hostname was passed rather than an IP / IP block:
		except netaddr.core.AddrFormatError:
			hostList.append(item)
		# unknown exception:
		except Exception as e:
			print('Unknown exception: %s' % e)
	return hostList

if __name__ == '__main__':

	import argparse

	NUMTHREADS = 10

	parser = argparse.ArgumentParser(description='Multi-threaded host ping and/or port check')
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
	parser.add_argument("hostList", nargs="+", help="specify IPs, subnet (in cidr), or hostnames")
	parser.add_argument("--ping", action="store_true", help="ping specified hosts ONLY (no port check)")
	parser.add_argument("--ports", nargs="+", help="ports to check: separated by spaces, no quotes")
	parser.add_argument("--threads", type=int, help="number of concurrent threads")
	args = parser.parse_args()
		
	parsedHostList = parseHostList(args.hostList)
	numThreads = args.threads if args.threads else NUMTHREADS
	if args.ports:
		hostPortMap = []
		for host in parsedHostList:
			for port in args.ports:
				# host-port tuple:
				hostPortMap.append((host, port))
		initialize(testOpenPort, hostPortMap, numThreads, args.verbose)
	elif 'ping' in args:
		initialize(pingIps, parsedHostList, numThreads, args.verbose)
	else:
		print("I can't figure out what you want me to do. Exiting")
		sys.exit(1)	
