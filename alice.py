from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta

import margin_utility
'''
class product_template(osv.osv):
	_inherit = 'product.template'

# FUNCTION -------------------------------------------------------------------------------------------------------------
	@api.model
	def _calculate_margin(self, price_unit, margin_string):
		try:
			valid_margin_string = margin_utility.validate_margin_string(margin_string, price_unit, self._max_margin)
		except margin_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)

		total_margin = 0
		for margin in margin_utility.calculate_Margin(valid_margin_string, price_unit, self._max_margin):
			total_margin += margin
		return total_margin

#	'''	
#	def onchange_margin(self, cr, uid, ids, purchase_discount, amount_total):
#		purchase_discount_amount = 0
#		for po_id in ids:
#			purchase_discount_amount = self._calculate_purchase_discount_amount(
#				cr, uid, purchase_discount, amount_total)
#		return {'value': {'purchase_discount_amount': purchase_discount_amount}}
#
#		margin = self._calculate_margin(cr,uid,price_unit,valid_discount_string)
#	'''
'''
# ATTRIBUTES -------------------------------------------------------------------------------------------------------------
	_max_margin = 3

	_columns = {
		'margin_string' : fields.char('Margin'),
		'margin_value': fields.float(string="Margin Value", readonly=True),
	}

class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'margin_string' : fields.char('Margin'),
		'margin_value': fields.function(_calc_margin, string="Margin Value", readonly=True)
	}


'''	
class account_invoice_line(osv.osv):
	_inherit = 'account.invoice.line'

	def _cost_price_watcher(self, cr, uid, vals, context={}):
		result = super(account_invoice_line, self)._cost_price_watcher(cr, uid, vals, context=context)
		
		invoice_type = context.get('type',0)
		product_uom = context.get('product_uom',0)
		product_id = context.get('product_id',0)
		discount_string = context.get('discount_string','0')
		discount_string_old = context.get('discount_string_old','0')
		invoice_id = context.get('invoice_id',0)
		name = context.get('name','')	#product name ?
		partner_id = context.get('partner_id','')
		sell_price_unit = context.get('sell_price_unit',0)
		buy_price_unit = context.get('buy_price_unit',0)
		buy_price_unit_nett = 0
		buy_price_unit_nett_old = 0
		sell_price_unit_nett = 0
		sell_price_unit_nett_old = 0
		margin = 0
		old_margin = 0
		percentage = 0
		old_percentage = 0

		#print "invoice_type:"+str(invoice_type)
		#print "invoice_id:"+str(invoice_id)
		if invoice_type == 'in_invoice': #buy
			buy_price_unit_nett = context.get('price_unit_nett',0)
			buy_price_unit_nett_old = context.get('price_unit_nett_old',0)
			buy_price_unit = context.get('price_unit',0)
			buy_price_unit_old = context.get('price_unit_old',0)
			buy_price_type_id = context.get('price_type_id',0)
			sell_price_unit_nett = sell_price_unit if sell_price_unit > 0 else 1
			margin = sell_price_unit_nett - buy_price_unit_nett
			old_margin = sell_price_unit_nett - buy_price_unit_nett_old
			percentage = (margin/sell_price_unit_nett) * 100
			old_percentage = (old_margin/sell_price_unit_nett) * 100 

		elif invoice_type == 'out_invoice': #sell
			sell_price_unit_nett = context.get('price_unit_nett',0)
			sell_price_unit_nett_old = context.get('price_unit_nett_old',0)
			sell_price_unit = context.get('price_unit',0)
			sell_price_unit_old = context.get('price_unit_old',0)
			sell_price_type_id = context.get('price_type_id',0)
			buy_price_unit_nett = buy_price_unit if buy_price_unit > 0 else 1
			margin = sell_price_unit_nett - buy_price_unit_nett
			old_margin = sell_price_unit_nett_old - buy_price_unit_nett
			sell_price = sell_price_unit_nett if sell_price_unit_nett > 0 else 1
			percentage = (margin/sell_price) * 100
			old_percentage = (old_margin/sell_price) * 100 
			
		account_invoice_obj = self.pool.get('account.invoice')
		product_current_price_obj = self.pool.get('product.current.price')
		now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')

		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		wuid = alice[0]

		#print "sell_price_unit_nett:"+str(sell_price_unit_nett)
		#print "buy_price_unit_nett:"+str(buy_price_unit_nett)
		#print "sell_price_unit_nett_old:"+str(sell_price_unit_nett_old)
		#print "buy_price_unit_nett_old:"+str(buy_price_unit_nett_old)
		#print "margin:"+str(margin)
		#print "old_margin:"+str(old_margin)
		#print "percentage"+str(percentage)
		#print "old percentage"+str(old_percentage)

		#force create new buy price ##################################################################################################	
		if (invoice_type == 'in_invoice') and (buy_price_unit_nett_old > 0) and (buy_price_unit > 0) and (round(buy_price_unit_nett_old) != round(buy_price_unit_nett)):
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
			})	
		
		#ga ada margin bahkan jual rugi, force new sell price
		if ((invoice_type == 'in_invoice') or (invoice_type == 'out_invoice')) and (margin <= 0) or (percentage < 1):
			#cek margin lama
			if (old_percentage >= 2):
				new_sell_price_unit = buy_price_unit_nett + old_margin 	#mesti di round menuju 500 rupiah terdekat
			else:
				new_sell_price_unit = buy_price_unit_nett + (buy_price_unit_nett * 3 / 100) #harga beli + 3%

			message="ALICE : I'm changing %s sell price to %s" % (name,new_sell_price_unit)	
			account_invoice_obj.message_post(cr, wuid, invoice_id, body=message)
			#print "new_sell_price_unit:"+str(new_sell_price_unit)
			#Create new current sell price
			sell_price_type_id = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])[0]
			general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')[1]			
			product_current_price_obj.create(cr, wuid, {
			'price_type_id': sell_price_type_id,
			'product_id': product_id,
			'start_date': now,
			'partner_id': general_customer_id,
			'uom_id_1': product_uom,
			'price_1': new_sell_price_unit,	
			})	

		return result

		''' 		
			domain = [
				('price_type_id', '=', sell_price_type_id),
				('product_id', '=', product_id),
				('start_date','<=',now),
				('partner_id','=',general_customer_id),
			]
			product_current_price_ids = product_current_price_obj.search(cr, uid, domain, order='start_date DESC', limit=1)
			
			if len(product_current_price_ids) == 0:
				#Create new price list
				product_current_price_obj.create(cr, wuid, {
				'price_type_id': price_type_id,
				'product_id': product_id,
				'start_date': now,
				'partner_id': partner_id,
				'uom_id_1': product_uom,
				'price_1': price_unit,
				'disc_1' : discount_string,	
				})	
			else:
				#Edit the price list
				product_current_price = product_current_price_obj.browse(cr, uid, product_current_price_ids)[0]
				product_current_price_obj.write(cr, wuid, [product_current_price.id], {
				'product_id': product_id,
				'price_1': price_unit,
				'disc_1' : discount_string,	
				'start_date': now,
				'partner_id' : partner_id,
			})
		'''
		############################################################################################################################

class stock_inventory(osv.osv):
	_inherit = 'stock.inventory'

	#nambahin SO inject by ALICE
	def action_done(self, cr, uid, ids, context=None):
		result = super(stock_inventory, self).action_done(cr, uid, ids, context=context)
		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		wuid = alice[0]
		stock_opname_inject = self.pool.get('stock.opname.inject')

		for inventory in self.browse(cr, uid, ids, context=context):
			for line in inventory.line_ids:
				delta_old_and_new_total_qty_line = abs(line.theoretical_qty - line.product_qty)
				old_qty = line.theoretical_qty if line.theoretical_qty > 0 else 1
				percentage = (delta_old_and_new_total_qty_line/old_qty) * 100
				# create SO inject
				if percentage > 10:
					stock_opname_inject.create(cr,wuid, {
						'location_id': inventory.location_id.id,
						'product_id': line.product_id.id,
						'priority': 1,
						'active': True,
						'domain':'not',
						'employee_id': inventory.employee_id.id,
					})
		return result