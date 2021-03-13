from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta
import os.path

try:
	from pyfcm import FCMNotification
	import firebase_admin
	from firebase_admin import credentials
	from firebase_admin import firestore
	has_notification_lib = True
except:
	has_notification_lib = False

# ==========================================================================================================================
SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1
LOCAL_CRED = '/opt/odoo/tokobesiVIP-ade097b8b6e5.json'

class tbvip_fcm_notif(osv.osv):
	_name = 'tbvip.fcm_notif'
	_description = 'Notification via Firestore Cloud Messaging'
	_auto = False

	#push_service = None

	'''
	def __init__(self):
		#init Firestore DB			
		cred = credentials.ApplicationDefault()
		firebase_admin.initialize_app(cred, {'projectId': 'awesome-beaker-150403',})

		#FCM Notification Server cred
		self.push_service = FCMNotification(api_key="AAAAl1iYTeo:APA91bHp-WiAzZxjiKa93znVKsD1N2AgtgwB1azuEYyvpWHyFR2WfZRj3UPXMov9PzbCBpOCScz8YN_Ki2kEVf_5V43bgUDjJmHSh78NOK0KLWOU2cgYUe9KClTkTTwpTzUcaBB2hVqT")
	'''

	#init Firestore DB	

	if has_notification_lib:
		if  os.path.isfile(LOCAL_CRED):
			cred = credentials.Certificate(LOCAL_CRED)
			firebase_admin.initialize_app(cred)
		else:
			cred = credentials.ApplicationDefault()
			firebase_admin.initialize_app(cred, {'projectId': 'awesome-beaker-150403',})
	else:
		cred = None


	def send_notification(self,cr,uid,message_title,message_body,context={}): #context : is_stored,branch,category,sound_idx,lines,alert

		if not has_notification_lib: return
		#Get Param Value
		#param_obj = self.pool.get('ir.config_parameter')
		#param_ids = param_obj.search(cr, uid, [('key','in',['notification_topic'])])
		#notification_topic = ''
		#for param_data in param_obj.browse(cr, uid, param_ids):
		#	if param_data.key == 'notification_topic':
		#		notification_topic = param_data.value

		branch_name = context.get('branch','VIP')
		#SELECT SOUND FOR NOTIFICATION
		sound_index = context.get('sound_idx',0)
		sound = 'notification'+str(sound_index)+'.mp3'

		#push notification
		push_service = FCMNotification(api_key="AAAAl1iYTeo:APA91bHp-WiAzZxjiKa93znVKsD1N2AgtgwB1azuEYyvpWHyFR2WfZRj3UPXMov9PzbCBpOCScz8YN_Ki2kEVf_5V43bgUDjJmHSh78NOK0KLWOU2cgYUe9KClTkTTwpTzUcaBB2hVqT")
		push_service.notify_topic_subscribers(topic_name=branch_name, message_title=message_title,message_body=message_body, sound=sound)

		#Firebase Firestore
		if context.get('is_stored',True):		
			category = context.get('category','BASE')
			lines = context.get('lines','')
			now = datetime.now() + timedelta(hours = 7)
			#now = datetime.now()
			alert = context.get('alert','!')
			db = firestore.client()
			doc_ref = db.collection(unicode(branch_name)).document()
			doc_ref.set({
				u'branch':unicode(branch_name),
				u'category':unicode(category),
				u'date':unicode(now.strftime("%d/%m/%Y %H:%M:%S")),
				u'timestamp':datetime.now(),
				u'title':unicode(message_title),
				u'message':unicode(message_body),
				u'lines':unicode(lines),
				u'state':u'unread',
				u'alert':unicode(alert),
			})
