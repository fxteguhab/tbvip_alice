from openerp.osv import osv, fields

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class sale_order(osv.osv):
	_inherit = 'sale.order'

	def action_button_confirm(self, cr, uid, ids, context=None):
		result = super(sale_order, self).action_button_confirm(cr, uid, ids, context)
		#Get Param Value
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_sale_limit'])])
		sale_limit = 0
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_sale_limit':
				sale_limit = float(param_data.value)
		
		#for sale in self.browse(cr, uid, ids):
		sale = self.browse(cr, uid, ids)
		value = sale.amount_total
		row_count = len(sale.order_line)
		branch = sale.branch_id.name
		cust_name = sale.partner_id.display_name
		bon_number = sale.bon_number
		desc = sale.client_order_ref
		employee = sale.employee_id.name
		line_str = ''
		product_name = ''
		need_notif = False
		for line in sale.order_line:
			product_watch = ''
			extra_info = ''
			product_name = line.product_id.name_template
			sell_price_unit = line.price_unit
			sell_price_unit_nett = line.price_unit_nett
			sell_price_unit_nett_old = line.product_id.list_price
			buy_price_unit_nett = line.product_id.standard_price
			discount_string = line.discount_string

			buy_price = buy_price_unit_nett if buy_price_unit_nett > 0 else 1
			margin = sell_price_unit_nett - buy_price_unit_nett
			percentage = (margin/buy_price) * 100
			old_margin = sell_price_unit_nett_old - buy_price_unit_nett
			old_percentage = (old_margin/buy_price) * 100 

			if line.product_id.sale_notification: 
				need_notif = True
				product_watch += '[!!]'	
			
			if (round(sell_price_unit_nett_old) != round(sell_price_unit_nett)):
				need_notif = True
				product_watch += '[PRICE]'
				extra_info += ' NETT From '+ str("{:,.0f}".format(sell_price_unit_nett_old))+' to '+str("{:,.0f}".format(sell_price_unit_nett))

			if (margin <= 0):
				need_notif = True
				product_watch += '[LOSS]'

			product_name += product_watch + '('+str("{:,.0f}".format(margin))+')'
			if (extra_info != ''):
				product_name += '\n' + extra_info
			line_str += str(line.product_uos_qty)+':'+product_name + '\n'				

		if ((value >= sale_limit) or (need_notif)):
			alert = '!'
			for alert_lv in range(int(value // sale_limit )):
				alert += '!'
			message_title = 'SALE('+branch+')'+product_watch+':'
			message_body = 'CUST:'+str(cust_name)+'\n'+ employee+'('+str(bon_number)+'):'+str(row_count)+' row(s):'+str("{:,.0f}".format(value))# +'\n'+'Cust:'+cust_name
			if (desc):
					message_body = message_body +'\n'+ 'Desc:'+ str(desc)
			
			context = {
				'branch' : branch,
				'category':'SALES',
				'sound_idx':SALES_SOUND_IDX,
				'lines' : line_str,
				'alert' : alert,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result