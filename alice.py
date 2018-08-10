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
		
		price_unit_nett = context.get('price_unit_nett',0)
		price_unit_nett_old = context.get('price_unit_nett_old',0)
		price_unit = context.get('price_unit',0)
		price_unit_old = context.get('price_unit_old',0)
		product_uom = context.get('product_uom',0)
		product_id = context.get('product_id',0)
		price_type_id = context.get('price_type_id',0)
		name = context.get('name','')
		discount_string = context.get('discount_string','0')
		discount_string_old = context.get('discount_string_old','0')
		invoice_id = context.get('invoice_id',0)
		sell_price_unit = context.get('sell_price_unit',0)
		partner_id = context.get('partner_id','')

		#force create new price ##################################################################################################	
		if (price_unit_nett_old > 0) and (price_unit > 0) and (round(price_unit_nett_old) != round(price_unit_nett)):
			user_obj = self.pool.get('res.users')
			domain = [
					('name', '=', 'ALICE'),
				]
			alice = user_obj.search(cr, uid, domain)
			wuid = alice[0]

			account_invoice_obj = self.pool.get('account.invoice')
			message="ALICE : I'm changing %s purchase price" % (name)	
			account_invoice_obj.message_post(cr, uid, invoice_id, body=message)	

			product_current_price_obj = self.pool.get('product.current.price')
			now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
			domain = [
				('price_type_id', '=', price_type_id),
				('product_id', '=', product_id),
				('start_date','<=',now),
				('partner_id','=',partner_id),
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
				############################################################################################################################