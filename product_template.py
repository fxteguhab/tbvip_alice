from openerp.osv import osv, fields

SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

class product_template(osv.osv):
	_inherit = 'product.template'

# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_template, self).create(cr, uid, vals, context)
		
		name = ''
		#for product in self.browse(cr, uid, new_id, context=context):
		product = self.browse(cr, uid, new_id, context=context)
		name = product.name
		create_by = product.create_uid.name

		message_title = 'NEW ITEM CREATION'
		message_body = 'NAME:'+str(name) +'\n'+'Created by :' +str(create_by)
		context = {
				'category':'PRODUCT',
				'sound_idx':PRODUCT_SOUND_IDX,
				}
		self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return new_id