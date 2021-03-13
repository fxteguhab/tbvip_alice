from openerp.osv import osv, fields

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class tbvip_bon_book(osv.osv):
	_inherit = "tbvip.bon.book"

	def create(self, cr, uid, vals, context=None):
		result = super(tbvip_bon_book, self).create(cr, uid, vals, context)
		residual = 	self._cek_last_book_residual(cr,uid,vals['employee_id'],vals['branch_id'])
		employee_obj = self.pool.get('hr.employee')
		branch_obj = self.pool.get('tbvip.branch')
		employee_name = employee_obj.browse(cr,uid,vals['employee_id']).name
		branch_name = branch_obj.browse(cr,uid,vals['branch_id']).name
		if (residual>3):
			message_body = ''	
			message_title = 'BON ('+str(employee_name)+'-'+str(branch_name)+')::'+str(residual)+' lbr'
			alert = '!'
			for alert_lv in range(residual):
				alert += '!'

			context = {
				'category':'SALES',
				'sound_idx':PURCHASE_SOUND_IDX,
				'alert' : alert,
				'branch': branch_name,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
		return result