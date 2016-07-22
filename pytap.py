from fcntl import ioctl
import subprocess
import os
import struct


class TapDevice:
	""" TUN/TAP device class """
	
	# magic numbers and structlayout
	TUNSETIFF = 0x400454ca
	IFF_TUN   = 0x0001
	IFF_TAP   = 0x0002
	DEVPATH   = "/dev/net/tun"
	_ifreq = "16sh"

	def __init__(self, name='', tap=True, conf=None, stripHeader=True):
		""" Constructor for the device.
		
		name - the device name, use a %d for a generated device numer
		tap  - if this device should be a tap device
		conf - conf to pass to the ifconfig function of this class
		       (if None ifconfig() won't be called)
		stripHeader - strips the first 4 bytes, they don't belong to
		              the actual network traffic ("\x00\x00\x08\x00")
		"""
		self._mode = (tap and self.IFF_TAP) or self.IFF_TUN
		self._fd = None
		self._nametpl = name
		self._tap = tap
		self._mac = None
		self._mtu = 1500
		self.conf = conf
		self._stripHeader = stripHeader
		
		if name == '':
			self._nametpl = (tap and "tap%d") or "tun%d"
		
		self._createDev()
		if self.conf:
			self.ifconfig(**conf)
	
	def _createDev(self):
		if self._fd:
			self.close()
		
		self._fd = os.open(self.DEVPATH, os.O_RDWR)
		ifreq = struct.pack(self._ifreq, self._nametpl, self._mode)
		ret = ioctl(self._fd, self.TUNSETIFF, ifreq)
		# retmode should be the same as self._mode
		(retname, retmode) = struct.unpack(self._ifreq, ret)
		self._name = retname.strip("\x00")
	
	def _ifconfig(self, params):
		args = ["/sbin/ifconfig"] + params
		ret = subprocess.Popen(args).wait()
		if ret != 0:
			raise PyTapException("Command '%s' did not return 0" % (" ".join(args),))
	
	def ifconfig(self, **kwargs):
		""" Calls ifconfig for the device.
		All arguments will be passed to ifconfig. Use 'address' for the device address.
		E.g. device.ifconfig(address="12.34.56.78", mtu=1500)
		"""
		args = [self._name]
		if kwargs.has_key("address"):
			args.append(kwargs["address"])
			del(kwargs["address"])
		args = reduce(lambda l, key: l+[key, str(kwargs[key])],
							             kwargs, args)
		self._ifconfig(args)
	
	def getMac(self):
		""" Get the device mac """
		# this "could" be buffered, but we never know who when changed the mac
		# ==> we re-get the mac on every request
		proc = subprocess.Popen("LC_ALL=C /sbin/ifconfig %s|head -n 1|egrep -o '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'" % self.getName(), shell=True, stdout=subprocess.PIPE)
		mac = proc.stdout.read().strip()
		return mac
	
	def up(self):
		""" Bring the device up """
		self._ifconfig([self._name, "up"])
	
	def down(self):
		""" Bring the device down """
		self._ifconfig([self._name, "down"])
	
	def getFD(self):
		""" Get the device file descriptor (e.g. to use in select()) """
		return self._fd
	
	def getName(self):
		""" Get the (real) name of the device """
		return self._name
	
	def read(self):
		""" Read a packet from the device """
		readSize = self._mtu
		if self._tap:
			# don't forget the ethernet frame (not included in MTU)
			readSize += 18
		data = os.read(self._fd, self._mtu)
		if self._stripHeader:
			data = data[4:]
		return data
	
	def write(self, data):
		""" Write a packet to the device """
		if self._stripHeader:
			data= "\x00\x00\x08\x00" + data
		os.write(self._fd, data)
	
	def close(self):
		""" Close the device """
		os.close(self._fd)
		self._fd = self._name = None

class PyTapException(Exception):
	pass

