
from openerp.osv import osv, fields

import urllib
import json
import requests
import logging

_logger = logging.getLogger(__name__)

ACCOUNT_URL = "https://accounts.tokopedia.com/"
PRODUCT_STOCK_URL = "https://fs.tokopedia.net/inventory/v1/fs/"
PRODUCT_STOCK_URL2 = "https://fs.tokopedia.net/inventory/v2/fs/"
CRED = "YTcyOWM3ZTFiYjEzNDk1ZWEyZDZmNGZjOWRmMjY4ZjI6N2M3MjM4OWZlZmIyNDJlNTgxMTgyNWYzYmI2MTc5OGU="
USER_AGENT = "Alice_python/1.0"
APP_ID = "14928"
#STORE_ID = "2328294"

class tokopedia_connector(osv.osv):
	_name = 'tokopedia.connector'
	_description = 'Connect to TOKOPEDIA'

	
	def _getStoreID(self,cr,uid):
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['TOKOPEDIA_STORE_ID'])])
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'TOKOPEDIA_STORE_ID':
				return str(param_data.value)
			else:
				return '0'

	def _call_api(self,host, endpoint, params=None, return_response=False, method="GET", access_token='', credentials=''):
		"""
		Calls toped api.
		:param endpoint: endpoint path that should end with '/', example 'discover/explore/'
		:param params: POST parameters
		:param query: GET url query parameters
		:param return_response: return the response instead of the parsed json object
		:param method
		:return:
		"""
		url = "{0}{1}".format(host, endpoint)

		headers = {}
		response = None
		#_logger.info('url : %s',str(url))
		if (access_token != ''):
			headers['Authorization'] = 'Bearer ' + access_token 
			headers['Content-Type'] = 'application/json'
		else:
			headers['Authorization'] = 'Basic ' + credentials 
			headers['Content-Length'] = '0'
			headers['user-agent'] = USER_AGENT

		#_logger.info('headers : %s',str(headers))
		if (method == 'POST'):
			try:
				response = requests.post(url, data=params, headers=headers, timeout = 10)
			except requests.exceptions.Timeout as err: 
				_logger.info('err: %s',str(err))
		else:
			try:
				response = requests.get(url, params=params, headers=headers, timeout = 10)
			except requests.exceptions.Timeout as err: 
				#print(err)
				_logger.info('err: %s',str(err))

		if (response):
			#print"url:"+response.url
			#_logger.info('response url : %s',str(response.url))
			json_response = response.json()
			#_logger.info('response : %s',str(response))
			#_logger.info('json_response : %s',str(json_response))
			return json_response
		else:
			return None

	def auth(self):		
		# coba login ke sistem TOPED	
		response = None
		data = {'grant_type': "client_credentials"}
		response = self._call_api(ACCOUNT_URL,'token', params=data, method="POST",credentials=CRED)
		if (response):
			if (response["access_token"]):
				access_token = response["access_token"]
				return response["access_token"]
			else : return None
		else: return None

	def stock_update(self, cr, uid,product_sku, new_stock):		
		STORE_ID = self._getStoreID(cr,uid)
		if (STORE_ID != '0'):
			# coba login ke sistem TOPED	
			token = self.auth()
			if (token):
				response = None
				new_stock = int(new_stock)
				if (new_stock < 0) :new_stock = 0
				
				data = [{
						'sku' : str(product_sku),
						'new_stock' : new_stock
						}]
				
				#print "token:"+str(token)
				#print"store_id:"+STORE_ID+"this"
				#print"product_sku:"+str(product_sku)+"this"
				#print"new_stock:"+str(new_stock)+"this"
				#_logger.info('store ID to update stock : %s',str(STORE_ID))
				response = self._call_api(PRODUCT_STOCK_URL,APP_ID+'/stock/update?shop_id='+STORE_ID, params=json.dumps(data), method="POST",access_token=token)
				#print "response:"+str(response)
				#_logger.info('SKU : %s',str(product_sku))
				#_logger.info('response : %s',str(response))
				if response["data"]:
					#_logger.info('tokopedia response : %s',str(response["data"]))
					_logger.info('update stock @TOKOPEDIA success for item_sku : %s',str(product_sku))
					return response["data"]["succeed_rows"]
				else:
					_logger.info('update stock @TOKOPEDIA failed for item_sku : %s',str(product_sku))
					return 0

	def price_update(self, cr, uid, product_sku, new_price):
		STORE_ID = self._getStoreID(cr,uid)
		if (STORE_ID != '0'):		
			# coba login ke sistem TOPED	
			token = self.auth()
			if (token):
				response = None
				data = [{
						'sku' : str(product_sku),
						'new_price' : int(new_price)
						}]
				response = self._call_api(PRODUCT_STOCK_URL,APP_ID+'/price/update?shop_id='+STORE_ID, params=json.dumps(data), method="POST",access_token=token)
				if response["data"]:
					#_logger.info('tokopedia response : %s',str(response["data"]))
					_logger.info('update price @TOKOPEDIA success for item_sku : %s',str(product_sku))
					return response["data"]["succeed_rows"]
				else:
					_logger.info('update price @TOKOPEDIA failed for item_sku : %s',str(product_sku))
					return 0

	def stock_update_delta(self, cr, uid, product_sku, delta, action):		
		# coba login ke sistem TOPED	
		token = self.auth()
		if (token):
			response = None
			data = [{
					'sku' : str(product_sku),
					'stock_value' : int(delta)
					}]
			
			if (action == 'INC'):
				response = self._call_api(PRODUCT_STOCK_URL2,APP_ID+'/stock/increment?shop_id='+self._getStoreID(cr,uid), params=json.dumps(data), method="POST",access_token=token)
			elif (action == 'DEC'):
				response = self._call_api(PRODUCT_STOCK_URL2,APP_ID+'/stock/decrement?shop_id='+self._getStoreID(cr,uid), params=json.dumps(data), method="POST",access_token=token)	

	def get_product_list(self):		
		#login ke sistem TOPED	
		token = self.auth()
		response = None
		data = {
		'start' : '1',
		'rows' : '10',
		'order_by' : '1',
		'shop_id' : self._getStoreID(cr,uid)
		}
		response = self._call_api(PRODUCT_STOCK_URL,APP_ID+'/product/list', params=data, method="GET",access_token=token)
		#print response

	def get_product_info(self):		
		# coba login ke sistem TOPED	
		token = self.auth()
		response = None
		data = {
		'page' : '1',
		'per_page' : '10',
		'sort' : '1',
		'sku' : '3504'
		}
		response = _call_api(PRODUCT_STOCK_URL,APP_ID+'/product/info', params=data, method="GET",access_token=token)
		#print response



'''
if (stock_update('3504', 7) > 0): print "success update stock" 
else: print "failed update stock"
if (price_update('3502', 5000) > 0): print "success update price"
else: print "failed update price"

#masih error dari tokopedia nya
#if stock_update_delta('3504', 2, 'DEC'):
#	print "success update stock delta"

#get_product_list()
'''		