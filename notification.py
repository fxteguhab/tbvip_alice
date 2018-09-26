from openerp import SUPERUSER_ID
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
LOCAL_CRED = 'tokobesiVIP-ade097b8b6e5.json'

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
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_topic'])])
		notification_topic = ''
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_topic':
				notification_topic = param_data.value

		if (notification_topic != ''):
			push_service = FCMNotification(api_key="AAAAl1iYTeo:APA91bHp-WiAzZxjiKa93znVKsD1N2AgtgwB1azuEYyvpWHyFR2WfZRj3UPXMov9PzbCBpOCScz8YN_Ki2kEVf_5V43bgUDjJmHSh78NOK0KLWOU2cgYUe9KClTkTTwpTzUcaBB2hVqT")		
			
			#SELECT SOUND FOR NOTIFICATION
			sound_index = context.get('sound_idx',0)
			sound = 'notification'+str(sound_index)+'.mp3'
			
			#push notification
			push_service.notify_topic_subscribers(topic_name=notification_topic, message_title=message_title,message_body=message_body, sound=sound)

			if context.get('is_stored',True):
				branch = context.get('branch','VIP')
				category = context.get('category','BASE')
				lines = context.get('lines','')
				now = datetime.now() + timedelta(hours = 7)
				#now = datetime.now()
				alert = context.get('alert','!')
				db = firestore.client()
				doc_ref = db.collection(u'notification').document()
				doc_ref.set({
					u'branch':unicode(branch),
					u'category':unicode(category),
					u'date':unicode(now.strftime("%d/%m/%Y %H:%M:%S")),
					u'timestamp':datetime.now(),
					u'title':unicode(message_title),
					u'message':unicode(message_body),
					u'lines':unicode(lines),
					u'state':u'unread',
					u'alert':unicode(alert),
				})



