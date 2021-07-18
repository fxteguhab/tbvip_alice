from openerp.osv import osv, fields

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class stock_inventory(osv.osv):
	_inherit = 'stock.inventory'

	def action_done(self, cr, uid, ids, context=None):
		result = super(stock_inventory, self).action_done(cr, uid, ids, context=context)

		user_obj = self.pool.get('res.users')
		domain = [
				('name', '=', 'ALICE'),
			]
		alice = user_obj.search(cr, uid, domain)
		wuid = alice[0]
		stock_opname_inject = self.pool.get('stock.opname.inject')
		branch_name = user_obj.browse(cr,uid,uid).branch_id.name
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['so_limit_koef'])])
		
		so_limit_koef = -1.0 #default : 75
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'so_limit_koef':
				so_limit_koef = float(param_data.value)


		row_total_qty = 0
		inventory = self.browse(cr, uid, ids, context=context)	
		for line in inventory.line_ids:
			row_total_qty += line.product_qty
			selisih =  line.product_qty - line.theoretical_qty
			delta_old_and_new_total_qty_line = abs(selisih)
			old_qty = line.theoretical_qty if line.theoretical_qty > 0 else 1
			percentage = (delta_old_and_new_total_qty_line/old_qty) * 100

			# create SO inject & notif, later create penalty
			if (so_limit_koef >= 0) and (percentage > so_limit_koef):
				#create inject
				stock_opname_inject.create(cr,wuid, {
					'location_id': inventory.location_id.id,
					'product_id': line.product_id.id,
					'priority': 2,
					'active': True,
					'domain':'not',
					'employee_id': inventory.employee_id.id,
				})
				
				#send notif
				message_title = 'SO('+str(line.product_id.name_template)+')::'+str(inventory.location_id.name)	
				message_body = 'DELTA: '+str(selisih)+'('+str(percentage)+'%)'+'\n'+'SO BY: '+str(inventory.employee_id.name_related)+'\n' + 'ADMIN: '+str(inventory.create_uid.partner_id.name)+'\n'+'OLD QTY: '+str(line.theoretical_qty)+'\n'+'NEW QTY: '+str(line.product_qty)
				alert = ''
				for alert_lv in range(int(percentage/50)):
					alert += '!'
				context = {
					'category':'PRODUCT',
					'sound_idx':PRODUCT_SOUND_IDX,
					'alert' : alert,
					'branch' : branch_name,
					}
				self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

			#update product stock on TOPED & SHOPEE
			if (line.product_id.product_tmpl_id.toped_stock_update):
				toped = self.pool.get('tokopedia.connector')
				toped.stock_update(cr,uid,line.product_id.product_tmpl_id.sku,line.product_qty)
				
				shopee = self.pool.get('shopee.connector')
				shopee.stock_update(cr,uid,line.product_id.product_tmpl_id.sku,line.product_qty)

		return result