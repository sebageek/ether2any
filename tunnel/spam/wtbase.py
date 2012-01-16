#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Sebastian Lohff <seba@seba-geek.de>
# Licensed under GPL v3 or later

""" wtbase - what the base
Provides classes to encode text to arbitrary bases (base 2^n supported) and
then to textual forms. """

from collections import deque
import math
from random import randint, randrange
import sys
import time

class DecodingException(Exception):
	pass

class Token():
	""" A Token contains a word/sentence and a list of tokenlists which can follow the word. """
	def __init__(self, word, nextLists):
		self.word = word
		self.nextLists = nextLists
	
	def __str__(self):
		return "Token: word \"%s\"" % self.word

class TextGenerator():
	""" Basis generator to en- and decode text-bits. """
	def __init__(self, base=16):
		self.lists = {}
		self.base = base
		self.baseBit = math.log(base, 2)
		if self.baseBit != int(self.baseBit):
			raise ValueError("base must be a power of 2")
		self.baseBit = int(self.baseBit)
		self.startList = "initial"
	
	def addList(self, identifier, newList):
		self.lists[identifier] = newList
	
	def getList(self, identifier):
		return self.lists.get(identifier, None)
	
	def convToBits(self, data):
		""" Converts a data string into n-bit parts defined by self.base. 
		
		Returns a list of integers. """
		l = []
		bit = 0
		rest = 0
		for c in data:
			n = ord(c)
			if bit != 0:
				nc = rest | ((n & ((1 << bit) - 1 << 8-bit)) >> 8-bit)
				l.append(nc)
			while 8-bit >= self.baseBit:
				nc = (n & (((1 << self.baseBit)-1) << 8-bit-self.baseBit)) >> (8-bit-self.baseBit)
				l.append(nc)
				bit += self.baseBit
			rest = (n & (1 << 8-bit) - 1) << self.baseBit-(8-bit)
			bit = (bit+self.baseBit) % 8 % self.baseBit
		if bit != 0:
			l.append(rest)
		return l
	
	def convToNums(self, data):
		""" Reassemble a list of bits back to the original data bytestring. """
		l = ""
		w = 0
		rest = 0
		bit = 0
		for n in data:
			if bit+self.baseBit >= 8:
				w |= n >> self.baseBit - (8-bit)
				bit = self.baseBit - (8-bit)
				l += chr(w)
				if bit != 0:
					w = (n & (1 << bit) - 1) << 8 - bit
				else:
					w = 0
			else:
				w |= n << 8-bit-self.baseBit
				bit = (bit + self.baseBit) % 8
				if bit == 0:
					l += chr(w)
					w = 0
		return l
	
	#def convTo4Bits(self, data):
	#	l = []
	#	for c in data:
	#		n = ord(c)
	#		lo = n & ((1 << 4)-1)
	#		hi = (n & (((1 << 4)-1) << 4)) >> 4
	#		l.extend([hi, lo])
	#	return l


