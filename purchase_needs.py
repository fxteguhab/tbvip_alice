from datetime import datetime, timedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import math

from dateutil.relativedelta import relativedelta

# ===========================================================================================================================

class sale_history(osv.Model):
	_name = 'sale.history'
	_description = 'Stores monthly sales history to be used in needs calculation'
	
	_columns = {
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'period': fields.char('Period'), # nanti berisi misal "201812" untuk desember 2018
		'months1970': fields.integer('Months Since 1970', search=False), # sudah berapa bulan sejak januari 1970
		'sale_qty': fields.float('Sale Qty'),
	}
	
# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
		'period': lambda self, cr, uid, ctx: "%s%s" % (datetime.now().year,datetime.now().month),
	}

# CONSTRAINTS --------------------------------------------------------------------------------------------------------------

	_sql_constraints = [
		('unique_period_product_branch','UNIQUE(product_id, branch_id, period)',_('Product, branch, and period must be unique.'))
	]

# FUNCTION --------------------------------------------------------------------------------------------------------------
	
	def _get_period_data(self, month, year):
	# asumsi tidak ada data sebelum 1970
		period = "%s%02d" % (year,month)
		months1970 = (year - 1970) * 12 + month
		return period, months1970

	def compute_monthly_qty(self, cr, uid, month, year, branch_id, context={}):
	# kalau diminta calculate bulan desember 2018 maka yang sebenernya diupdate ke tabel adalah
	# november 2018 (pakai dari tanggal 1 s/d 30). Hal ini karena transaksi2 bulan ini bisa jadi 
	# masih volatile alias bisa diedit dsb. asumsinya pengeditan trx bulan lalu relatif hampir ngga
	# ada sehingga isi tabel sale_history relatif valid.
		end_time = datetime(year,month,1)
		start_time = end_time + relativedelta(months=-1)
		end_time = end_time + relativedelta(seconds=-1)
	# ambil total qty penjualan per product per uom. qty nanti harus diconvert ke uom dasar productnya
		cr.execute("""
			SELECT 
				product_id, 
				product_uom,
				SUM(product_uom_qty) as qty_total 
			FROM (
				SELECT * 
				FROM sale_order_line JOIN sale_order ON sale_order_line.order_id = sale_order.id 
				WHERE 
					branch_id = %s AND sale_order.date_order BETWEEN '%s' AND '%s'
			) AS tabel
			GROUP BY product_id, product_uom ORDER BY product_id
			""" % (branch_id,start_time.strftime("%Y-%m-%d %H:%M:%S"),end_time.strftime("%Y-%m-%d %H:%M:%S")))
		sales = cr.dictfetchall()
	# bikin cache berisi list produk. ini sekalian ngupdate cache di internal Odoo supaya di 
	# pemanggilan method2 di bawahnya tidak harus query database lagi
		product_ids = list(set([row['product_id'] for row in sales]))
		product_dict = {}
		for product in self.pool.get('product.product').browse(cr, uid, product_ids):
			product_dict[product.id] = product
	# proses setiap baris hasil query, mengconvert qty sesuai aturan product conversion utk uom ybs
		product_conversion_obj = self.pool.get('product.conversion')
		for row in sales:
			new_uom = product_conversion_obj.get_conversion_auto_uom(cr, uid, row['product_id'], row['product_uom'])
			row['qty_total'] = self.pool.get('product.uom')._compute_qty(cr, uid, new_uom.id, row['qty_total'], product_dict[row['product_id']].product_tmpl_id.uom_po_id.id)
	# hapus dan insert ulang sale history di periode ybs
		period, months1970 = self._get_period_data(month, year)
		cr.execute("""
			DELETE from sale_history 
			WHERE branch_id = %s AND period = '%s'
			""" % (branch_id, period))
		for row in sales:
			self.create(cr, uid, {
				'product_id': row['product_id'],
				'branch_id': branch_id,
				'period': period,
				'months1970': months1970,
				'sale_qty': row['qty_total']
				})

