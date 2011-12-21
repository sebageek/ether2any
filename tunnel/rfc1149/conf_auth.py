from conf import Conf

# WARNING: This config will be overwritten if you use the scripts internal
#          way to get an access key.
if not Conf['twitter']['ACCESS_KEY']:
	Conf['twitter']['ACCESS_KEY'] = None
	Conf['twitter']['ACCESS_SECRET'] = None