class SpamGenerator(TextGenerator):
	""" De- and encode data in base8 spam text. """
	def __init__(self):
		TextGenerator.__init__(self, base=8)
		self.startList = "greeting"
		self.addList("greeting",
		 {
			0:  Token("Hi,\n\n", ["start"]),
			1:  Token("Hey,\n\n", ["start"]),
			2:  Token("Greetings,\n\n", ["start"]),
			3:  Token("Dear Mr. or Mrs.,,\n\n", ["start"]),
			4:  Token("SPECIAL OFFER!\n", ["start"]),
			5:  Token("High Quality! Read on!\n", ["start"]),
			6:  Token("Best buy!\n\n", ["start"]),
			7:  Token("Dear Valued Customer,\n\n", ["start"]),
			8:  Token("Well, uhm, ", ["start"]),
		 })
		self.addList("start",
		 {
			0:  Token("we are happy to ",		["inform_them"]),
			1:  Token("we are glad to ",		["inform_them"]),
			2:  Token("we gladly ", 			["inform_them"]),
			3:  Token("it happens that we can ",["inform_them"]),
			4:  Token("we want to ", 			["inform_them"]),
			5:  Token("today ", 				["you_have"]),
			6:  Token("ITS TRUE! ", 			["you_have"]),
			7:  Token("you won! ", 				["you_have"]),
			8:  Token("awesome for you, buddy! ",["leaving"]),
		 })
		self.addList("inform_them",
		 {
			0:  Token("inform you, that ",			["you_have"]),
			1:  Token("make a remarkt, that ",		["you_have"]),
			2:  Token("announce, that ", 			["you_have"]),
			3:  Token("celebrate with you! ",		["you_have"]),
			4:  Token("congratulate you, because ",	["you_have"]),
			5:  Token("take the extra step: ",		["you_have"]),
			6:  Token("tell you, that ", 			["you_have"]),
			7:  Token("don't forget about you, ",	["you_have"]),
			8:  Token("move property! ",			["you_have"]),
		 })
		
		self.addList("you_have",
		 {
			0:  Token("you won ",								["won_item"]),
			1:  Token("you have won ",							["won_item"]),
			2:  Token("you aqcuired ", 							["won_item"]),
			3:  Token("one time offer only: ",				 	["won_item"]),
			4:  Token("at your account we found ",				["won_item"]),
			5:  Token("the prince of nigeria offers to you ",	["won_item"]),
			6:  Token("off shore accounts brought you ",		["won_item"]),
			7:  Token("insider traging brought you ", 			["won_item"]),
			8:  Token("you managed to get", 					["won_item"]),
		 })
		
		self.addList("won_item",
		 {
			0:  Token("a sum of ",								["money_sum"]),
			1:  Token("the priceless diamond of Zalanda. " ,	["claim"]),
			2:  Token("free viagra! ", 							["claim"]),
			3:  Token("an inheritance of ", 					["money_sum"]),
			4:  Token("the opportunity to make money online! ", ["claim"]),
			5:  Token("a part of an oil pipe line, worth ", 	["money_sum"]),
			6:  Token("free money - ",							["money_sum"]),
			7:  Token("a rare antique item worth", 				["money_sum"]),
			8:  Token("quiet a bit o' stuff. ", 				["claim"]),
		 })
		
	
		self.addList("money_sum",
		 {
			0:  Token( "5,000,000 USD. ", ["claim"]),
			1:  Token("10,000,000 USD. ", ["claim"]),
			2:  Token(   "300,000 USD. ", ["claim"]),
			3:  Token("13,412,573 USD. ", ["claim"]),
			4:  Token( "7,555,530 USD. ", ["claim"]),
			5:  Token(    "50,000 USD. ", ["claim"]),
			6:  Token( "4,500,000 USD. ", ["claim"]),
			7:  Token("42,000,000 USD. ", ["claim"]),
			8:  Token("87,000,000 USD. ", ["claim"]),
		 })
		
		self.addList("claim",
		 {
			0:  Token("To claim ",			["claimable_item"]),
			1:  Token("To get hold ",		["claimable_item"]),
			2:  Token("To acquire ",		["claimable_item"]),
			3:  Token("To receive ", 		["claimable_item"]),
			4:  Token("To obtain ", 		["claimable_item"]),
			5:  Token("To gatherh ", 		["claimable_item"]),
			6:  Token("To take ownership ", ["claimable_item"]),
			7:  Token("To collect ",		["claimable_item"]),
			8:  Token("To finally get ", 	["claimable_item"]),
		 })
			
		self.addList("claimable_item",
		 {
			0:  Token("this item, please send ",			["sendables"]),
			1:  Token("this stuff, please send ",			["sendables"]),
			2:  Token("your profit, please send ",			["sendables"]),
			3:  Token("these assets, please send ",			["sendables"]),
			4:  Token("this price, please send ",			["sendables"]),
			5:  Token("your earnings, please send ",		["sendables"]),
			6:  Token("this top-line profit, please send ",	["sendables"]),
			7:  Token("this treasure, please send ",		["sendables"]),
			8:  Token("this your winnings, please send ",	["sendables"]),
		 })
			
		self.addList("sendables",
		 {
			0:  Token("us all your information.\n\n",		["more_stuff", "jibberjabber_start"]),
			1:  Token("us your account data.\n\n",			["more_stuff", "jibberjabber_start"]),
			2:  Token("us a transfer-free of 50 USD.\n\n",	["more_stuff", "jibberjabber_start"]),
			3:  Token("us a list of your passwords.\n\n", 	["more_stuff", "jibberjabber_start"]),
			4:  Token("10 valid TAN Numbers.\n\n", 			["more_stuff", "jibberjabber_start"]),
			5:  Token("us your mothers maiden name.\n\n", 	["more_stuff", "jibberjabber_start"]),
			6:  Token("your birth certificate.\n\n", 		["more_stuff", "jibberjabber_start"]),
			7:  Token("a listing of your incomes.\n\n", 	["more_stuff", "jibberjabber_start"]),
			8:  Token("us your personal information.\n\n",	["jibberjabber_start", "leaving"]),
		 })

		self.addList("more_stuff",
		 {
			0:  Token("But wait, there is more! ",								["you_have"]),
			1:  Token("But that is not all! ",									["you_have"]),
			2:  Token("And there is even more! ",								["you_have"]),
			3:  Token("Also ",													["you_have"]),
			4:  Token("And because you seem to be the luckiest person alive: ",	["you_have"]),
			5:  Token("And how does this sound: ",								["you_have"]),
			6:  Token("In addition ",											["you_have"]),
			7:  Token("But... what is this? ",									["you_have"]),
			8:  Token("AND! ",													["you_have"]),
		 })
		
		# loop this. random conversation starter
		self.addList("jibberjabber_start",
		 {
			0:  Token("Would you ",						["jj_consider"]), # have you <tought> <get/buy> <stuff>
			1:  Token("Will you ",						["jj_consider"]),
			2:  Token("Did you ever ",					["jj_consider"]),
			3:  Token("Maybe you ",						["jj_consider"]),
			4:  Token("In ",							["jj_times"]), # in <time> there is <stuff>
			5:  Token("At ",							["jj_times"]),
			6:  Token("Living in ",						["jj_times"]),
			7:  Token("Considering ",					["jj_times"]),
			8:  Token("Everything will be better!",		["leaving"]),
		 })
		
		self.addList("jj_times",
		 {
			0:  Token("times like these ",				["jj_whattodo"]),
			1:  Token("the age of the internet ",		["jj_whattodo"]),
			2:  Token("mobile times ",					["jj_whattodo"]),
			3:  Token("this economic crisis ",			["jj_whattodo"]),
			4:  Token("the time of globalisation ",		["jj_whattodo"]),
			5:  Token("the age of the global village ",	["jj_whattodo"]),
			6:  Token("a world of networks ",			["jj_whattodo"]),
			7:  Token("times of moral values ",			["jj_whattodo"]),
			8:  Token("the here and now ",				["jj_whattodo"]),
		 })
		
		self.addList("jj_consider",
		 {
			0:  Token("consider ",				["jj_buyverb"]),
			1:  Token("think about ",			["jj_buyverb"]),
			2:  Token("take into account ",		["jj_buyverb"]),
			3:  Token("have the desire for ",	["jj_buyverb"]),
			4:  Token("evaluate ",				["jj_buyverb"]),
			5:  Token("reason about ",			["jj_buyverb"]),
			6:  Token("keep in mind ",			["jj_buyverb"]),
			7:  Token("suggest ",				["jj_buyverb"]),
			8:  Token("imagine ",				["jj_buyverb"]),
		 })
		
		self.addList("jj_buyverb",
		 {
			0:  Token("buying ",			["jj_buynoun"]),
			1:  Token("obtaining ",			["jj_buynoun"]),
			2:  Token("purchasing ",		["jj_buynoun"]),
			3:  Token("posessing ",			["jj_buynoun"]),
			4:  Token("owning ",			["jj_buynoun"]),
			5:  Token("creating ",			["jj_buynoun"]),
			6:  Token("crafting ",			["jj_buynoun"]),
			7:  Token("receiving ",			["jj_buynoun"]),
			8:  Token("getting ",			["jj_buynoun"]),
		 })
		
		self.addList("jj_buynoun",
		 {
			0:  Token("a new car? ",						["jibberjabber_start"]),
			1:  Token("an own house? ",						["jibberjabber_start"]),
			2:  Token("the women of your dreams? ",			["jibberjabber_start"]),
			3:  Token("a healthy sexual relationship? ",	["jibberjabber_start"]),
			4:  Token("an own country? ",					["jibberjabber_start"]),
			5:  Token("your penis size? ",					["jibberjabber_start"]),
			6:  Token("free viagra? ",						["jibberjabber_start"]),
			7:  Token("the newest of apples products? ",	["jibberjabber_start"]),
			8:  Token("a brand new kitchentable? ",			["jibberjabber_start", "leaving"]),
		 })
		
		self.addList("jj_whattodo",
		 {
			0:  Token("you should always think about ",					["jj_whattodonoun"]),
			1:  Token("the moral values predict good values for  ",		["jj_whattodonoun"]),
			2:  Token("society will talk about ",						["jj_whattodonoun"]),
			3:  Token("all your friends will admire ",					["jj_whattodonoun"]),
			4:  Token("the talk of your social group will be ",			["jj_whattodonoun"]),
			5:  Token("genderstudies will celebrate ",					["jj_whattodonoun"]),
			6:  Token("considering everything about ",					["jj_whattodonoun"]),
			7:  Token("your possibilities are unimaginable regarding ",	["jj_whattodonoun"]),
			8:  Token("things are looking good regarding",				["jj_whattodonoun"]),
		 })
		
		self.addList("jj_whattodonoun",
		 {
			0:  Token("the stock market. ",										["jibberjabber_start"]),
			1:  Token("your penis size. ",										["jibberjabber_start"]),
			2:  Token("how attractive you are to the opposite sex. ",			["jibberjabber_start"]),
			3:  Token("your investment in foreign oil company funds. ",			["jibberjabber_start"]),
			4:  Token("mobility options for going into the mobile business. ",	["jibberjabber_start"]),
			5:  Token("a bottle from our best collection of tasteful wines. ",	["jibberjabber_start"]),
			6:  Token("buying viagra online NOW! ",								["jibberjabber_start"]),
			7:  Token("getting more money out of your job! ",					["jibberjabber_start"]),
			8:  Token("winning money in Las Vegas! ",							["leaving"]),
		 })
		# HACK: At the moment this does not support choosing random words
		self.addList("leaving",
		 {
			0:  Token(None,			[None]),
			1:  Token(None,			[None]),
			2:  Token(None,			[None]),
			3:  Token(None,			[None]),
			4:  Token(None,			[None]),
			5:  Token(None,			[None]),
			6:  Token(None,			[None]),
			7:  Token(None,			[None]),
			8:  Token("\n\nYours faithfully,\n\n",	["leave_name_%d" % i for i in range(8)]),
		 })
		for i in zip(range(8), ["Ernest Schlempl", "Bernhard Vonneguth", "Maria Peters", "Sibille Harstall", "Richmond Maltitz", "Benno Boch", "Tatjana Horn", "Marcell Hintzenstern"]):
			self.addList("leave_name_%d" % i[0], {8: Token(i[1], [None])}) 
		
		self.addList("m",
		 {
			0:  Token("",			[None]),
			1:  Token("",			[None]),
			2:  Token("",			[None]),
			3:  Token("",			[None]),
			4:  Token("",			[None]),
			5:  Token("",			[None]),
			6:  Token("",			[None]),
			7:  Token("",			[None]),
			8:  Token("",			[None]),
		 })
	
	def encode(self, data):
		""" Encode data: Traverse wordlists. Return spam-text. """
		listBits = self.convToBits(data)
		listBitsLen = len(listBits)
		nextList = self.startList
		pos = 0
		text = ""
		# for performance!
		getList = self.getList
		while nextList:
			bit = 8
			if pos < listBitsLen:
				bit = listBits[pos]
			l = getList(nextList)
			idx = pos < listBitsLen and listBits[pos] or self.base
			tok = l[bit]
			#text.append(tok.word)
			text += tok.word
			nextList = tok.nextLists[randrange(0, len(tok.nextLists))]
			if bit != 8:
				pos += 1
		return text
	
	def hexdump(self, data):
		return ((len(data)*"%02x ") % tuple(map(lambda x: ord(x), data))).rstrip()
	
	def decode(self, text):
		""" Decode spam-text to original data. """
		text = text.lstrip().replace("\r\n", "\n")
		nextLists = [self.startList]
		result = deque()
		findInList = self.findInList
		while text != "" and len(nextLists) > 0 and nextLists[0]:
			match = False
			for listname in nextLists:
				(match, bits, token) = findInList(text, listname)
				if match:
					#print "matched value ", bits, "word", token.word
					if bits != 8:
						result.append(bits)
					text = text.replace(token.word, "", 1)
					nextLists = token.nextLists
					#print "next possible lists are", nextLists
					break
			if not match:
				#print "BASEWTF"
				#print nextLists
				#print self.getList(nextLists[0])
				#print self.hexdump(text)
				#print " --------------- "
				print "Beginning of text (hex): ", self.hexdump(text[:10])
				for l in self.getList(nextLists[0]):
					print l, self.getList(nextLists[0])[l], self.hexdump(self.getList(nextLists[0])[l].word)
				raise DecodingException("Could not decode text (no more possible lists). Remaining text is \"%s\"" % text)
		# print "text remaining", text
		convBack = self.convToNums(result)		
		return convBack
	
	def findInList(self, text, listname):
		sList = self.getList(listname)
		for key in sList:
			#print "\tTesting word: ", sList[key].word
			w = sList[key].word
			if w and (text.startswith(w)):
				#or \
				#text.replace("\n", "", 1).startswith(sList[key].word.replace("\n", "", 1))):
				# HACK: Newline matching problem, mail classes add extra newlines
				#       ==> matching not possible
				token = sList[key]
				#print "\t==> MATCH in list", listname
				return (True, key, token)
		#print "\tNO match in list", listname
		return (False, -1, None)

def main():
	""" Main function, does en- and decoding test for testing purposes. """
	# data = "\xF2\x51\x92\x61\x9d\x1f\x0F\xb7\xaa\xc1"
	#data = "".join(sys.argv[1:])
	#for d in data:
	#	print ord(d),
	#print ""
	#t = SpamGenerator()
	#d = t.convToBits(data)
	#e = t.convToNums(d)
	#print d
	#for a in e:
	#	print ord(a),
	#print ""
	#msg = t.encode(data)
	##print res, "\n"
	#res = t.decode(msg)
	#print 
	#print d
	#for d in data:
	#	print ord(d),
	#print ""
	#print msg
	t = SpamGenerator()
	#data = "".join([chr(randint(0, 255)) for i in range(1500)])
	#t.encode(data)
	#return
	msg = open("file.txt", "r").read()
	t.decode(msg)
	print t.encode("Hallo ihr beiden")

if __name__ == '__main__':
	main()

