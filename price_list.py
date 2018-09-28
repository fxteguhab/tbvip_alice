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
		wuid = alice[0]

		if (uid != SUPERUSER_ID) and (uid != wuid):	
			prices = self.browse(cr, uid, new_id, context=context)
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
				message_title = 'NEW SELL PRICE:'
			elif (tipe.type == 'buy'):
				message_title = 'NEW BUY PRICE:'

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

		
			
