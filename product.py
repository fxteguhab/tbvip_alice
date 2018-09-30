from openerp.osv import osv, fields
from openerp import api
import margin_utility

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class product_template(osv.osv):
	_inherit = 'product.template'

	_max_discount = 3

	_columns = {
		'base_margin_string': fields.char('Expected Margin'),	
		'base_margin_amount': fields.float('Expected Margin Amount', group_operator="avg"),
		'real_margin' : fields.float('Real Margin Amount', compute="_compute_real_margin", group_operator="avg", readonly="True",store="True"),
		'real_margin_percentage' : fields.float('Real Margin %', compute="_compute_real_margin", group_operator="avg",store="True"),
		#'recommended_sale' : fields.float('Recommended Sale Price',compute="_compute_recommended_sale", store="True"),
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
	}

	_defaults = {
		'base_margin_string': '0',
		'base_margin_amount': 0,
	}

	@api.onchange('base_margin_string')
	def onchange_margin_string(self,cr,uid,ids,margin_string,context=None):
		result = {}
		buy_price_unit = 0
		total_margin = 0	
		template = self.browse(cr,uid,ids)
		uom_id = template.uom_id
		_max_discount = template._max_discount
		if len(template.product_variant_ids) > 0:
			variant = template.product_variant_ids[0]
			#ambil harga beli dari last invoice if null then ambil dari price list
			invoice_obj = self.pool.get('account.invoice.line')
			invoice_line_id = invoice_obj.search(cr, uid, [('product_id','=',variant.id),('purchase_line_id','!=',None)],order='create_date DESC', limit=1)
			if invoice_line_id:
				invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[0])
				price_subtotal = invoice_line.price_subtotal
				product_qty = invoice_line.quantity if invoice_line.quantity > 0 else 1
				nett_price = price_subtotal / product_qty
				buy_price_unit = nett_price
			else:
				price_type_id_buys = self.pool.get('price.type').search(cr,uid,[('type','=','buy'),('is_default','=',True),])
				price_type_id_buy = price_type_id_buys[0]
				price_list = self.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_buy, uom_id.id, field="nett", context=context)
				if price_list:
					buy_price_unit = price_list
			try:
				valid_margin_string = margin_utility.validate_margin_string(margin_string, buy_price_unit,_max_discount)
			except margin_utility.InvalidMarginException as exception:
				raise osv.except_orm(_('Warning!'), exception.message)
			total_margin = 0
			for margin in margin_utility.calculate_margin(valid_margin_string,buy_price_unit,_max_discount):
				total_margin += margin
			
			result.update({
				'base_margin_amount': total_margin,
			})

			if context.get('from_category',False):
				self.write(cr, uid, template.id, result)

			return {'value': result}

	@api.one
	@api.depends('list_price','standard_price')
	def _compute_real_margin(self):
		for record in self:
			cr = record.env.cr
			uid = record.env.user.id
			price_type_id_buy = record.pool.get('price.type').search(cr,uid,[('type','=','buy'),('is_default','=',True),])[0]
			price_type_id_sell = record.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])[0]
			general_customer_id = record.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')
			real_margin = 0
			percentage = 0
			buy_price_unit = 0
			sell_price_unit = 0
			if len(record.product_variant_ids) > 0:
				variant = record.product_variant_ids[0]
				
				#ambil harga dari price list
				#buy_price_unit_nett = record.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_buy, record.uom_id.id,field="nett", context=None)
				#sell_price_unit_nett = record.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_sell, record.uom_id.id, partner_id = general_customer_id[1],field="nett", context=None)

				#if record.list_price <= 1:
				#	record.list_price = sell_price_unit_nett
				#if record.standard_price <= 1:
				#	record.standard_price = buy_price_unit_nett			
				
				#ambil harga beli dari last invoice if null then ambil dari price list
				invoice_obj = self.pool.get('account.invoice.line')
				invoice_line_id = invoice_obj.search(cr, uid, [('product_id','=',variant.id),('purchase_line_id','!=',None)],order='create_date DESC', limit=1)
				if invoice_line_id:
					invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[0])
					price_subtotal = invoice_line.price_subtotal
					product_qty = invoice_line.quantity if invoice_line.quantity > 0 else 1
					nett_price = price_subtotal / product_qty
					buy_price_unit = nett_price
				else:
					buy_price_unit_nett = self.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_buy, record.uom_id.id, field="nett", context=context)
					if buy_price_unit_nett:
						buy_price_unit = price_list

				invoice_line_id = invoice_obj.search(cr, uid, [('product_id','=',variant.id),('purchase_line_id','=',None)],order='create_date DESC', limit=1)
				if invoice_line_id:
					invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[0])
					price_subtotal = invoice_line.price_subtotal
					product_qty = invoice_line.quantity if invoice_line.quantity > 0 else 1
					nett_price = price_subtotal / product_qty
					sell_price_unit = nett_price
				else:
					sell_price_unit_nett = record.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_sell, record.uom_id.id, partner_id = general_customer_id[1],field="nett", context=None)
					if sell_price_unit_nett:
						sell_price_unit = price_list

				real_margin = sell_price_unit - buy_price_unit
				#real_margin = record.list_price - record.standard_price
				buy_price = buy_price_unit if buy_price_unit > 0 else 1
				percentage = (real_margin/buy_price) * 100 
			record.real_margin = real_margin
			record.real_margin_percentage = percentage

