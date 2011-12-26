#!/usr/bin/python
# -*- coding: utf-8 -*-

import bitarray
import random
import re
import urllib
from HTMLParser import HTMLParser

class PHelper():
	""" Packaging Helper baseclass """
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
	def toBin(val, leading):
		""" Binary formatter for python versions without str.format() """
		x = bin(val).replace("0b", "")
		return "0" * (leading-len(x)) + x
	
	@staticmethod
	def encode(data):
		""" Encode data, return list of messages (max. 140 chars long) """
		raise NotImplementedError("You need to implement this method when subclassing.")
	
	@staticmethod
	def decode(packet):
		""" Decode packet, return tuple(isFragmented boolean), packetLength int, packetId int, data (byte)string) """
		raise NotImplementedError("You need to implement this method when subclassing.")
	

class UPHelper(PHelper):
	""" The Unicode Packaging Helper
	
	Twitter supports 140 chars, while a char can be a unicode
	character. For a unicode character there are 2^20 possibilities.
	For the sake of lazyness we put two bytes in each character, using
	only 2^16. The remaining 4 bits can be used for metadata or whatever.
	
	The header in the metadata is as following:
	<fragment bit (1 if packet is a fragment, 0 if last in row)>
	<9 bits length of payload>
	<32 bit random paket id greater than 0>"""


	@staticmethod
	def encode(data):
		""" Generate list of packets with a header from data. """
		packetId = random.randint(1, 2**32)
		fragments = []
		while len(data) >= 280:
			newData = data[0:280]
			if newData[-1] == '\x00' and newData[-2] == '\x00' and len(newData) == 280:
				fragments.append(data[0:278])
				data = data[278:]
			else:
				fragments.append(newData)
				data = data[280:]
		if len(data) > 0:
			fragments.append(data)
		
		# convert to twitter message
		for y in range(len(fragments)):
			fragment = fragments[y]
			lenX = len(fragment)
			# pad packet if it is not long enouth / not aligned
			if len(fragment) < 2*11:
				fragment = fragment + "-" * (2*11-len(fragment))
			if len(fragment) % 2 == 1:
				fragment += "-"
			
			# write header (bits: 1 fragment, 9 length, 32 id)
			header = bitarray.bitarray(1)
			# write fragment-bit
			header[0] = not (y+1 == len(fragments))
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
				# hack for (0x2026, 0x202f)
				if val > 0x2026 and val < 0x202f:
					val = val | (1<<16)
				ret += unichr(val)
				i += 2

			# if the last characters are multiple \x00-bytes, twitter eats them!
			# we already took care so there is space at the end for an extra dot
			if ret[-1] == '\x00':
				ret = ret + "."
			fragments[y] = ret
		return fragments
	
	@staticmethod
	def reassembleBrokenChars(packet):
		""" Reassemble broken characters back to unicode.
		
		Twitter breaks some characters (currently known range is 0xd800 - 0xdfff)
		into r"\XXX\XXX\XXX", X being octal numbers. These are actually strings,
		so one unicodechar from the range gets broken up to 12 chars.
		
		Note that through this packets containing the following byte sequence will
		get mangled:
		00 5c 00 XX 00 XX 00 XX 00 5c 00 XX 00 XX 00 XX 00 5c 00 XX 00 XX 00 XX
		while XX is a number from ord('0') to ord('9')
		
		Also _some_ of these are again converted into other chars.
		\ud800\udc00 gets converted to \U00010000, so we need to guess-convert
		these back. """
		origPacket = packet
		brokenChars = re.findall(r"(\\([0-9]{3})\\([0-9]{3})\\([0-9]{3}))", packet)
		for broken in brokenChars:
			#print "broken", broken, repr("".join(map(lambda x: chr(int(x, 8)), broken[1:])))
			newChar = "".join(map(lambda x: chr(int(x, 8)), broken[1:])).decode("utf-8")
			packet = packet.replace(broken[0], newChar)

		# this is guesswork-derivation, its derived from these lines
		# they represent our input and twitters output
		# guesswork++: for the header, this is plausible, afterwards not.
		# u"\ud900\udc00 \uda00\udcFF \udb00\uddFF"
		# u'\U00050000 \U000900ff \U000d01ff"
		# u"\ud800\udc00 \ud800\udcFF \ud800\uddFF \ud800\ude00 \ud800\udeff \ud800\udf00 \ud800\udfff"
		# u'\U00010000 \U000100ff \U000101ff \U00010200 \U000102ff \U00010300 \U000103ff'
		# u"\ud800\udc00 \ud801\udc00 \ud802\udc00 \ud803\udc00 \ud804\udc00 \ud805\udc00\ud806\udc00 \ud807\udc00 \ud808\udc00 \ud809\udc00 \ud80a\udc00 \ud80b\udc00 \ud80c\udc00 \ud80d\udc00 \ud80e\udc00 \ud80f\udc00 \ud810\udc00 \ud811\udc00 \ud812\udc00 \ud813\udc00"
		# u'\U00010000 \U00010400 \U00010800 \U00010c00 \U00011000 \U00011400\U00011800 \U00011c00 \U00012000 \U00012400 \U00012800 \U00012c00 \U00013000 \U00013400 \U00013800 \U00013c00 \U00014000 \U00014400 \U00014800 \U00014c00'


		for c in origPacket[11:]:
			o = ord(c)
			# (0x2027, 0x202f) are not displayed properly
			if o > 0x12027 and o < 0x1202f:
				packet.replace(c, unichr(o & (0xFFFF)))
			elif o > 65535:
				# -.-
				a = unichr(0xd800 + ((o >> 10) - 64))
				b = unichr(0xdc00 + (o & 1023))
				packet = packet.replace(c, a+b)
		return packet
	
	@staticmethod
	def decode(packet):
		""" Decodes an unicodestring (packet) back to header + data
		
		Returns: tupel(isFragmented, packetLen, packetId, data) """
		
		packet = UPHelper.reassembleBrokenChars(packet)
		
		if len(packet) < 11:
			raise ValueError("This is not a valid packet, header is too short (should be at least 11, is %d)" % len(packet))
		header = bitarray.bitarray()
		for i in range(11):
			# format with binary is not understood by older python versions
			#header.extend("{:04b}".format(ord(packet[i]) >> 16))
			header.extend(UPHelper.toBin((ord(packet[i]) >> 16), 4))
		isFragmented = header[0]
		
		packetLen = UPHelper.bitsToInt(header[1:10])
		packetId = UPHelper.bitsToInt(header[10:])
		if packetId == 0:
			raise ValueError("Packet id cannot be 0")

		rawData = map(lambda x: ord(x) & 0xFFFF, packet)
		data = []
		for p in rawData:
			data.append(chr((p >> 8) & 255))
			data.append(chr(p & 255))
		data = "".join(data[:packetLen])
		return (isFragmented, packetLen, packetId, data)

