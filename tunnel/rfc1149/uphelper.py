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

if __name__ == '__main__':
	msg = u'\U000c0000\U00060800\u4500\u0344\U000f225d\U000b4000\U00054006\U0004ed2e\U00040a0a\u0a0a\U000c0a0a\u0a0b\x16\u9fba\u2c1d\u8297\uc02e\u662b\u8018U\u1ccc\x00\u0101\u080a\u49b1\ua6ad\u05d6\u3cd6\x00\u030c\u0a14\u0eff\uf074\u828b\u11e1\uc732\u7eaa\u1756\u4a7b\x00~\u6469\u6666\u6965\u2d68\u656c\u6c6d\u616e\u2d67\u726f\u7570\u2d65\u7863\u6861\u6e67\u652d\u7368\u6132\u3536\u2c64\u6966\u6669\u652d\u6865\u6c6c\u6d61\u6e2d\u6772\u6f75\u702d\u6578\u6368\u616e\u6765\u2d73\u6861\u312c\u6469\u6666\u6965\u2d68\u656c\u6c6d\u616e\u2d67\u726f\u7570\u3134\u2d73\u6861\u312c\u6469\u6666\u6965\u2d68\u656c\u6c6d\u616e\u2d67\u726f\u7570\u312d\u7368\u6131\x00\x0f\u7373\u682d\u7273\u612c\u7373\u682d\u6473\u7300\x00\u9d61\u6573\u3132\u382d\u6374\u722c\u6165\u7331\u3932\u2d63\u7472\u2c61\u6573\u3235\u362d\u6374\u722c\u6172\u6366\u6f75\u7232\u3536\u2c61\u7263\u666f'
	print UPHelper.decode(msg)
	sys.exit(0)
	enc = UPHelper.encode(msg)
	print enc
	print UPHelper.decode(enc[-1])
	msg = '\x00\x00\x08\x00E\x00\x00T\x00\x00@\x00@\x01\x12\x81\n\n\n\x0b\n\n\n\n\x08\x00\xd7Gt\xd2\x00\x01[U\xf1Nl=\x08\x00\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./01234567'
	msg = u'\U0004352c\U0006686d\u6163\U00092d73\U00026861\U0003312c\u756d\U000a6163\U00092d36\U00013440\U00086f70\u656e\u7373\u682e\u636f\u6d2c\u686d\u6163\u2d72\u6970\u656d\u6431\u3630\u2c68\u6d61\u632d\u7269\u7065\u6d64\u3136\u3040\u6f70\u656e\u7373\u682e\u636f\u6d2c\u686d\u6163\u2d73\u6861\u312d\u3936\u2c68\u6d61\u632d\u6d64\u352d\u3936\x00i\u686d\u6163\u2d6d\u6435\u2c68\u6d61\u632d\u7368\u6131\u2c75\u6d61\u632d\u3634\u406f\u7065\u6e73\u7368\u2e63\u6f6d\u2c68\u6d61\u632d\u7269\u7065\u6d64\u3136\u302c\u686d\u6163\u2d72\u6970\u656d\u6431\u3630\u406f\u7065\u6e73\u7368\u2e63\u6f6d\u2c68\u6d61\u632d\u7368\u6131\u2d39\u362c\u686d\u6163\u2d6d\u6435\u2d39\u3600\x00\u156e\u6f6e\u652c\u7a6c\u6962\u406f\u7065\u6e73\u7368\u2e63\u6f6d\x00\x15\u6e6f\u6e65\u2c7a\u6c69\u6240\u6f70\u656e\u7373\u682e\u636f\u6d00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.'
	print UPHelper.decode(msg)
	sys.exit(0)
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