class product_template(osv.osv):
	_inherit = 'product.product'

	_max_discount = 3
	@api.onchange('base_margin_amount')
	def onchange_margin_string(self,cr,uid,ids,margin_string,context=None):
		result = {}
		buy_price_unit = 0
		total_margin = 0
		
		product_product = self.browse(cr, uid, ids, context=context)
		variant = product_product
		uom_id = product_product.uom_id
		_max_discount = product_product._max_discount
		
		#ambil harga beli dari last invoice if null then ambil dari price list
		invoice_obj = self.pool.get('account.invoice.line')
		invoice_line_id = invoice_obj.search(cr, uid, [('product_id','=',variant.id),('purchase_line_id','!=',None)],order='create_date DESC', limit=1)
		if invoice_line_id:
			invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[0])
			price_subtotal = invoice_line.price_subtotal
			product_qty = invoice_line.quantity if invoice_line.quantity > 0 else 1
			nett_price = price_subtotal / product_qty
			buy_price_unit = nett_price
		else:
			price_type_id_buys = self.pool.get('price.type').search(cr,uid,[('type','=','buy'),('is_default','=',True),])
			price_type_id_buy = price_type_id_buys[0]
			price_list = self.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_buy, uom_id.id, field="nett", context=context)
			if price_list:
				buy_price_unit = price_list

		try:
			valid_margin_string = margin_utility.validate_margin_string(margin_string, buy_price_unit,_max_discount)
		except margin_utility.InvalidMarginException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		total_margin = 0
		for margin in margin_utility.calculate_margin(valid_margin_string,buy_price_unit,_max_discount):
			total_margin += margin
		
		result.update({
			'base_margin_amount': total_margin,
		})
		return {'value': result}



class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
		'base_margin_string': fields.char('Margin'),
	}

	def write(self, cr, uid, ids, data, context=None):
		result = super(product_category, self).write(cr, uid, ids, data, context)
		
		margin_string = data['base_margin_string'] if 'base_margin_string' in data else '0'
		sale_notification = data['sale_notification'] if 'sale_notification' in data else False
		purchase_notification = data['purchase_notification'] if 'purchase_notification' in data else False

		product_obj = self.pool.get('product.template')
		for category_id in ids:
			product_ids = product_obj.search(cr, uid, [
				('categ_id', '=', category_id),
			])
			product_obj.write(cr, uid, product_ids, {
				'base_margin_string': margin_string,
				'sale_notification': sale_notification,
				'purchase_notification': purchase_notification,
			})
			for product_id in product_ids:
				context = {
					'from_category' : True,
				}
				product_obj.onchange_margin_string(cr,uid,product_id,margin_string,context=context)
		return result

