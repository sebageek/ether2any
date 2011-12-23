#!/usr/bin/python
# -*- coding: utf-8 -*-

import bitarray
import random
import re

class UPHelper():
	""" The Unicode Packet Helper
	
	Twitter supports 140 chars, while a char can be a unicode
	character. For a unicode character there are 2^20 possibilities.
	For the sake of lazyness we put two bytes in each character, using
	only 2^16. The remaining 4 bits can be used for metadata or whatever.
	
	The header in the metadata is as following:
	<fragment bit (1 if packet is a fragment, 0 if last in row)>
	<9 bits length of payload>
	<32 bit random paket id greater than 0>"""

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
		""" Generate list of packets with a header from data. """
		packetId = random.randint(1, 2**32)
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
				ret += unichr(val)
				i += 2
			fragments[y] = ret
		return fragments
	
	@staticmethod
	def reassembleBrokenChars(packet):
		""" Reassemble broken characters back to unicode.
		
		Twitter breaks some characters (currently known range is 0xd800 - 0xdfff)
		into r"\XXX\XXX\XXX", X being octal numbers. These are actually strings,
		so one unicodechar from the range gets broken up to 12 chars.
		
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
			if o > 65535:
				# -.-
				a = unichr(0xd800 + ((o >> 10) - 64))
				b = unichr(0xdc00 + (o & 1023))
				packet = packet.replace(c, a+b)
		return packet
	
	@staticmethod
	def decode(packet):
		""" Decodes an unicodestring (packet) back to header + data
		
		Returns: tupel(isFragmented, packetLen, packetId, data) """
		
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
			data.append(chr(p >> 8))
			data.append(chr(p & 255))
		data = "".join(data)
		return (isFragmented, packetLen, packetId, data[:packetLen])

if __name__ == '__main__':
	msg = '\x00\x00\x08\x00E\x00\x00T\x00\x00@\x00@\x01\x12\x81\n\n\n\x0b\n\n\n\n\x08\x00\xd7Gt\xd2\x00\x01[U\xf1Nl=\x08\x00\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./01234567'
	msg = u'\U000c1011\U00061213\U00011415\U000a1617\U00031819\U00041a1b\U000a1c1d\U000a1e1f\U000c2021\u2223\U000c2425\u2627\u2829\u2a2b\u2c2d\u2e2f\u3031\u3233\u3435\u3637\u3839\u3a3b\u3c3d\u3e3f\u4041\u4243\u4445\u4647\u4849\u4a4b\u4c4d\u4e4f\u5051\u5253\u5455\u5657\u5859\u5a5b\u5c5d\u5e5f\u6061\u6263\u6465\u6667\u6869\u6a6b\u6c6d\u6e6f\u7071\u7273\u7475\u7677\u7879\u7a7b\u7c7d\u7e7f\u8081\u8283\u8485\u8687\u8889\u8a8b\u8c8d\u8e8f\u9091\u9293\u9495\u9697\u9899\u9a9b\u9c9d\u9e9f\ua0a1\ua2a3\ua4a5\ua6a7\ua8a9\uaaab\uacad\uaeaf\ub0b1\ub2b3\ub4b5\ub6b7\ub8b9\ubabb\ubcbd\ubebf\uc0c1\uc2c3\uc4c5\uc6c7\uc8c9\ucacb\ucccd\ucecf\ud0d1\ud2d3\ud4d5\ud6d7\ud8d9\udadb\udcdd\udedf\ue0e1\ue2e3\ue4e5\ue6e7\ue8e9\ueaeb\ueced\ueeef\uf0f1\uf2f3\uf4f5\uf6f7\uf8f9\ufafb\ufcfd\ufeff\x01\u0203\u0405\u0607\u0809\u0a0b\u0c0d\u0e0f\u1011\u1213\u1415\u1617\u1819\u1a1b\u1c1d\u1e1f\u2021\u2223\u2425\u2627'
	msg = '\x00\x00\x08\x00E\x00\x04\x04\x00\x00@\x00@\x01\x0e\xd1\n\n\n\x0b\n\n\n\n\x08\x005f\x03\xec\x00\x01\xe7\xf7\xf1NR\xf2\r\x00\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7'
	enc = UPHelper.encode(msg)
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print enc
	ret = ""
	for e in enc:
		e = UPHelper.decode(e)
		print e[0:3]
		print e[3]
		ret += e[3]
	m = UPHelper.decode(UPHelper.encode(msg)[0])
	#print m
	if ret == msg:
		print "success"
	else:
		print "failure"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print UPHelper.decode(UPHelper.encode("X"*281)[0])
	print UPHelper.decode(UPHelper.encode("X"*281)[1])
	#msg = "".join([chr(i) for i in range(256)])
	#msg += "".join([chr(i) for i in range(256)])
	#p = UPHelper.encode(msg)
	#print repr(msg)
	#for x in p:
	#	print UPHelper.decode(x)

