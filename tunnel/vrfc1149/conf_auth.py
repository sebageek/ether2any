from conf import Conf

# WARNING: This config will be overwritten. Only change things here if
#          you know, what you are doing.
if not Conf['twitter']['ACCESS_KEY']:
	Conf['twitter']['ACCESS_KEY'] = None
	Conf['twitter']['ACCESS_SECRET'] = None