class DPHelper(PHelper):
	""" The Dump Packaging Helper
	
	As twitters unicodehandling is quiet random, this is an
	attempt to a more reliable en-/decoding. It uses
	the first char for an unicode header, the remaining 138
	chars are used for the networkpacket in plain.
	
	Header: 
	<1 bit, True if fragment>
	<8 bit, lenght of packet>
	<11 bit, packet id [1, 2047]>
	"""
	
	@staticmethod
	def textEncode(t):
		return t.replace("&",  "&amp;") \
				.replace("\n", "&#10;") \
				.replace("\r", "&#13;")

	@staticmethod
	def textDecode(t):
		return t.replace("&lt;",  "<")   \
				.replace("&gt;",  ">")   \
				.replace("&#10;",  "\n") \
				.replace("&#13;",  "\r") \
				.replace("&amp;", "&")
	
	@staticmethod
	def encode(data):
		# twitter encodes <>'s ==> we need to encode & to distinguish between &lt; and an encoded etc.
		data = DPHelper.textEncode(data)
		packetId = random.randint(1, 2**11)
		fragments = []
		while len(data) >= 139:
			newData = data[0:139]
			if newData[-1] == '\x00' and newData[-2] == '\x00' and len(newData) == 139:
				fragments.append(data[0:138])
				data = data[138:]
			else:
				fragments.append(newData)
				data = data[139:]
		if len(data) > 0:
			fragments.append(data)
		
		# convert to twitter message
		for y in range(len(fragments)):
			fragment = fragments[y]
			lenX = len(fragment)
			
			# write header (bits: 1 fragment, 8 length, 11 id)
			header = bitarray.bitarray(1)
			# write fragment-bit
			header[0] = not (y+1 == len(fragments))
			# append packet length
			header.extend(DPHelper.intToBits(lenX, 8))
			# add packet id
			header.extend(DPHelper.intToBits(packetId, 11))
			ret = unichr(DPHelper.bitsToInt(header)) + "".join([unichr(ord(i)) for i in fragment])

			# if the last characters are multiple \x00-bytes, twitter eats them!
			# we already took care so there is space at the end for an extra dot
			if ret[-1] == '\x00' and ret[-2] == '\x00':
				ret = ret + "."
			fragments[y] = ret
		return fragments
	
	@staticmethod
	def decode(packet):
		""" Decodes an unicodestring (packet) back to header + data
		
		Returns: tupel(isFragmented, packetLen, packetId, data) """
		
		# twitter urlencodes < and > to &lt; and &gl;
		# this will of course break packets containing an actual &lt; or &gt;
		packet = DPHelper.textDecode(packet)
		#packet = packet.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
		
		if len(packet) < 2:
			raise ValueError("This is not a valid packet, header is too short (should be at least 11, is %d)" % len(packet))
		header = bitarray.bitarray(DPHelper.toBin(ord(packet[0]), 20))
		isFragmented = header[0]
		
		packetLen = DPHelper.bitsToInt(header[1:9])
		packetId = DPHelper.bitsToInt(header[9:])
		if packetId == 0:
			raise ValueError("Packet id cannot be 0")
		
		data = "".join(map(lambda x: chr(ord(x)), packet[1:packetLen+1]))
		return (isFragmented, packetLen, packetId, data)

if __name__ == '__main__':
	msg = '\x00\x00\x08\x00E\x00\x00T\x00\x00@\x00@\x01\x12\x81\n\n\n\x0b\n\n\n\n\x08\x00\xd7Gt\xd2\x00\x01[U\xf1Nl=\x08\x00\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./01234567'
	enc = DPHelper.encode(msg)
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print repr(enc)
	ret = ""
	for e in enc:
		e = DPHelper.decode(e)
		ret += e[3]
	print "broken", repr(DPHelper.encode(msg)[0])
	m = DPHelper.decode(DPHelper.encode(msg)[0])
	print repr(msg)
	print repr(ret)
	if ret == msg:
		print "success"
	else:
		print "failure"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print DPHelper.decode(DPHelper.encode("X"*281)[0])
	print DPHelper.decode(DPHelper.encode("X"*281)[1])
	print DPHelper.decode(DPHelper.encode("X"*281)[2])
	print repr(DPHelper.encode("foo & < \r\r > and &lt;")[0].replace("<", "&lt;").replace(">", "&gt;"))
	print DPHelper.decode(DPHelper.encode("foo & < \r\r > and &lt;")[0].replace("<", "&lt;").replace(">", "&gt;"))

