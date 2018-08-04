from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta

import margin_utility

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

	'''	
	def onchange_margin(self, cr, uid, ids, purchase_discount, amount_total):
		purchase_discount_amount = 0
		for po_id in ids:
			purchase_discount_amount = self._calculate_purchase_discount_amount(
				cr, uid, purchase_discount, amount_total)
		return {'value': {'purchase_discount_amount': purchase_discount_amount}}

		margin = self._calculate_margin(cr,uid,price_unit,valid_discount_string)
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


	