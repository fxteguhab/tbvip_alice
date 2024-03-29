from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
#from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from datetime import datetime, timedelta

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class stock_opname_memory(osv.osv_memory):
	_inherit = 'stock.opname.memory'
	
	_columns = {
		'allow_so': fields.related('employee_id', 'allow_so', type="boolean", string="allow_so"),
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}

	_defaults = {
		'location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_stock_location_id.id,
		'branch_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.id,
	}
	
	def action_generate_stock_opname(self, cr, uid, ids, context=None):
	# karena di tbvip location stock opname per barang pasti idem Inventoried Location,
	# maka di form field/kolom location di Inventories (stock_opname_memory_line.location_id) dihide
	# akhirnya kita harus ngisi satu2 field tsb berdasarkan stock_opname_memory.location_id
			memory_line_obj = self.pool.get('stock.opname.memory.line')
			memory = self.browse(cr, uid, ids)
			is_override = context.get('is_override',False)
			if is_override or memory.allow_so:
				for line in memory.line_ids:
					memory_line_obj.write(cr, uid, [line.id], {
						'location_id': memory.location_id.id,
						})
				return super(stock_opname_memory, self).action_generate_stock_opname(cr, uid, ids, context=context)
			else:
				raise osv.except_orm(_('Employee Stock Opname Block'),
				_('Employee : %s cannot do Stock Opname at this moment' % (memory.employee_id.name_related)))

	def _generate_stock_opname_products(self, cr, uid, location,context={}):
		return self.algoritma_generate_so_products3(cr, uid, location,context=context)

	'''
	def algoritma_generate_so_products1(self, cr, uid, location,context={}):
		today = datetime.now()
		last_week = today - timedelta(days=7)
		last_month = today - timedelta(days=100)
		cr.execute("""
			SELECT
				product_id, last_sale_date
			FROM (
				SELECT
					DISTINCT ON (product_id)
					so_line.product_id, so.date_order as last_sale_date
				FROM
					sale_order_line so_line LEFT JOIN sale_order so
					ON so.id = so_line.order_id
				WHERE
					so_line.product_id IN (
						SELECT
							ptemplate.id
						FROM
							product_template as ptemplate JOIN product_product as pproduct
							ON ptemplate.id = pproduct.product_tmpl_id
						WHERE
							type = 'product' AND
							(latest_inventory_adjustment_date is NULL OR latest_inventory_adjustment_date < \'{}\')
					)
				ORDER BY
					product_id ASC, last_sale_date DESC
			) AS product_last_sale_date_ordered
			WHERE
				last_sale_date < \'{}\' AND 
				last_sale_date > \'{}\'
			ORDER BY
				last_sale_date DESC
			""".format(last_week, today, last_month)
		)
		stock_opname_products = []
		for row in cr.dictfetchall():
			stock_opname_products.append({'product_id': row['product_id']})
		return stock_opname_products
	
	def algoritma_generate_so_products2(self, cr, uid, location,context={}):
		today = datetime.now()
		last_week = today - timedelta(days=7)
		last_month = today - timedelta(days=30)	
		cr.execute("""
			SELECT
				product_id, last_sale_date
			FROM (
				SELECT
					DISTINCT ON (product_id)
					so_line.product_id, so.date_order as last_sale_date
				FROM
					sale_order_line so_line LEFT JOIN sale_order so
					ON so.id = so_line.order_id
				WHERE
					so_line.product_id NOT IN (
						SELECT
							si_line.product_id
						FROM
							stock_inventory_line as si_line
						WHERE	
							location_id = \'{}\' AND
							(write_date is NULL OR write_date > \'{}\')
					) AND so_line.stock_location_id = \'{}\'
				ORDER BY
					product_id ASC, last_sale_date DESC
			) AS product_last_sale_date_ordered
			WHERE
				last_sale_date < \'{}\' AND 
				last_sale_date > \'{}\'
			ORDER BY
				last_sale_date DESC
			""".format(location, last_week, location, today, last_month)
		)
		stock_opname_products = []
		for row in cr.dictfetchall():
			stock_opname_products.append({'product_id': row['product_id']})
		
		return stock_opname_products

	'''
	def algoritma_generate_so_products3(self, cr, uid, location,context={}):
		today = datetime.now()
		last_week = today - timedelta(days=7)
		last_month = today - timedelta(days=30)	
		cr.execute("""				
			SELECT
				product_id, last_sale_date
			FROM (
				SELECT DISTINCT ON (product_id)
				so_line.product_id, so_line.write_date as last_sale_date
				FROM
					sale_order_line so_line
				WHERE
					so_line.product_id NOT IN (
						SELECT
							si_line.product_id
						FROM
							stock_inventory_line as si_line
						WHERE	
							location_id = \'{}\' AND
							(write_date is NULL OR write_date > \'{}\')
					) AND so_line.stock_location_id = \'{}\'
					  AND so_line.write_date < \'{}\' 
					  AND so_line.write_date > \'{}\'	
				) AS product_last_sale_date,
				product_product product_product,
				product_template product_template
				WHERE 
				product_id = product_product.id AND
				product_product.product_tmpl_id = product_template.id AND
				product_template.auto_so = 't'
				ORDER BY
					last_sale_date ASC
			""".format(location, last_week, location, today, last_month)
		)
		stock_opname_products = []
		for row in cr.dictfetchall():
			stock_opname_products.append({'product_id': row['product_id']})

		return stock_opname_products

	
	#def algoritma_generate_so_products_all_delima(self, cr, uid, location,context={}):		
	#	cr.execute("""				
	#		SELECT DISTINCT
	#			product_id
	#		FROM stock_quant
	#			WHERE 
	#			location_id = '64'
	#		"""
	#	)
	#	stock_opname_products = []
	#	for row in cr.dictfetchall():
	#		stock_opname_products.append({'product_id': row['product_id']})
	#
	#	return stock_opname_products	

	def action_load_inventories(self, cr, uid, ids, context=None):
		stock_opname_memory_line_obj = self.pool.get('stock.opname.memory.line')
		#for so_memory in self.browse(cr, uid, ids):
		so_memory = self.browse(cr, uid, ids)
		stock_opname_memory_line_obj.unlink(cr, uid, so_memory.line_ids.ids, context=context)
		new_line_ids = []
		onchange_result = self.onchange_location_and_employee(cr, uid, ids,
			so_memory.location_id.id, so_memory.rule_id.id, so_memory.employee_id.id, context=context)
		if onchange_result['value']['line_ids']:
			for line in onchange_result['value']['line_ids']:
				new_line_ids.append((0, False, {
					'inject_id': line['inject_id'] if line.get('inject_id', False) else 0,
					'location_id': line['location_id'],
					'product_id': line['product_id'].id,
				}))
			self.write(cr, uid, so_memory.id, {
				'line_ids': new_line_ids,
			})

		return {
			'context': context,
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.opname.memory',
			'res_id': so_memory.id,
			'view_id': False,
			'type': 'ir.actions.act_window',
			'target': 'new',
		}	
	
class stock_opname_memory_line(osv.osv_memory):
	_inherit = "stock.opname.memory.line"
	
	_columns = {
		'sublocation': fields.text('Sublocations'),
		'location_id': fields.many2one('stock.location', 'Location', required=False),
	}
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		context = {} if context is None else None
		product_obj = self.pool.get('product.product')
		result = ''
		#for product in product_obj.browse(cr, uid, [product_id], context):
		product = product_obj.browse(cr, uid, [product_id], context)
		for product_sublocation_id in product.product_sublocation_ids:
			branch_name = product_sublocation_id.branch_id.name if product_sublocation_id.branch_id.name else ''
			sublocation_full_name = product_sublocation_id.sublocation_id.full_name if product_sublocation_id.sublocation_id.full_name else ''
			result += branch_name + ' / ' + sublocation_full_name + '\r\n'
		return {'value': {'sublocation': result}}
