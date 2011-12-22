#!/usr/bin/python
# -*- coding: utf-8 -*-

import base64
import collections
import logging
import math
import re
import sys
import threading
import time
import tweepy
from uphelper import UPHelper

sys.path.append("../../../")

from conf import Conf
from ether2any import Ether2Any
from ether2any.helper import getDstMacFromPkt, isBroadcast, binToHexStr

class TwittStreamHandler(tweepy.StreamListener):
	def __init__(self, dev):
		super(TwittStreamHandler, self).__init__()
		self.dev = dev
		self.fragments = collections.defaultdict(str)
	
	def on_status( self, status ):
		#print '-' * 20
		#print "incoming:", unicode(status.text), "from", dir(status)
		#print "hex:", binToHexStr(status.text), len(status.text)
		# reassemble messages, write them to dev when complete
		(isFragment, packetLen, packetId, packet) = None, None, None, None
		try:
			(isFragment, packetLen, packetId, packet) = UPHelper.decode(status.text)
		except ValueError, e:
			print "Could not decode tweet, omitting (Error was: %s).\n\tText was: %s" % (e, status.text)
			raise
			return
		#print "Parsed packet:", (isFragment, packetLen, packetId)
		#print "\t contents:", packet
		if isFragment:
			self.fragments[packetId] += packet
			print " >+ Added fragment with id", packetId
		else:
			toSend = None
			if self.fragments.has_key(packetId):
				toSend = self.fragments[packetId] + packet
			else:
				toSend = packet
			print " >> Received packet with id", packetId
			print repr(toSend)
			self.dev.write(toSend)
	
	def on_limit(self, track):
		print "We got limited ", track
		print "At the moment there is no error-handling for this, so we just kill everything. Remember: This software doesn't even deserve the label 'alpha' ;)"
		sys.exit(1)
	
	def on_error(self, status_code):
		print "We got an error code: ", status_code
		if status_code == 401:
			print "Better check 'yer twitter-credentials."
			sys.exit(2)
		else:
			print "At the moment there is no error-handling for this, so we just kill everything. Remember: This software doesn't even deserve the label 'alpha' ;)"
			#sys.exit(1)
	
	def on_timeout(self, status_code):
		print "Got an timeout: ", status_code
		print "At the moment there is no error-handling for this, so we just kill everything. Remember: This software doesn't even deserve the label 'alpha' ;)"

class DownstreamThread(threading.Thread):
	def __init__(self, dev, auth, endpoint):
		threading.Thread.__init__(self)
		self.auth = auth
		self.api = tweepy.API(self.auth)
		self.endpoint = endpoint
		self.dev = dev
		self.daemon = True
	
	def run(self):
		stream = tweepy.Stream(auth=self.auth, listener=TwittStreamHandler(self.dev))
		user = self.api.get_user(self.endpoint)
		print "Endpoint is", self.endpoint, "with id", user.id
		stream.filter([user.id])
		#stream.userstream()
		#stream.sample()

class RFC1149(Ether2Any):
	def __init__(self):
		Ether2Any.__init__(self, tap=False)
		
		network = Conf.get("network", {'mtu': 1400})
		self.twitterConf = Conf.get("twitter", None)
		self.endpoint = self.twitterConf['endpoint']
		if not self.endpoint:
			print "No endpoint in configuration, please add one."
			sys.exit(1)
		self.dev.ifconfig(**network)
		self.dev.up()

		self._setupTwitter()
		self.downstream = DownstreamThread(dev=self.dev, auth=self.auth, endpoint=self.endpoint)
		self.downstream.start()
	
	def _requestTwitterTokens(self):
		auth = tweepy.OAuthHandler(self._dec(self.ck), self._dec(self.cs))
		pass
	
	def _setupTwitter(self):
		ck = [17, 39, 65, 39, 25, 22, 38, 30, 20, 38, 33, 69, 27, 0, 61,
		      31, 61, 34, 42, 32]
		cs = [71, 37, 71, 37, 57, 36, 18, 2, 59, 64, 63, 58, 23, 61, 74,
		      30, 34, 68, 38, 33, 56, 1, 3, 74, 29, 9, 41, 32, 33, 7, 52,
			  8, 70, 20, 30, 25, 38, 51, 57, 66, 53, 0, 42]
		self.auth = tweepy.OAuthHandler(self._dec(ck), self._dec(cs))
		if not self.twitterConf['ACCESS_KEY']:
			# request tokens, get access, write tokens down.
			auth_url = self.auth.get_authorization_url()
			print "We have no access token for a twitter account. Please visit the"
			print "url printed down below, login and report back with the PIN."
			print
			print " Authorization URL: %s" % auth_url
			print 
			verifier = raw_input('PIN: ').strip()
			self.auth.get_access_token(verifier)
			self.twitterConf['ACCESS_KEY'] = self.auth.access_token.key
			self.twitterConf['ACCESS_SECRET'] = self.auth.access_token.secret
			authConf = open("conf_auth.py", "w")
			authConf.write("""from conf import Conf

# WARNING: This config was overwritten! If you change it be sure
#          that you know, what you are doing.
if not Conf['twitter']['ACCESS_KEY']:
	Conf['twitter']['ACCESS_KEY'] = "%s"
	Conf['twitter']['ACCESS_SECRET'] = "%s"
""" % (self.twitterConf['ACCESS_KEY'], self.twitterConf['ACCESS_SECRET']))
			authConf.close()
		self.auth.set_access_token(self.twitterConf['ACCESS_KEY'], self.twitterConf['ACCESS_SECRET'])
		self.api = tweepy.API(self.auth)
		self.me = self.api.me()
		print "Logged in as %s" % (self.me.screen_name,)
	
	def _dec(self, s):
		""" ... """
		return "".join(map(lambda x: chr(x+48), reversed(s)))
	
	def sendToNet(self, packet):
		fragments = UPHelper.encode(packet)
		print " >> Sending out %d bytes in %d tweet%s" % (len(packet), len(fragments), len(fragments)!=1 and "s" or "")
		for fragment in fragments:
			# FIXME: catch tweepy.error.TweepError
			self.api.update_status(fragment)

if __name__ == '__main__':
	rfc = RFC1149()
	print "Starting RFC1149 ip-over-twitter service..."
	rfc.run()

