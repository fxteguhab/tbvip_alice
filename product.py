from openerp.osv import osv, fields
from openerp import api
import margin_utility

class product_template(osv.osv):
	_inherit = 'product.template'

	_max_discount = 3

	_columns = {
		'margin_amount': fields.float('Expected Margin Amount', compute="_compute_margin", group_operator="avg", readonly="True"),
		'margin_string': fields.char('Expected Margin'),
	}

	_defaults = {
		'margin_string': '0',
	}

	@api.one
	@api.depends('margin_string','standard_price')
	def _compute_margin(self):
		try:
			valid_margin_string = margin_utility.validate_margin_string(self.margin_string, self.standard_price, self._max_discount)
		except margin_utility.InvalidMarginException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		total_margin = 0
		for margin in margin_utility.calculate_margin(valid_margin_string,self.standard_price, self._max_discount):
			total_margin += margin
		self.margin_amount = total_margin
		
class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'margin_string': fields.char('Margin'),
	}

	def write(self, cr, uid, ids, data, context=None):
		result = super(product_category, self).write(cr, uid, ids, data, context)
		margin_string = data['margin_string'] if 'margin_string' in data else False

		for category_id in ids:
			product_obj = self.pool.get('product.template')
			product_ids = product_obj.search(cr, uid, [
				('categ_id', '=', category_id),
			])
			product_obj.write(cr, uid, product_ids, {
				'margin_string': margin_string,
			})

		return result