class sale_order(osv.osv):
	_inherit = 'sale.order'

	def action_button_confirm(self, cr, uid, ids, context=None):
		result = super(sale_order, self).action_button_confirm(cr, uid, ids, context)
		#Get Param Value
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_sale_limit'])])
		sale_limit = 0
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_sale_limit':
				sale_limit = float(param_data.value)
		
		#for sale in self.browse(cr, uid, ids):
		sale = self.browse(cr, uid, ids)
		value = sale.amount_total
		row_count = len(sale.order_line)
		branch = sale.branch_id.name
		cust_name = sale.partner_id.display_name
		bon_number = sale.bon_number
		desc = sale.client_order_ref
		employee = sale.employee_id.name
		line_str = ''
		product_name = ''
		product_watch = ''
		for line in sale.order_line:
			product_name = line.product_id.name_template
			if line.product_id.sale_notification: 
				product_watch = '[!!]'
				product_name += product_watch
			
			line_str += str(line.product_uos_qty)+':'+product_name + '\n'				

		if ((value >= sale_limit) or (product_watch == '[!!]')):
			alert = '!'
			for alert_lv in range(int(value // sale_limit )):
				alert += '!'
			message_title = 'SALES('+branch+')'+product_watch+':'+cust_name
			message_body = employee+'('+str(bon_number)+'):'+str(row_count)+' row(s):'+str("{:,.0f}".format(value))# +'\n'+'Cust:'+cust_name
			if (desc):
					message_body = message_body +'\n'+ 'Desc:'+ str(desc)
			
			context = {
				'branch' : branch,
				'category':'SALES',
				'sound_idx':SALES_SOUND_IDX,
				'lines' : line_str,
				'alert' : alert,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result

class purchase_order(osv.osv):
	_inherit = 'purchase.order'

	def wkf_confirm_order(self, cr, uid, ids, context=None):
		result = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)

		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_purchase_limit'])])
		purchase_limit = 0
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_purchase_limit':
				purchase_limit = float(param_data.value)

		#for purchase in self.browse(cr, uid, ids, context=context):
		purchase = self.browse(cr, uid, ids, context=context)
		value = purchase.amount_total
		supplier_name = purchase.partner_id.display_name
		row_count = len(purchase.order_line)
		line_str = ''
		product_watch = ''
		for line in purchase.order_line:
			qty_available = line.product_id.qty_available
			product_name = line.product_id.name_template
			if line.product_id.sale_notification: 
				product_watch = '[!!]'
				product_name += product_watch

			line_str += str(line.product_qty)+':'+product_name + '\n'+'     Stock:'+str(qty_available)+'\n'
				
		if ((value >= purchase_limit) or (product_watch == '[!!]')):
			alert = '!'
			for alert_lv in range(int(value // purchase_limit )):
				alert += '!'
			message_title = 'PURCHASE'+product_watch+':'+str(supplier_name)
			message_body = str(row_count)+' row(s):'+str("{:,.0f}".format(value)) 

			context = {
				'category':'PURCHASE',
				'sound_idx':PURCHASE_SOUND_IDX,
				'lines' : line_str,
				'alert' : alert,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result


class product_template(osv.osv):
	_inherit = 'product.template'
	_columns = {
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
	}

	# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_template, self).create(cr, uid, vals, context)
		
		name = ''
		#for product in self.browse(cr, uid, new_id, context=context):
		product = self.browse(cr, uid, new_id, context=context)
		name = product.name
		create_by = product.create_uid.name

		message_title = 'NEW ITEM CREATION'
		message_body = 'NAME:'+str(name) +'\n'+'Created by :' +str(create_by)
		context = {
				'category':'PRODUCT',
				'sound_idx':PRODUCT_SOUND_IDX,
				}
		self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return new_id


class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
	}


	def write(self, cr, uid, ids, data, context=None):
		result = super(product_category, self).write(cr, uid, ids, data, context)
		sale_notification = data['sale_notification'] if 'sale_notification' in data else False
		purchase_notification = data['purchase_notification'] if 'purchase_notification' in data else False

		for category_id in ids:
			product_obj = self.pool.get('product.template')
			product_ids = product_obj.search(cr, uid, [
				('categ_id', '=', category_id),
			])
			#if data.get('sale_notification', False):
			product_obj.write(cr, uid, product_ids, {
				'sale_notification': sale_notification,
				'purchase_notification': purchase_notification,
			})
			#if data.get('purchase_notification', False):
			#product_obj.write(cr, uid, product_ids, {
			#	'purchase_notification': purchase_notification,
			#})
		return result


class account_invoice_line(osv.osv):
	_inherit = 'account.invoice.line'

	def _cost_price_watcher(self, cr, uid, vals, context):
		result = super(account_invoice_line, self)._cost_price_watcher(cr, uid, vals, context=context)

		price_unit_nett = context.get('price_unit_nett',0)
		price_unit_nett_old = context.get('price_unit_nett_old',0)
		price_unit = context.get('price_unit',0)
		price_unit_old = context.get('price_unit_old',0)
		name = context.get('name','')
		invoice_id = context.get('invoice_id',0)
		sell_price_unit = context.get('sell_price_unit',0)
		buy_price_unit = context.get('buy_price_unit',0)
		discount_string = context.get('discount_string','0')
		discount_string_old = context.get('discount_string_old','0')
		partner_names = context.get('partner_name','')
		partner_name = partner_names if partner_names else '-'
		partner_id = context.get('partner_id','')
		invoice_type = context.get('type',0)

		message_body = ''
		line_str = ''
		# cek perubahan harga
		if (price_unit_nett_old > 0) and (price_unit > 0) and (round(price_unit_nett_old) != round(price_unit_nett)):
			if round(price_unit_old) != round(price_unit):
				message_body += 'PLIST From '+ str("{:,.0f}".format(price_unit_old))+' to '+str("{:,.0f}".format(price_unit)) +'\n'
			if discount_string_old != discount_string:
				message_body += 'DISC From '+ str(discount_string_old)+' to '+ str(discount_string) +'\n'
			line_str += 'NETT From '+ str("{:,.0f}".format(price_unit_nett_old))+' to '+str("{:,.0f}".format(price_unit_nett)) +'\n'
			line_str += 'PARTNER:'+partner_name +'\n'
			
			if invoice_type == 'in_invoice': #buy
				message_title = 'PURCHASE$:'+str(name)
				line_str += 'SELL PRICE:'+str("{:,.0f}".format(sell_price_unit)) +'\n'
			elif invoice_type == 'out_invoice': #sell
				message_title = 'SALE$:'+str(name)
				line_str += 'BUY PRICE:'+str("{:,.0f}".format(buy_price_unit)) +'\n'
			
			message_body += line_str
			context = {
				'category':'INVOICE',
				'sound_idx':PURCHASE_SOUND_IDX,
				'alert' : '!!!!!!!',
				'lines' : line_str,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result


class tbvip_bon_book(osv.osv):
	_inherit = "tbvip.bon.book"

	def create(self, cr, uid, vals, context=None):
		result = super(tbvip_bon_book, self).create(cr, uid, vals, context)
		residual = 	self._cek_last_book_residual(cr,uid,vals['employee_id'],vals['branch_id'])
		employee_obj = self.pool.get('hr.employee')
		branch_obj = self.pool.get('tbvip.branch')
		employee_name = employee_obj.browse(cr,uid,vals['employee_id']).name
		branch_name = branch_obj.browse(cr,uid,vals['branch_id']).name
		if (residual>3):
			message_body = ''	
			message_title = 'BON ('+str(employee_name)+'-'+str(branch_name)+')::'+str(residual)+' lbr'
			alert = '!'
			for alert_lv in range(residual):
				alert += '!'

			context = {
				'category':'SALES',
				'sound_idx':PURCHASE_SOUND_IDX,
				'alert' : alert,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		return result

class stock_inventory(osv.osv):
	_inherit = 'stock.inventory'

	def action_done(self, cr, uid, ids, context=None):
		result = super(stock_inventory, self).action_done(cr, uid, ids, context=context)
		#for inventory in self.browse(cr, uid, ids, context=context):
		row_total_qty = 0
		inventory = self.browse(cr, uid, ids, context=context)
		for line in inventory.line_ids:
			row_total_qty += line.product_qty
			selisih =  line.product_qty - line.theoretical_qty
			delta_old_and_new_total_qty_line = abs(selisih)
			old_qty = line.theoretical_qty if line.theoretical_qty > 0 else 1
			precentage = (delta_old_and_new_total_qty_line/old_qty) * 100
			# checking penalty
			if precentage > 10:		
				message_title = 'SO('+str(line.product_id.name_template)+')::'+str(inventory.location_id.name)	
				message_body = 'DELTA:'+str(selisih)+'('+str(precentage)+'%)'+'\n'+'SO BY:'+str(inventory.employee_id.name_related)+'\n' + 'ADMIN:'+str(inventory.create_uid.partner_id.name)+'\n'+'OLD QTY:'+str(line.theoretical_qty)+'\n'+'NEW QTY:'+str(line.product_qty)
				alert = ''
				for alert_lv in range(int(precentage/10)):
					alert += '!'
				context = {
					'category':'PRODUCT',
					'sound_idx':PRODUCT_SOUND_IDX,
					'alert' : alert,
					}
				self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		return result

class product_current_price(osv.osv):
	_inherit = 'product.current.price'

	def create(self, cr, uid, vals, context={}):
		new_id = super(product_current_price, self).create(cr, uid, vals, context)
		if (uid != SUPERUSER_ID):	
			for prices in self.browse(cr, uid, new_id, context=context):
				product_id = prices.product_id
				tipe = prices.price_type_id
				create_id = prices.create_uid
				partner_id = prices.partner_id
				price_unit_nett = prices.nett_1
				price_unit = prices.price_1
				discount_string = prices.disc_1
				product_uom = prices.uom_id_1

				message_body = ''
				line_str = ''
				message_title = ''
				price_unit_old = 0
				discount_string_old = '0'
				price_unit_nett_old = 0
				now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')

				if (tipe.type == 'sell'):
					message_title = 'SELL$:'+str(product_id.name_template)
				elif (tipe.type == 'buy'):
					message_title = 'BUY$:'+str(product_id.name_template)

				domain = [
					('price_type_id', '=', tipe.id),
					('product_id', '=', product_id.id),
					('start_date','<=',now),
					('partner_id','=',partner_id.id),
				]
				old_price_ids = self.search(cr, uid, domain, order='start_date DESC', limit=2)

				if len(old_price_ids) > 1:
					old_price_id = self.browse(cr,uid,old_price_ids[1],context=None)
					price_unit_old = old_price_id.price_1
					discount_string_old = old_price_id.disc_1
					price_unit_nett_old = old_price_id.nett_1

				message_body += 'PLIST From '+ str("{:,.0f}".format(price_unit_old))+' to '+str("{:,.0f}".format(price_unit)) +'\n'
				message_body += 'DISC From '+ str(discount_string_old)+' to '+ str(discount_string) +'\n'
				line_str += 'NETT From '+ str("{:,.0f}".format(price_unit_nett_old))+' to '+str("{:,.0f}".format(price_unit_nett)) +'\n'
				line_str += 'PARTNER:'+ partner_id.name +'\n'
				line_str += 'Created by :' +str(create_id.name)
				message_body += line_str

				context = {
						'category':'PRODUCT',
						'sound_idx':PRODUCT_SOUND_IDX,
						'alert' : '!!!!!!!',
						'lines' : line_str,
						}
				self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		
	
		return new_id

		'''
			product_current_price_obj = self.pool.get('product.current.price')
			now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
			sell_price_type_id = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])[0]
			buy_price_type_id = self.pool.get('price.type').search(cr, uid, [('type','=','buy'),('is_default','=',True),])[0]
			general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')[1]
			message_body = ''
			line_str = ''

			#GET OLD PRICE
			domain = [
				('price_type_id', '=', buy_price_type_id),
				('product_id', '=', product_id.id),
				('start_date','<=',now),
			]
			current_price_buy_ids = product_current_price_obj.search(cr, uid, domain, order='start_date DESC', limit=2)
			domain = [
				('price_type_id', '=', sell_price_type_id),
				('product_id', '=', product_id.id),
				('start_date','<=',now),
				('partner_id','=',general_customer_id),
			]
			current_price_sell_ids = product_current_price_obj.search(cr, uid, domain, order='start_date DESC', limit=2)
			
			partner_name = ''
			price_unit_nett_last_buy = 0
			price_unit_nett_buy_old = 0
			price_unit_buy_old = 0
			discount_string_buy_old = '0'
			price_unit_nett_last_sell = 0
			price_unit_nett_sell_old = 0
			price_unit_sell_old = 0
			discount_string_sell_old = '0'

			if (len(current_price_buy_ids) > 0): 	
				for product_current_price_buy_ids in product_current_price_obj.browse(cr, uid, current_price_buy_ids[0],context=context):
					price_unit_nett_last_buy = product_current_price_buy_ids[0].nett_1
				if (len(current_price_buy_ids) > 1): 
					for product_current_price_buy_ids in product_current_price_obj.browse(cr, uid, current_price_buy_ids[1],context=context):
						price_unit_nett_buy_old = product_current_price_buy_ids.nett_1
						price_unit_buy_old = product_current_price_buy_ids.price_1
						discount_string_buy_old = product_current_price_buy_ids.disc_1
						partner_name = product_current_price_buy_ids.partner_id.name

			if (len(current_price_sell_ids) > 0): #cuman ada current price yg baru dibikin itu
				for product_current_price_sell_ids in product_current_price_obj.browse(cr, uid, current_price_sell_ids[0],context=context):
					price_unit_nett_last_sell = product_current_price_sell_ids[0].nett_1
				if (len(current_price_sell_ids) > 1): 
					for product_current_price_sell_ids in product_current_price_obj.browse(cr, uid, current_price_sell_ids[1],context=context):
						price_unit_nett_sell_old = product_current_price_sell_ids.nett_1
						price_unit_sell_old = product_current_price_sell_ids.price_1
						discount_string_sell_old = product_current_price_sell_ids.disc_1	

		
			if (tipe.type == 'sell'):
				message_title = 'NEW SELL$:'+str(product_id.name_template)					
				if round(price_unit_sell_old) != round(price_unit):
					message_body += 'PLIST From '+ str("{:,.0f}".format(price_unit_sell_old))+' to '+str("{:,.0f}".format(price_unit)) +'\n'
				if discount_string_sell_old != discount_string:
					message_body += 'DISC From '+ str(discount_string_sell_old)+' to '+ str(discount_string) +'\n'
				line_str += 'NETT From '+ str("{:,.0f}".format(price_unit_nett_sell_old))+' to '+str("{:,.0f}".format(price_unit_nett)) +'\n'	
				line_str += 'BUY PRICE:'+str("{:,.0f}".format(price_unit_nett_last_buy)) +'\n'+'Supplier:'+partner_name
				message_body += line_str
				
			if (tipe.type == 'buy'):
				partner_name = partner_id.name
				message_title = 'NEW BUY$:'+str(product_id.name_template)					
				if round(price_unit_buy_old) != round(price_unit):
					message_body += 'PLIST From '+ str("{:,.0f}".format(price_unit_buy_old))+' to '+str("{:,.0f}".format(price_unit)) +'\n'
				if discount_string_buy_old != discount_string:
					message_body += 'DISC From '+ str(discount_string_buy_old)+' to '+ str(discount_string) +'\n'
				line_str += 'NETT From '+ str("{:,.0f}".format(price_unit_nett_buy_old))+' to '+str("{:,.0f}".format(price_unit_nett)) +'\n'	
				line_str += 'SELL PRICE:'+str("{:,.0f}".format(price_unit_nett_last_sell)) +'\n'+'Supplier:'+partner_name
				message_body += line_str
		'''
			

