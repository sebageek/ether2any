# -*- coding: utf-8 -*-
import commands
import select
import pytap
import logging
from pytap import TapDevice

class Ether2Any:
	""" Baseclass for writing arbitrary Ethernet/IP Tunnels using TUN/TAP device.
	
	This class handles a TUN/TAP devices and runs a select loop for it and,
	if given, a set of sockets. To use this class at least sendToNet() has
	to be implemented by a subclass. """
	def __init__(self, tap=True, readSockets=[]):
		""" Constructor for Ether2Any.

		isTap defines if the managed device should be a tap (ethernet tunnel)
		or a tun (IP tunnel). """
		self.readSockets = readSockets
		# create device
		self.dev = TapDevice(tap=tap)
		
		self.timeout = None
	
	def setupLogging(self, name):
		l = logging.getLogger(name)
		fmt = logging.Formatter("%(asctime)s - [%(levelname)s] (%(name)s) - %(message)s")
		ch = logging.StreamHandler()
		ch.setFormatter(fmt)
		l.addHandler(ch)
		
		return l
	
	def addSocket(self, sock):
		""" Add socket to readSockets set. """
		self.readSockets.append(sock)
	
	def delSocket(self, socket):
		""" Remove socket from readSockets set. """
		try:
			self.readSockets.remove(socket)
		except ValueError:
			pass

	# outgoing data
	def sendToNet(self, packet):
		""" This function has to be implemented to handle outgoing
		data (read from the TUN/TAP device) """
		raise NotImplementedError("You need to overload sendToNet()")
	
	# incoming data
	def sendToDev(self, sock):
		""" This function has to be implemented to handle incoming
		data which is read from the extra sockets (self.readSockets).
		It will not be called when no extra readSockets are specified. """
		raise NotImplementedError("You need to overload sendToDev()")
	
	def setTimeout(self, t):
		""" Set select timeout. """
		self.timeout = t
	
	def callAfterSelect(self):
		""" Will be called as last operation of the mainloop when
		handling of the select result / the select timeout is hit.
		"""
		pass
	
	def run(self):
		""" Run main select-loop. """
		try:
			while True:
				sockets = [self.dev.getFD()] + self.readSockets
				(readFDs, _, _) = select.select(sockets, [], [], self.timeout)
				for readFD in readFDs:
					if readFD == self.dev.getFD():
						self.sendToNet(self.dev.read())
					elif readFD in self.readSockets:
						self.sendToDev(readFD)
				self.callAfterSelect()
		except KeyboardInterrupt:
			self.quit()
		self.dev.close()
	
	def quit(self):
		""" Will be called after the run-select() and its processing is done. """
		pass

