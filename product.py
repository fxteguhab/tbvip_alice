from openerp.osv import osv, fields
from openerp import api
from datetime import datetime, timedelta
import margin_utility
import math

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class product_template(osv.osv):
	_inherit = 'product.template'

	_max_discount = 3

	def cron_calc_recommended_qty(self, cr, uid, context=None):
		all_product_ids = self.search(cr, uid, [('active', '=', True)], context=context)	
		for templates in all_product_ids:
			template = self.browse(cr,uid, templates,context=context)
			min_qty = 0
			max_qty = 0
			if len(template.product_variant_ids) > 0:
				variant = template.product_variant_ids[0]	
				if (variant):
					today = datetime.now() 
					current_year = today.year
					current_month = today.month
					data_years = 4 # mundur 4 tahun ke belakang. mungkin ini bisa diganti dengan config parameter?
					max_coeff = 2 # same: config parameter?
					sale_matrix = {}
					for year in range(current_year-data_years,current_year+1):
						sale_matrix[year] = {
							'year': year,
						# kenapa 0 s/d 14?
						# monthly_qty akan berisi qty sale bulanan di tahun itu. Index 0 adalah utk des tahun sebelumnya,
						# index 1 s/d 12 adalah untuk tahun itu, index 13 adalah untuk jan tahun depannya. 
							'monthly_qty': [0 for i in range(0,14)],
							'avg': 0,
							'weekly_avg': 0,
						}
					months1970_to = ((current_year - 1) - 1970) * 12 + 13
					months1970_from = ((current_year - data_years) - 1970) * 12
					
					#dibuang filed branch nya spy terambil data semua cabang sekaligus
					cr.execute("""
						SELECT * FROM sale_history 
						WHERE 
							product_id = %s AND months1970 BETWEEN %s AND %s
						""" % (variant.id,months1970_from,months1970_to))
				# bikin matrix berisi penjualan per bulan dan rerata bulanan dan mingguan, dipisah per tahun
					for row in cr.dictfetchall():
						year = int(row['period'][0:4])
						month = int(row['period'][4:])
						sale_matrix[year]['monthly_qty'][month] += row['sale_qty']
				# hitung rerata bulanan dan minggun
					for year in sale_matrix:
						qty_sum = 0
					# range(1,13): jumlahkan hanya monthly_qty tahun ybs. index 0 dan 13 ditinggal dulu karena itu
					# bukan punya tahun yang ini
						for month in range(1,13): qty_sum += sale_matrix[year]['monthly_qty'][month]
						active_month = 0
						for month in range(1,13):
							if ((year < current_year) or (month <= current_month)) and (sale_matrix[year]['monthly_qty'][month] > 0): active_month+=1
						if active_month == 0: active_month = 1
							
						sale_matrix[year]['avg'] = qty_sum / active_month #12.0
						sale_matrix[year]['weekly_avg'] = int(math.ceil(sale_matrix[year]['avg'] / 4.0))
				# set "carry" monthly_qty: index 0 untuk des tahun sebelumnya, index 13 utk jan tahun sesudahnya
					for year in sale_matrix:
						if (year-1) in sale_matrix:
							sale_matrix[year]['monthly_qty'][0] = sale_matrix[year-1]['monthly_qty'][12]
						if (year+1) in sale_matrix:
							sale_matrix[year]['monthly_qty'][13] = sale_matrix[year+1]['monthly_qty'][1]
				# hapus entry year yang avg nya 0, artinya di tahun itu ngga ada sale sama sekali
					delete_years = []
					for year in sale_matrix:
						if sale_matrix[year]['avg'] <= 0: delete_years.append(year)
					for year in delete_years: sale_matrix.pop(year)

				# hitung weight
					weight = 0
					weekly_qty = [] # numpang biar cuman 1 for :D
					for year in sale_matrix:
						if year == current_year: continue # skip tahun ini karena dia masih ada di matrix
						weekly_qty.append(sale_matrix[year]['weekly_avg'])
						year_avg = sale_matrix[year]['avg']
						if sale_matrix[year]['monthly_qty'][current_month-1] > year_avg: weight += 1
						if sale_matrix[year]['monthly_qty'][current_month] > year_avg: weight += 1
						if sale_matrix[year]['monthly_qty'][current_month+1] > year_avg: weight += 1

				# masukkan rumus untuk hitung kebutuhan
					jml_data = len(weekly_qty) * 3 # jumlah elemen weekly_qty diasumsikan idem tahun. 3 adalah current month +/- 1 
					min_stock = float(sum(weekly_qty)) / max(len(weekly_qty), 1)
					
					if len(weekly_qty) == 0: weekly_qty = [0]
					max_stock = max_coeff * max(weekly_qty)
					delta_stock = max_stock - min_stock
					if jml_data == 0: jml_data = 1
					stock_limit = ((float(weight)/float(jml_data)) * delta_stock) + min_stock
					rec_stock = math.ceil(stock_limit)
					
					print "min_qty : "+str(min_stock)
					print "max_qty : "+str(max_stock)
					print "rec_stock : "+str(rec_stock)
					#print "stock_limit: "+str(stock_limit)
					print "template.id: "+str(template.id)
					print "template.name: "+str(template.name)

					self.write(cr, uid, templates, {
					'min_qty': min_stock,# if template.min_qty == 0 else template.min_qty,
					'max_qty': max_stock,# if template.max_qty == 0 else template.max_qty,
					'recommended_qty': rec_stock,
					'overstock_koef' : (template.qty_available / rec_stock) if rec_stock > 0 else (template.qty_available)
					}, context=context)			

	#@api.multi
	#@api.depends('qty_available','min_qty','max_qty')
	#def _calculate_recommended_qty(self, cr, uid, ids, field_name, arg, context):
	def calculate_recommended_qty(self, cr, uid,ids,context={}):
		result = {}
		min_qty = 0
		max_qty = 0
		#product_obj = self.pool.get('product.template')
		for template in self.browse(cr, uid, ids, context):
			#cr = template.env.cr
			#uid = template.env.user.id
			if len(template.product_variant_ids) > 0:
				variant = template.product_variant_ids[0]	
				if (variant):
				# ambil data X tahun terakhir, dari januari s/d desember 
					#print "product : "+str(variant.name_template)
					#print "qty avail: "+str(variant.qty_available)
					today = datetime.now() 
					current_year = today.year
					current_month = today.month
					data_years = 4 # mundur 4 tahun ke belakang. mungkin ini bisa diganti dengan config parameter?
					max_coeff = 2 # same: config parameter?
				# persiapkan matrix sale qty
					sale_matrix = {}
					for year in range(current_year-data_years,current_year+1):
						sale_matrix[year] = {
							'year': year,
						# kenapa 0 s/d 14?
						# monthly_qty akan berisi qty sale bulanan di tahun itu. Index 0 adalah utk des tahun sebelumnya,
						# index 1 s/d 12 adalah untuk tahun itu, index 13 adalah untuk jan tahun depannya. 
							'monthly_qty': [0 for i in range(0,14)],
							'avg': 0,
							'weekly_avg': 0,
						}
				# kenapa + 13?
				# di algonya kita juga kudu liat sebulan ke depan. Misal skg desember 2018 memang betul bikin matrixnya 
				# cm 2017 ke belakang, tapi kolom "next month" nya kan jadi januari 2018
				# si 13 itulah yang memungkinkan januari 2018 ikut keambil
				# Alasan yang mirip dengan kenapa months1970_from ngga ditambah 1. Misal sekarang jan 2019 kan berarti
				# kita lihat data jan 2018 mundur ke belakang sampai misal jan 2015. nah pas jan 2015 butuh "previous 
				# month" ke des 2014.
					months1970_to = ((current_year - 1) - 1970) * 12 + 13
					months1970_from = ((current_year - data_years) - 1970) * 12
					
					#dibuang filed branch nya spy terambil data semua cabang sekaligus
					cr.execute("""
						SELECT * FROM sale_history 
						WHERE 
							product_id = %s AND months1970 BETWEEN %s AND %s
						""" % (variant.id,months1970_from,months1970_to))
					'''
					cr.execute("""
						SELECT * FROM sale_history 
						WHERE 
							branch_id = %s AND product_id = %s AND months1970 BETWEEN %s AND %s
						""" % (purchase.branch_id.id,product_id,months1970_from,months1970_to))
					'''
				# bikin matrix berisi penjualan per bulan dan rerata bulanan dan mingguan, dipisah per tahun
					for row in cr.dictfetchall():
						year = int(row['period'][0:4])
						month = int(row['period'][4:])
						sale_matrix[year]['monthly_qty'][month] += row['sale_qty']
				# hitung rerata bulanan dan minggun
					for year in sale_matrix:
						qty_sum = 0
					# range(1,13): jumlahkan hanya monthly_qty tahun ybs. index 0 dan 13 ditinggal dulu karena itu
					# bukan punya tahun yang ini
						for month in range(1,13): qty_sum += sale_matrix[year]['monthly_qty'][month]
						active_month = 0
						for month in range(1,13):
							if ((year < current_year) or (month <= current_month)) and (sale_matrix[year]['monthly_qty'][month] > 0): active_month+=1
						if active_month == 0: active_month = 1
							
						sale_matrix[year]['avg'] = qty_sum / active_month #12.0
						sale_matrix[year]['weekly_avg'] = int(math.ceil(sale_matrix[year]['avg'] / 4.0))
				# set "carry" monthly_qty: index 0 untuk des tahun sebelumnya, index 13 utk jan tahun sesudahnya
					for year in sale_matrix:
						if (year-1) in sale_matrix:
							sale_matrix[year]['monthly_qty'][0] = sale_matrix[year-1]['monthly_qty'][12]
						if (year+1) in sale_matrix:
							sale_matrix[year]['monthly_qty'][13] = sale_matrix[year+1]['monthly_qty'][1]
				# hapus entry year yang avg nya 0, artinya di tahun itu ngga ada sale sama sekali
					delete_years = []
					for year in sale_matrix:
						if sale_matrix[year]['avg'] <= 0: delete_years.append(year)
					for year in delete_years: sale_matrix.pop(year)
					#if len(sale_matrix) == 0: return 0

					#product_obj = self.pool.get('product.product')
					#products = product_obj.browse(cr, uid, product_id)[0]
					#print "product_id: %s" % products.name_template
					#print "branch_id: %s" % purchase.branch_id.id
					#for year in sale_matrix:
					#	print sale_matrix[year]

				# hitung weight
					weight = 0
					weekly_qty = [] # numpang biar cuman 1 for :D
					for year in sale_matrix:
						if year == current_year: continue # skip tahun ini karena dia masih ada di matrix
						weekly_qty.append(sale_matrix[year]['weekly_avg'])
						year_avg = sale_matrix[year]['avg']
						#print "%s: %s %s %s" % (year,sale_matrix[year]['monthly_qty'][current_month-1],sale_matrix[year]['monthly_qty'][current_month],sale_matrix[year]['monthly_qty'][current_month+1])
						if sale_matrix[year]['monthly_qty'][current_month-1] > year_avg: weight += 1
						if sale_matrix[year]['monthly_qty'][current_month] > year_avg: weight += 1
						if sale_matrix[year]['monthly_qty'][current_month+1] > year_avg: weight += 1
					#print "weight: %s" % weight
					#print "=================="

				# masukkan rumus untuk hitung kebutuhan
					jml_data = len(weekly_qty) * 3 # jumlah elemen weekly_qty diasumsikan idem tahun. 3 adalah current month +/- 1 
					min_stock = float(sum(weekly_qty)) / max(len(weekly_qty), 1)
					
					if len(weekly_qty) == 0: weekly_qty = [0]
					max_stock = max_coeff * max(weekly_qty)
					delta_stock = max_stock - min_stock
					if jml_data == 0: jml_data = 1
					stock_limit = ((float(weight)/float(jml_data)) * delta_stock) + min_stock
					rec_stock = math.ceil(stock_limit)

					#print "weekly_qty : "+str(weekly_qty)
					print "min_qty : "+str(min_stock)
					print "max_qty : "+str(max_stock)
					print "rec_stock : "+str(rec_stock)
					#print "stock_limit: "+str(stock_limit)
					print "template.id: "+str(template.id)
					print "ids:"+str(ids)
					#print "=================="

					result[template.id] = rec_stock
									
				self.write(cr, uid, template.id, {
				'min_qty': min_stock,# if template.min_qty == 0 else template.min_qty,
				'max_qty': max_stock,# if template.max_qty == 0 else template.max_qty,
				'recommended_qty': rec_stock,
				'overstock_koef' : (template.qty_available / rec_stock) if rec_stock > 0 else (template.qty_available)
				}, context=context)
				
				self.recommended_qty = rec_stock
		return result


	_columns = {
		'base_margin_string': fields.char('Expected Margin'),	
		'base_margin_amount': fields.float('Expected Margin Amount', group_operator="avg"),
		'real_margin' : fields.float('Margin', compute="_compute_real_margin", group_operator="avg", readonly="True",store="True"),
		'real_margin_percentage' : fields.float('Margin %', compute="_compute_real_margin", group_operator="avg",store="True"),
		#'recommended_sale' : fields.float('Recommended Sale Price',compute="_compute_recommended_sale", store="True"),
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
		 

		#'recommended_qty' : fields.float(calculate='_calculate_recommended_qty',string="Rec Qty", group_operator="avg", store=True),
		'recommended_qty' : fields.float("Recommended Qty"),
		'overstock_koef' : fields.float("Stock/Rec Koef"),
		'auto_so': fields.boolean('Allow SO', help="Allow to be included in auto generated stock opname"),
	}

	_defaults = {
		'base_margin_string': '0',
		'base_margin_amount': 0,
		'auto_so' : True,
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
				buy_price_unit_nett = record.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_buy, record.uom_id.id,field="nett", context=None)
				sell_price_unit_nett = record.pool.get('product.current.price').get_current(cr, uid, variant.id,price_type_id_sell, record.uom_id.id, partner_id = general_customer_id[1],field="nett", context=None)

				if record.list_price <= 1:
					record.list_price = sell_price_unit_nett
				if record.standard_price <= 1:
					record.standard_price = buy_price_unit_nett			
				
				'''
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
				'''

				#real_margin = sell_price_unit - buy_price_unit
				real_margin = record.list_price - record.standard_price
				buy_price = record.standard_price if record.standard_price > 0 else 1
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

