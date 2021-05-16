from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class product_current_price(osv.osv):
	_inherit = 'product.current.price'

	def create(self, cr, uid, vals, context={}):
		new_id = super(product_current_price, self).create(cr, uid, vals, context)
		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		if alice:
				wuid = alice[0]
		else:
				wuid = SUPERUSER_ID

		#user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'FEI'),
			]
		fei = user_obj.search(cr, uid, domain)
		if fei:
				fei_id = fei[0]
		else:
			fei_id = SUPERUSER_ID
		
		branch_name = user_obj.browse(cr,uid,uid).branch_id.name

		if (uid != SUPERUSER_ID) and (uid != wuid) and (uid != fei_id):	
			prices = self.browse(cr, uid, new_id, context=context)
			product_id = prices.product_id
			tipe = prices.price_type_id
			create_id = prices.create_uid
			partner_id = prices.partner_id
			price_unit_nett = prices.nett_1
			price_unit = prices.price_1
			discount_string = prices.disc_1
			product_uom = prices.uom_id_1
			partner_name = partner_id.name if partner_id else ''

			message_body = ''
			line_str = ''
			message_title = ''
			price_unit_old = 0
			discount_string_old = '0'
			price_unit_nett_old = 0
			sell_price = 0
			now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')

			if (tipe.type == 'sell'):
				message_title = 'NEW SELL PRICE LIST:'
			elif (tipe.type == 'buy'):
				message_title = 'NEW BUY PRICE LIST:'

				#get sell price
				domain = [
				('price_type_id', '=', 1),
				('product_id', '=', product_id.id),
				('start_date','<=',now),
				]	
				sell_price_ids = self.search(cr, uid, domain, order='start_date DESC', limit=1)
				sell_price_id = self.browse(cr,uid,sell_price_ids,context=None)
				sell_price = sell_price_id.nett_1

			#get prev price 	
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

			message_body += 'NAME:' + str(product_id.name_template) +'\n'
			message_body += 'PLIST From '+ str("{:,.0f}".format(price_unit_old))+' to '+str("{:,.0f}".format(price_unit)) +'\n'
			message_body += 'DISC From '+ str(discount_string_old)+' to '+ str(discount_string) +'\n'
			line_str += 'NETT From '+ str("{:,.0f}".format(price_unit_nett_old))+' to '+str("{:,.0f}".format(price_unit_nett)) +'\n'
			line_str += 'PARTNER:'+ partner_name +'\n'
			line_str += 'Created by :' +str(create_id.name)
			message_body += line_str

			context = {
					'category':'PRODUCT',
					'sound_idx':PRODUCT_SOUND_IDX,
					'alert' : '!!!!!!!',
					'lines' : line_str,
					'branch' : branch_name,
					'product_id':product_id.id,
					'new_price': sell_price,
					}
			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		
		#update price di TOPED
		prices = self.browse(cr, uid, new_id, context=context)
		product_id = prices.product_id
		tipe = prices.price_type_id
		if ((product_id.product_tmpl_id.toped_price_update) and (tipe == product_id.product_tmpl_id.toped_price_type)):		
			#if ((tipe.type == 'sell') and (tipe.is_default)):
			toped = self.pool.get('tokopedia.connector')
			toped.price_update(cr,uid,product_id.product_tmpl_id.sku,prices.nett_1)
	
		return new_id

		
			
