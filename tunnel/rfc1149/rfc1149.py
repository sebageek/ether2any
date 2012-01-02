#!/usr/bin/python
# -*- coding: utf-8 -*-

import pyudev
import subprocess
import scapy
from scapy.all import IP
import sys
import tempfile
import threading
from zlib import crc32

from conf import Conf

sys.path.append("../../../")

from ether2any import Ether2Any

class UdevReader(threading.Thread):
	def __init__(self, dev):
		threading.Thread.__init__(self)
		self.daemon = True
		self.context = pyudev.Context()

		self.dev = dev

		self.mountpoint = Conf.get("mountpoint")
		self.attrs = Conf.get("udevAttrs")
	
	def isUsableDevice(self, device):
		for k, v in self.attrs.items():
			try:
				if not device[k] == v:
					print device[k]
					return False
			except KeyError:
				return False
		return True

	def readPacket(self):
		print " ** Decoding packet"
		p = subprocess.Popen("find %s -iname '*jpg'  -printf '%%C@ %%p\n'|sort -n|tail -n 1|awk {'print $2'}" % (self.mountpoint,), shell=True, stdout=subprocess.PIPE)
		if p.wait() != 0:
			return False
		imgName = p.stdout.read().strip()
		if imgName == "":
			print " !! Error: No suitable image found"
			return False
		print "	++ Using image %s" % imgName
		print "	++ Attempting convert + tesseract decoding"
		imgFile, txtFile = tempfile.mktemp(suffix=".tif"), tempfile.mktemp()
		p = subprocess.Popen("convert %(input)s -colorspace Gray -white-threshold 45%% %(tmpImg)s ; tesseract %(tmpImg)s %(output)s nobatch tessconf/hex" % {'input': imgName, 'tmpImg': imgFile, 'output': txtFile}, shell=True)
		if p.wait() != 0:
			print "	!! Error executing convert/tesseract command"
			return False
		output = None
		try:
			outFile = open(txtFile + ".txt", "r")
			output = outFile.read()
			outFile.close()
		except IOError:
			print " !! Could not open tesseract output file"
			return False
		output = output.replace("\n", "").replace(" ", "")
		if len(output) % 2 != 0:
			print " !! Output of tesseract is not byte aligned"
			return False
		if len(output) < 10:
			print " !! Output of tesseract is not long enough"
			return False
		
		packet = "".join(map(lambda x: chr(int(output[x:x+2], 16)), xrange(0, len(output[0:-8]), 2)))
		checksum = int(output[-8:], 16)
		calcedChecksum = crc32(packet) & 0xffffffff
		if checksum != calcedChecksum:
			print " !! Checksum failed (was 0x%08x, should be 0x%08x)" % (checksum, calcedChecksum)
			return Falsea
		self.dev.write("\x00\x00\x08\x00" + packet)
		return True
	
	def run(self):
		monitor = pyudev.Monitor.from_netlink(self.context)
		monitor.filter_by(subsystem='block')
		for action, device in monitor:
			if self.isUsableDevice(device):
				self.devname = device['DEVNAME']
				if action == 'add':
					print ["/bin/mount", self.devname, self.mountpoint]
					p = subprocess.Popen(["/bin/mount", self.devname, self.mountpoint])
					ret = p.wait()
					if ret == 0:
						print " ++ Mounted camera/card (%s) at %s" % (self.devname, self.mountpoint)
						if self.readPacket():
							print " >> Successfully read packet"
						else:
							print " !! Error reading packet"
						print " ** Releasing camera/card (%s)..." % (self.devname,)
						subprocess.Popen(["/bin/umount", "-f", self.devname])
						subprocess.Popen("/bin/sync")
						print " ** Unmounted"
					else:
						print " !! Error mounting stick (%s) at %s: Error id %d" % (self.devname, self.mountpoint, ret)
				elif action == 'remove':
					print " -- Camera/card (%s) removed." % self.devname


class RFC1149(Ether2Any):
	
	def __init__(self):
		Ether2Any.__init__(self, tap=False)
		
		network = Conf.get("network", {'mtu': 1500})
		
		self.dev.ifconfig(**network)
		self.dev.up()
		
		self.reader = UdevReader(self.dev)
		self.reader.start()
	
	def toPrinter(self, packet):
		packet = packet.upper()
		print packet
	
	def sendToNet(self, packet):
		print "packet", repr(packet[4:])
		scp = IP(packet[4:])
		checksum = crc32(packet[4:]) & 0xffffffff
		checksumStr = "%08x" % checksum
		hexRepr = " ".join(map(lambda x: "%02x" % ord(x), packet[4:])) + " " + " ".join(map(lambda x: checksumStr[x:x+2], range(0, len(checksumStr), 2)))
		print " ?>", scp.summary(), " -- hex len", len(hexRepr), "checksum 0x%08x" % checksum
		i = ""
		while i.lower() not in ("a", "d"):
			i = raw_input(" ?? (A)ccept/(D)rop? ")
		if i == "a":
			# accept the packet!
			print " >> Moved one packet to printer"
			self.toPrinter(hexRepr)
			self.reader.output(hexRepr.replace(" ", ""))
		else:
			print " -- Dropped"

if __name__ == '__main__':
	rfc1149 = RFC1149()
	rfc1149.run()

