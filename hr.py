from openerp.osv import fields, osv

class hr_employee(osv.osv):
	_inherit = 'hr.employee'

	_columns = {
		'allow_so' : fields.boolean('Allowed to Stock Opname'),
	}
	
	_defaults = {
		'allow_so': True,
	}