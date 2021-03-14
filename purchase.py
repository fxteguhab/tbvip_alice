from openerp.osv import osv, fields

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class purchase_order(osv.osv):
	_inherit = 'purchase.order'

	def wkf_confirm_order(self, cr, uid, ids, context=None):
		result = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)

		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_purchase_limit'])])
		purchase_limit = 0
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_purchase_limit':
				purchase_limit = float(param_data.value)

		#for purchase in self.browse(cr, uid, ids, context=context):
		purchase = self.browse(cr, uid, ids, context=context)
		value = purchase.amount_total
		supplier_name = purchase.partner_id.display_name
		row_count = len(purchase.order_line)
		line_str = ''
		product_watch = ''
		qty_watch = ''
		user_obj = self.pool.get('res.users')
		branch_name = user_obj.browse(cr,uid,uid).branch_id.name
		
		for line in purchase.order_line:
			qty_available = line.product_id.qty_available
			product_name = line.product_id.name_template
			if line.product_id.sale_notification: 
				product_watch = '[!!]'
				product_name += product_watch
			if (line.product_id.max_qty_notification) and (line.product_qty + qty_available >= line.product_id.max_qty):
				product_watch = '[!!]'
				product_name += product_watch	
				qty_watch += '-[OVERSTOCK]'

			line_str += str(line.product_qty)+'('+str(qty_available)+')'+':'+product_name + qty_watch+'\n'
				
		if ((value >= purchase_limit) or (product_watch == '[!!]')):
			alert = '!'
			for alert_lv in range(int(value // purchase_limit )):
				alert += '!'
			message_title = 'PO'+product_watch+':'+str(supplier_name)
			message_body = str(row_count)+' row(s):'+str("{:,.0f}".format(value)) 

			context = {
				'category':'PURCHASE',
				'sound_idx':PURCHASE_SOUND_IDX,
				'lines' : line_str,
				'alert' : alert,
				'branch':branch_name,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result