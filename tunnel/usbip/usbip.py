#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Sebastian Lohff <seba@seba-geek.de>
# Licensed under GPL v3 or later

import logging
import os
import pyudev
import Queue
import subprocess
import sys
import threading
import time

sys.path.append("../../../")
from conf import Conf
from ether2any import Ether2Any

class USBWriter(threading.Thread):
	def __init__(self, dev, networkQueue, writeLock):
		threading.Thread.__init__(self)
		self.daemon = True
		self.quit = False
		self.packetCounter = 0
		
		self.dev = dev
		self.writeLock = writeLock
		self.networkQueue = networkQueue
		
		self.mountpoint = Conf.get("mountpoint")
		self.usbNetworkDir = Conf.get("usbNetworkDir")
		self.networkFilePrefix = Conf.get("networkFilePrefix")
		
		self.writePath = self.mountpoint + "/" + self.usbNetworkDir + "/"
	
	def getPacketCounter(self):
		return self.packetCounter
	
	def resetPacketCounter(self):
		self.packetCounter = 0
	
	def run(self):
		while not self.quit:
			packet = self.networkQueue.get()
			self.writeLock.acquire()
			f = open(self.writePath + self.networkFilePrefix + "%09d" % self.packetCounter, "w")
			f.write(packet)
			f.close()
			self.packetCounter += 1
			self.writeLock.release()

class UdevHandler(threading.Thread):
	def __init__(self, dev, usbwriter, writeLock):
		threading.Thread.__init__(self)
		self.daemon = True
		self.quit = False
		self.packetCounter = 0
		
		self.dev = dev
		self.usbwriter = usbwriter
		self.writeLock = writeLock
		self.context = pyudev.Context()
		
		self.mountpoint = Conf.get("mountpoint")
		self.usbNetworkDir = Conf.get("usbNetworkDir")
		self.networkFilePrefix = Conf.get("networkFilePrefix")
		self.sync = Conf.get("sync")
		
		self.writePath = self.mountpoint + "/" + self.usbNetworkDir + "/"
		self.attrs = Conf.get("udevAttrs")
		self.devname = None
	
	def isUsableDevice(self, device):
	    for k, v in self.attrs.items():
	        try:
	            if not device[k] == v:
	                return False
	        except KeyError:
	            return False
	    return True
	
	def readAndSweep(self):
		counter = 0
		try:
			for n in os.listdir(self.writePath):
				if n == "." or n == "..":
					continue
				f = open(self.writePath + n, "r")
				packet = f.read()
				f.close()
				os.unlink(self.writePath + n)
				self.dev.write(packet)
				counter += 1
		except OSError, o:
			print " !! Error reading from directory:", o
		
		print " >> Read %d packet(s)" % counter
	
	def run(self):
		monitor = pyudev.Monitor.from_netlink(self.context)
		monitor.filter_by(subsystem='block')
		for action, device in monitor:
			if self.isUsableDevice(device):
				self.devname = device['DEVNAME']
				if action == 'add':
					p = subprocess.Popen(["/bin/mount", self.devname, self.mountpoint])
					ret = p.wait()
					if ret == 0:
						print " ++ Mounted stick (%s) at %s" % (self.devname, self.mountpoint)
						if not os.path.exists(self.writePath):
							os.mkdir(self.writePath)
						self.readAndSweep()
						self.writeLock.release()
						raw_input(" ** Press any key to release usbstick...")
						print " >> %d packet(s) written" % (self.usbwriter.getPacketCounter(),)
						self.usbwriter.resetPacketCounter()
						print " ** Releasing stick..."
						self.writeLock.acquire()
						subprocess.Popen(["/bin/umount", "-f", self.devname])
						if self.sync:
							print " ** Syncing..."
							subprocess.Popen("/bin/sync")
						print " ** Unmounted"
					else:
						print " !! Error mounting stick (%s) at %s: Error id %d" % (self.devname, self.mountpoint, ret)
				elif action == 'remove':
					print " -- Stick (%s) removed." % self.devname


class USBIP(Ether2Any):
	def __init__(self):
		Ether2Any.__init__(self, tap=False)
		
		network = Conf.get("network", {'mtu': 1400})
		self.dev.ifconfig(**network)
		self.dev.up()
		
		self.networkQueue = Queue.Queue()
		self.writeLock = threading.Lock()
		self.writeLock.acquire()
		
		self.usb = USBWriter(self.dev, self.networkQueue, self.writeLock)
		self.usb.start()
		
		self.udev = UdevHandler(self.dev, self.usb, self.writeLock)
		self.udev.start()
		
	
	def sendToNet(self, packet):
		self.networkQueue.put(packet)

if __name__ == '__main__':
	usbip = USBIP()
	print "Starting ip over USB-Stick service..."
	usbip.run()

