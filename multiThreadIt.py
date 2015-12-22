#!/usr/bin/python

import os
import threading, Queue
import sys
import netaddr

import socket
import subprocess

def pingIps(host, verbose=False):
	""" ping IPs function, 
		needs to be extended 
		to work in Windows also """

	command = ['/bin/ping', '-c', '1', '%s' % host]
	devnull = open(os.devnull, 'w')
	if verbose:
		with safeprint:
			print('from queue: %s' % host)
	try:
		subprocess.check_call(command, stdout=devnull, stderr=devnull)
		return 'In use: %s' % host
	except subprocess.CalledProcessError as e:
		return 'Unreachable: %s' % host
	except Exception as e:
		return 'Unknown error: %s: %s' % (host,e)

def testOpenPort(host, ports, protocol='tcp', verbose=False):
	""" expects to be a host and list of ports -- 
		check if port is reachable """
	protocol = protocol.lower()
	if protocol == 'tcp':
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	else:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect((host, port))
	except socket.error:
		return 'Unreachable: %s' % host
	except Exception as e:
		return 'Unknown error: %s: %s' % (host,e)
	
def initialize(func, dataArray, numThreads=10, *args, **kwargs):
	""" expects to be passed a function and an array of 
		data that is loaded into the queue and divied out
		to worker threads
	"""	

	# populate queue with data:
	dataQueue = Queue.Queue()
	[ dataQueue.put(item) for item in dataArray ]

	threads = []
	safeprint = threading.Lock()

	while not dataQueue.empty():
		item = dataQueue.get()
		result = func(item)
		with safeprint:
			print(result)

	for i in range(numThreads):
		thread = threading.Thread(target=func, args=(item, *args, **kwargs))
		threads.append(thread)
		# thread.daemon = True
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
	parser = argparse.ArgumentParser(description='Multi-threaded host ping and/or port check')
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
	parser.add_argument("hostList", nargs="+", help="specify IPs, subnet (in cidr), or hostnames")
	parser.add_argument("--ping", action="store_true", help="ping specified hosts ONLY (no port check)")
	parser.add_argument("--ports", nargs="+", help="ports to check: separated by spaces, no quotes")
	args = parser.parse_args()
		
	parsedHostList = parseHostList(args.hostList)
	if args.ports:
		initialize(testOpenPort, parsedHostList, args.ports, args.verbose)
	elif 'ping' in args:
		initialize(pingIps, parsedHostList, args.verbose)
	else:
		print("I can't figure out what you want me to do. Exiting")
		sys.exit(1)	