# CRON ---------------------------------------------------------------------------------------------------------------------
	
	def cron_calculate_product_qty_sold(self, cr, uid, context={}):
	# tips: cron bisa dipanggil paksa via execute model method kalau ada perubahan sale di SATU bulan lalu,
	# kalo emang sale history bulan kemaren pengen diitung ulang. WARNING: ngga bisa hitung mundur 
	# lebih dari satu bulan!
		now = datetime.now()
		#now = datetime(2018,9,5) # DEBUG! hapus sesudah selesai development
		for branch_id in self.pool.get('tbvip.branch').search(cr, uid, []):
			self.compute_monthly_qty(cr, uid, now.month, now.year, branch_id, context=context)

	def maintenance_first_fill_sale_history(self, cr, uid, context={}):
	# 20190106: jalankan method ini untuk menginisialisasi isi tabel sale history
	# setelah dijalankan, method ini mau dihapus juga gapapa
		first_year = 2018 # awal program dijalankan & data benar diinput
		last_year = 2019 # sampe tahun ini
		branch_ids = self.pool.get('tbvip.branch').search(cr, uid, [])
		cr.execute("DELETE FROM sale_history")
		for year in range(first_year,last_year+1):
			for month in range(1,13):
				for branch_id in branch_ids:
					self.compute_monthly_qty(cr, uid, month, year, branch_id, context=context)

# ===========================================================================================================================
class product_template(osv.osv):
	_inherit = 'product.template'

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	_columns = {
		'minimum_purchase_qty': fields.float('Minimum Purchase Qty'),
		'maximum_purchase_qty': fields.float('Maximum Purchase Qty'),
		'multiple_purchase_qty': fields.float('Purchase Qty Multiple'),

	}
# DEFAULTS ----------------------------------------------------------------------------------------------------------------------
	_defaults = {
		'minimum_purchase_qty': 1,
		'multiple_purchase_qty' : 1,
	}

# ===========================================================================================================================
class purchase_order_line(osv.osv):
	_inherit = 'purchase.order.line'

	_columns = {
		'wh_qty': fields.float('WH Qty'),
	}

