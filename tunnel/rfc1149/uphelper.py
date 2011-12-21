#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import bitarray

class UPHelper():
	""" The Unicode Packet Helper
	
	Twitter supports 140 chars, while a char can be a unicode
	character. For a unicode character there are 2^20 possibilities.
	For the sake of lazyness we put two bytes in each character, using
	only 2^16. The remaining 4 bits can be used for metadata or whatever.
	
	The header in the metadata is as following:
	<fragment bit (1 if packet is a fragment, 0 if last in row)>
	<9 bits length of payload>
	<32 bit random paket id>"""

	@staticmethod
	def intToBits(n, length):
		""" Convert the number n to a bitarray of length. """
		i = 0
		c = 1
		ret = [False] * length
		while i < length:
			ret[length-(i+1)] = (n & c) > 0
			i += 1
			c <<= 1
		return ret
	
	@staticmethod
	def bitsToInt(bits):
		ret = 0
		for i in bits:
			ret = (ret << 1) | (i and 1 or 0)
		return ret
	
	@staticmethod
	def encode(data):
		""" Generate list of packets with a header from data. """
		packetId = random.randint(0, 2**32)
		fragments = []
		while len(data) > 280:
			fragments.append(data[0:280])
			data = data[280:]
		if len(data) > 0:
			fragments.append(data)
		
		# convert to twitter message
		for y in range(len(fragments)):
			fragment = fragments[y]
			lenX = len(fragment)
			# pad packet if it is not long enouth / not aligned
			if len(fragment) < 2*11:
				fragment = fragment + "\x00" * (2*11-len(fragment))
			if len(fragment) % 2 == 1:
				fragment += "\x00"
			
			# write header (bits: 1 fragment, 9 length, 32 id)
			header = bitarray.bitarray(1)
			# write fragment-bit
			header[0] = (y+1 == len(fragments))
			# append packet length
			header.extend(UPHelper.intToBits(lenX, 9))
			# add packet id
			header.extend(UPHelper.intToBits(packetId, 32))
			# padding to complete last 4 bytes
			header.extend([False, False])
			
			i = 0
			h = 0
			ret = ""
			while i+1 < len(fragment):
				val = ord(fragment[i]) << 8 | ord(fragment[i+1])
				if h < 11:
					val |= UPHelper.bitsToInt(header[h*4:(h+1)*4]) << 16
					h += 1
				ret += unichr(val)
				i += 2
			fragments[y] = ret
		return fragments
	
	@staticmethod
	def decode(packet):
		""" Decodes an unicodestring (packet) back to header + data
		
		Returns: tupel(isFragmented, packetLen, packetId, data) """
		if len(packet) < 11:
			raise ValueError("This is not a valid packet, header is too short (should be at least 11, is %d)" % len(packet))
		header = bitarray.bitarray()
		for i in range(11):
			header.extend("{:04b}".format(ord(packet[i]) >> 16))
		isFragmented = header[0]
		
		packetLen = UPHelper.bitsToInt(header[1:9])
		packetId = UPHelper.bitsToInt(header[9:])
		rawData = map(lambda x: ord(x) & 0xFFFF, packet)
		data = []
		for p in rawData:
			data.append(chr(p >> 8))
			data.append(chr(p & 255))
		data = "".join(data)
		
		return (isFragmented, packetLen, packetId, data)

if __name__ == '__main__':
	print UPHelper.encode("foo")
	print UPHelper.decode(UPHelper.encode("foo")[0])
	msg = "".join([chr(i) for i in range(256)])
	msg += "".join([chr(i) for i in range(256)])
	p = UPHelper.encode(msg)
	print repr(msg)
	for x in p:
		print UPHelper.decode(x)

