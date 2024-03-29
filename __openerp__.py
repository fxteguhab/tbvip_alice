{
	'name': 'TB VIP ALICE',
	'version': '0.1',
	'category': 'Sales Management',
	'description': """
		Custom AI implementation for Toko Besi VIP Bandung
	""",
	'author': 'FX and Associates',
	'maintainer': 'FX and Associates',
	'website': '',
	'depends': [
		"tbvip",
	],	
	'sequence': 200,
	'data': [
	'menu/stock_opname_menu.xml',
	'views/notification_view.xml',
	'views/stock_opname_view.xml',
	'views/product_view.xml',
	'views/purchase_needs_view.xml',
	'views/hr_view.xml',
	'cron/tbvip_alice_cron.xml',
	],
	'installable': True,
	'auto_install': False,
	'qweb': [
	]
}