class purchase_order(osv.osv):
	_inherit = 'purchase.order'
	
	def calculate_purchase_need(self, cr, uid, product_id, purchase, context={}):
	# ambil data X tahun terakhir, dari januari s/d desember 
		purchase_date = datetime.strptime(purchase.date_order, DEFAULT_SERVER_DATETIME_FORMAT)
		current_year = purchase_date.year
		current_month = purchase_date.month
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
			""" % (product_id,months1970_from,months1970_to))
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
			sale_matrix[year]['avg'] = qty_sum / 12.0
			sale_matrix[year]['weekly_avg'] = int(round(sale_matrix[year]['avg'] / 4.0))
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
		if len(sale_matrix) == 0: return 0

		#product_obj = self.pool.get('product.product')
		#products = product_obj.browse(cr, uid, product_id)[0]
		#print "product_id: %s" % products.name_template
		#print "branch_id: %s" % purchase.branch_id.id
		#for year in sale_matrix:
			#print sale_matrix[year]

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
		#print "weekly_qty: "+str(weekly_qty)
		if len(weekly_qty) == 0: weekly_qty = [0]
		max_stock = max_coeff * max(weekly_qty)
		delta_stock = max_stock - min_stock
		if jml_data == 0: jml_data = 1
		stock_limit = ((float(weight)/float(jml_data)) * delta_stock) + min_stock
		#print "jml_data: %s, min_stock: %s, max_stock: %s, delta_stock: %s, stock_limit: %s" % (jml_data, min_stock, max_stock, delta_stock, stock_limit)
	# ambil current_stock di lokasi cabang
		branch = self.pool.get('tbvip.branch').browse(cr, uid, purchase.branch_id.id)
		location_id = branch.default_stock_location_id.id
		cr.execute("""
		   SELECT sum(qty) as current_stock 
		   FROM stock_quant WHERE product_id=%s AND location_id=%s
		""" % (product_id, location_id))
		row = cr.dictfetchone()
		#print row
		if row:
			current_qty = row.get('current_stock', 0)
		else:
			current_qty = 0
	# tentukan berapa kebutuhan
		if current_qty < stock_limit:
			return round(stock_limit - max(current_qty,0)) # perlukan di-round?
		else:
			return 0

	def action_load_needs(self, cr, uid, ids, context={}):
		product_obj = self.pool.get('product.product')
		purchase_obj = self.pool.get('purchase.order')
		purchase = purchase_obj.browse(cr, uid, ids[0])
		#if not (purchase.branch_id and purchase.partner_id):
			#raise osv.except_osv(_('Purchase Error'),_('Please fill in branch and supplier before loading purchase needs.'))
		if not (purchase.partner_id):
			raise osv.except_osv(_('Purchase Error'),_('Please fill in supplier before loading purchase needs.'))	
	# ambil produk2 yang di-supply oleh supplier terpilih
	# list(set()) adalah untuk membuat unik entri2 di list ybs
		cr.execute("SELECT product_tmpl_id FROM product_supplierinfo WHERE name=%s" % purchase.partner_id.id)
		product_tmpl_ids = [row['product_tmpl_id'] for row in cr.dictfetchall()]
		product_tmpl_ids = list(set(product_tmpl_ids))
		product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','in',product_tmpl_ids)])
		product_ids = list(set(product_ids))
	# mulai bikin result
		new_order_lines = [[5]] # kosongkan dulu line yang sudah ada (jadi prinsipnya nimpa)
		
	#get user ALICE	
		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		wuid = alice[0]

		for product_id in product_ids:
			qty_need = self.calculate_purchase_need(cr, uid, product_id, purchase, context=context)
			products = product_obj.browse(cr, uid, product_id)[0]
			wh_qty = products.qty_available
			uom_id = products.uom_po_id.id #unit of measurement for purchase
			qty_minimum = products.minimum_purchase_qty
			qty_multiple = products.multiple_purchase_qty
			if (qty_multiple <= 0):	qty_multiple = 1
			if (qty_minimum <= 0):	qty_minimum = 1
			qty_order = 0
			#print "qty need: %s" % qty_need
			#print ""+'\n'
		# hanya tambahkan kalau ada qty yang dibutuhkan
			if qty_need >= qty_minimum:
				qty_order = (qty_need // qty_multiple) * qty_multiple
				remainder = float((qty_need % qty_multiple)) / float(qty_multiple)
				if remainder > 0.75 :
					qty_order += qty_multiple 	
			else:
				remainder = float((qty_need % qty_minimum)) / float(qty_minimum)
				if (round(remainder,1) >= 0.4 or (wh_qty <= 0)): qty_order += qty_minimum 
			
			if (qty_order > 0):
				new_line = {
					'product_id': product_id,
					'product_qty': qty_order,
					'wh_qty': wh_qty,
				}
			# jalankan onchange purchase order line untuk mengisi otomatis nilai2 yang perlu, seakan2 user 
			# yang memilih product_id di form
				oc_new_line = self.pool.get('purchase.order.line').onchange_product_id_tbvip(cr, wuid, None, \
					pricelist_id=purchase.pricelist_id.id, product_id=product_id, qty=qty_order, uom_id=uom_id,#None, 
					partner_id=purchase.partner_id.id, parent_price_type_id=purchase.price_type_id.id, 
					price_type_id=purchase.price_type_id.id)
			# hanya tambahkan line yang ada price unitnya. asumsinya, kalau ada price_unit berarti 
			# udah pernah dibeli sehingga ada stok dan kemudian (potensi) ada needs di masa selanjutnya
				if oc_new_line.get('value', None) and oc_new_line['value'].get('price_unit', 0) > 0: 
					new_line.update(oc_new_line['value'])
					new_order_lines.append([0,False,new_line])
	# timpa line baru ini ke purchase order
		purchase_obj.write(cr, wuid, [purchase.id], {
			'order_line': new_order_lines,
			})