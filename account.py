from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta
import margin_utility

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class account_invoice(osv.osv):
	_inherit = 'account.invoice'

	def _cost_price_watcher(self, cr, uid, vals, context={}):
		result = super(account_invoice, self)._cost_price_watcher(cr, uid, vals, context=context)

		name = context.get('name','')
		invoice_id = context.get('invoice_id',0)
		discount_string = context.get('discount_string','0')
		discount_string_old = context.get('discount_string_old','0')
		partner_names = context.get('partner_name','')
		partner_name = partner_names if partner_names else '-'
		partner_id = context.get('partner_id','')
		invoice_type = context.get('type',0)
		product_uom = context.get('product_uom',0)
		product_id = context.get('product_id',0)
		origin = context.get('origin','')
		categ_id = context.get('categ_id','')

		buy_price_unit_nett = 0
		buy_price_unit_nett_old = 0
		sell_price_unit_nett = 0
		sell_price_unit_nett_old = 0
		margin = 0
		old_margin = 0
		percentage = 0
		old_percentage = 0
		buy_price = 1

		message_body = ''
		line_str = ''
		message_title = ''

		if invoice_type == 'in_invoice': #buy
			buy_price_unit = context.get('price_unit',0)
			buy_price_unit_nett = context.get('price_unit_nett',0)
			buy_price_unit_old = context.get('price_unit_old',0)
			buy_price_unit_nett_old = context.get('price_unit_nett_old',0)
			buy_price_type_id = context.get('price_type_id',0)
			sell_price_unit = context.get('sell_price_unit',0)
			sell_price_unit_nett = sell_price_unit
			sell_price_unit_nett_old = sell_price_unit
			
		elif invoice_type == 'out_invoice': #sell
			sell_price_unit = context.get('price_unit',0)
			sell_price_unit_nett = context.get('price_unit_nett',0)
			sell_price_unit_old = context.get('price_unit_old',0)
			sell_price_unit_nett_old = context.get('price_unit_nett_old',0)
			buy_price_unit = context.get('buy_price_unit',0)
			buy_price_unit_nett = buy_price_unit
			buy_price_unit_nett_old = buy_price_unit_nett
			
		
		buy_price = buy_price_unit_nett if buy_price_unit_nett > 0 else 1
		
		margin = sell_price_unit_nett - buy_price_unit_nett
		percentage = (margin/buy_price) * 100
		
		if (buy_price_unit_nett_old > 0):
			old_margin = sell_price_unit_nett_old - buy_price_unit_nett_old
			old_percentage = (old_margin/buy_price_unit_nett_old) * 100 
		else:
			old_margin = 0
			old_percentage = 0
			
		account_invoice_obj = self.pool.get('account.invoice')
		product_current_price_obj = self.pool.get('product.current.price')
		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		wuid = alice[0]
		now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')

		#print "sell_price_unit_nett:"+str(sell_price_unit_nett)
		#print "buy_price_unit_nett:"+str(buy_price_unit_nett)
		#print "sell_price_unit_nett_old:"+str(sell_price_unit_nett_old)
		#print "buy_price_unit_nett_old:"+str(buy_price_unit_nett_old)
		#print "margin:"+str(margin)
		#print "old_margin:"+str(old_margin)
		#print "percentage"+str(percentage)
		#print "old percentage"+str(old_percentage)

		#force create new buy price karena ada perubahan harga beli ##################################################################################################	
		if (invoice_type == 'in_invoice') and (round(buy_price_unit_nett_old) != round(buy_price_unit_nett)) :		
			
			#send message to mail system
			message="ALICE : I'm changing %s purchase price to %s" % (name,buy_price_unit_nett)	
			account_invoice_obj.message_post(cr, wuid, invoice_id, body=message)	
	
			#Create new current buy price
			product_current_price_obj.create(cr, wuid, {
			'price_type_id': buy_price_type_id,
			'product_id': product_id,
			'start_date': now,
			'partner_id': partner_id,
			'uom_id_1': product_uom,
			'price_1': buy_price_unit,
			'disc_1' : discount_string,	
			'nett_1' : buy_price_unit_nett,
			'categ_id': categ_id,
			})	

			#send notif to FCM
			message_body = ''
			line_str = ''
			message_title = 'PURCHASE INVOICE ALERT'
			message_body += 'NAME:' + str(name) +'\n'
			change_price = False

			#GANTI HARGA PRICE LIST 
			if round(buy_price_unit_old) != round(buy_price_unit):
				message_body += 'PLIST From '+ str("{:,.0f}".format(buy_price_unit_old))+' to '+str("{:,.0f}".format(buy_price_unit)) +'\n'

				#if rugi or percentage < 1 then ganti harga jual
				if (sell_price_unit_nett > 0) and (margin != 0) and ((margin < 0) or (percentage < 1)):	
					change_price = True
					message_title += ' & NEW SALE PRICE'
					if (old_percentage >= 1):
						delta = old_margin
					else:
						delta = (buy_price_unit_nett * 1 / 100) #1%

					new_sell_price_unit = margin_utility.rounding_margin(buy_price_unit_nett + delta)
					new_margin = new_sell_price_unit - buy_price_unit_nett
					new_percentage = (new_margin/buy_price) * 100

					message="ALICE : I'm changing %s sell price to %s" % (name,new_sell_price_unit)	
					account_invoice_obj.message_post(cr, wuid, invoice_id, body=message)
					
					sell_price_type_id = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])[0]
					general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')[1]

					#Create new current sell price			
					product_current_price_obj.create(cr, wuid, {
					'price_type_id': sell_price_type_id,
					'product_id': product_id,
					'start_date': now,
					'partner_id': general_customer_id,
					'uom_id_1': product_uom,
					'price_1': new_sell_price_unit,	
					})	

			#GANTI PROMO CAMPAIGN
			if discount_string_old != discount_string:
				message_body += 'DISC From '+ str(discount_string_old)+' to '+ str(discount_string) +'\n'

			#SUSUN NITIFICATION
			line_str += 'BUY NETT From '+ str("{:,.0f}".format(buy_price_unit_nett_old))+' to '+str("{:,.0f}".format(buy_price_unit_nett)) +'\n'
			line_str += 'PARTNER:'+partner_name +'\n'
			line_str += 'ORIGIN:'+origin +'\n'
			line_str += 'SELL PRICE:'+str("{:,.0f}".format(sell_price_unit_nett)) +'\n'
			line_str += 'MARGIN From:'+ str("{:,.0f}".format(old_margin))+'('+str("{:,.2f}".format(old_percentage))+'%) to '+str("{:,.0f}".format(margin))+'('+str("{:,.2f}".format(percentage))+'%)' +'\n'
			
			if change_price:
				line_str += 'NEW SELL PRICE:'+str("{:,.0f}".format(new_sell_price_unit)) +'\n'
				line_str += 'NEW MARGIN:'+str("{:,.0f}".format(new_margin))+'('+str("{:,.2f}".format(new_percentage))+'%)' +'\n'

			message_body += line_str
			context = {
				'category':'INVOICE',
				'sound_idx':PURCHASE_SOUND_IDX,
				'alert' : '!!!!!!!',
				'lines' : line_str,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		

		#cek semua bon jual, ada yg jual rugi ga (tanpa diskon)
		if (invoice_type == 'out_invoice') and (sell_price_unit > 0) and (margin != 0) and ((margin < 0) or (percentage < 1))  and (discount_string == False):		
			
			if ('BASE' not in name):
				if (old_percentage >= 1):
					delta = old_margin
				else:
					delta = (buy_price_unit_nett * 1 / 100) #1%

				new_sell_price_unit = margin_utility.rounding_margin(buy_price_unit_nett + delta)
				new_margin = new_sell_price_unit - buy_price_unit_nett
				new_percentage = (new_margin/buy_price) * 100

				message="ALICE : I'm changing %s sell price to %s" % (name,new_sell_price_unit)	
				account_invoice_obj.message_post(cr, wuid, invoice_id, body=message)
				
				sell_price_type_id = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])[0]
				general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')[1]

				#Create new current sell price			
				product_current_price_obj.create(cr, wuid, {
				'price_type_id': sell_price_type_id,
				'product_id': product_id,
				'start_date': now,
				'partner_id': general_customer_id,
				'uom_id_1': product_uom,
				'price_1': new_sell_price_unit,	
				})	

				#send notif
				message_title += 'CREATE NEW SELL PRICE FROM SELL INVOICE'
				message_body += 'NAME:' + str(name) +'\n'

				line_str += 'SELL PRICE:'+ str("{:,.0f}".format(sell_price_unit))+' to '+str("{:,.0f}".format(new_sell_price_unit)) +'\n'
				line_str += 'BUY PRICE:'+str("{:,.0f}".format(buy_price_unit_nett)) +'\n'
				line_str += 'MARGIN:'+ str("{:,.0f}".format(margin))+'('+str("{:,.2f}".format(percentage))+'%) to '+str("{:,.0f}".format(new_margin))+'('+str("{:,.2f}".format(new_percentage))+'%)' +'\n'
				line_str += 'Create by ALICE' +'\n'
				message_body += line_str
				context = {
					'category':'INVOICE',
					'sound_idx':SALES_SOUND_IDX,
					'alert' : '!!!!!!!!!!',
					'lines' : line_str,
					}

				self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
			else:
				#send notif jual tinting rugi
				message_title += 'TINTING PAINT SELL LOSS'
				message_body += 'NAME:' + str(name) +'\n'

				line_str += 'SELL PRICE:'+ str("{:,.0f}".format(sell_price_unit))+'\n'
				line_str += 'BUY PRICE:'+str("{:,.0f}".format(buy_price_unit_nett)) +'\n'
				line_str += 'MARGIN:'+ str("{:,.0f}".format(margin))+'('+str("{:,.2f}".format(percentage))+'%' +'\n'
				message_body += line_str
				context = {
					'category':'INVOICE',
					'sound_idx':SALES_SOUND_IDX,
					'alert' : '!!!!!!!!!!',
					'lines' : line_str,
					}

				self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)


		'''
		#perubahan/diskon di bon jual / SALAH JUAL --- PINDAH KE SALES SAJA
		if (invoice_type == 'out_invoice') and (discount_string != False): #ada discount line di sales
			#send notif
			message_body = ''
			line_str = ''
			message_title = 'DISCOUNT SELL'
			message_body += 'NAME:' + str(name) +'\n'
			line_str += 'NETT From '+ str("{:,.0f}".format(sell_price_unit_nett_old))+' to '+str("{:,.0f}".format(sell_price_unit_nett)) +'\n'
			line_str += 'DISC: ' +str(discount_string) +'\n'
			line_str += 'BUY PRICE:'+str("{:,.0f}".format(buy_price_unit_nett)) +'\n'
			stored = False
			if (margin <=0):
				line_str += '[!!]'
				stored = True
				
			line_str += 'MARGIN :'+str("{:,.0f}".format(margin))+'('+str("{:,.2f}".format(percentage))+'%)' +'\n'
			
			message_body += line_str
			context = {
				'category':'INVOICE',
				'sound_idx':SALES_SOUND_IDX,
				'alert' : '!!!',
				'lines' : line_str,
				'is_stored' : stored, 
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		'''
	
		#ganti harga jual di bon jual ?!?!?!? notif doank ga ada rubah apa2, 
		if (invoice_type == 'out_invoice') and (round(sell_price_unit_old) != round(sell_price_unit)) and ('BASE' not in name) and (sell_price_unit > 0):
			#send notif
			message_title = 'SELL PRICE UNIT CHANGE'
			message_body += 'NAME:' + str(name) +'\n'
			line_str += 'PRICE From '+ str("{:,.0f}".format(sell_price_unit_old))+' to '+str("{:,.0f}".format(sell_price_unit)) +'\n'
			line_str += 'BUY PRICE:'+str("{:,.0f}".format(buy_price_unit_nett)) +'\n'
			line_str += 'MARGIN From:'+ str("{:,.0f}".format(old_margin))+'('+str("{:,.2f}".format(old_percentage))+'%) to '+str("{:,.0f}".format(margin))+'('+str("{:,.2f}".format(percentage))+'%)' +'\n'
			
			message_body += line_str
			context = {
				'category':'INVOICE',
				'sound_idx':SALES_SOUND_IDX,
				'alert' : '!!!!!!!!!!!!',
				'lines' : line_str,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
			
		return result
		############################################################################################################################