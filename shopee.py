
from openerp.osv import osv, fields

import urllib
import json
import requests
import hmac
import time
import hashlib
import logging

_logger = logging.getLogger(__name__)

HOST_URL = "https://partner.shopeemobile.com"
USER_AGENT = "Alice_python/1.0"

#const 
#SHOP_ID = 219482557
PARTNER_ID = 2001507
PARTNER_KEY = "27bc6c1f2bc3c736db69106dd04c2e5e9db443f4a55367b7c59084f0a653a8cc"

class shopee_connector(osv.osv):
	_name = 'shopee.connector'
	_description = 'Connect to SHOPEE'

	def _getStoreID(self,cr,uid):
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['SHOPEE_STORE_ID'])])
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'SHOPEE_STORE_ID':
				return int(param_data.value)
			else: return 0

	def cal_token(redirect_url, partner_key):
		base_string = partner_key + redirect_url
		token = hashlib.sha256(base_string).hexdigest()     # note: not HMAC
		return token

	def shopee_auth1(partner_id, partner_key):
		timest = int(time.time())
		path = "/api/v1/shop/auth_partner"
		redirect_url = "https://www.tokobesivip.com/"
		token = cal_token(redirect_url,partner_key)
		url = HOST_URL + path + "?id=%s&token=%s&redirect=%s"%(partner_id,token,redirect_url)
		print "AUTH URL: "+url

	def search_product_id_by_sku(self,shop_id, sku):		
		timest = int(time.time())
		path = "/api/v1/items/get"

		page_size = 100
		next_offset = 0
		response = None
		result_item_id = 0
		more = True
		found = False

		variation_id = 0
		item_id = 0
		variation_sku = ''
		item_sku = ''

		while True:
			data = {
			'partner_id' : PARTNER_ID,
			'timestamp' : timest,
			'shopid' : shop_id,
			'pagination_offset' : next_offset,
			'pagination_entries_per_page':page_size,
			}

			base_string = HOST_URL+path + "|" + json.dumps(data)
			sign = hmac.new(PARTNER_KEY, base_string, hashlib.sha256).hexdigest()
			
			headers = {
			"Authorization":sign
			}
			
			response = requests.post(HOST_URL+path, json=data, headers=headers).json()
			if ('items' in response):
				item_count = response["total"]
				more = response["more"]
				iterate = len(response["items"])
				if (more): next_offset = next_offset + iterate

				if (iterate > 0):
					for i in range(iterate):		
						item_sku = response["items"][i]["item_sku"]
						item_id = response["items"][i]["item_id"]
						variation_id = 0
						variations = len(response["items"][i]["variations"])
						if ((item_sku > 0) and (item_sku == sku)): 
							return item_id, variation_id #found item_id
						elif (variations > 0):
							for j in range(variations):
								variation_sku = response["items"][i]["variations"][j]["variation_sku"]
								variation_id = response["items"][i]["variations"][j]["variation_id"]
								if ((variation_sku > 0) and (variation_sku == sku)): 
									return item_id, variation_id #found variaton_id

					if (next_offset + iterate == item_count): break	
				else : break
			else : break
		return 0, 0 #not found

	def stock_update(self, cr, uid, item_sku, new_stock):		
		timest = int(time.time())
		path = "/api/v1/items/update_stock"

		shop_id = self._getStoreID(cr,uid)
		if (shop_id != 0):
			item_id, variation_id = self.search_product_id_by_sku(shop_id,item_sku)
			new_stock = int(new_stock)
			if (new_stock < 0) :new_stock = 0
			if (item_id > 0):
				
				data = {
				'partner_id' : PARTNER_ID,
				'timestamp' : timest,
				'shopid' : shop_id,

				'item_id' : item_id,
				'stock': new_stock,
				}

				if (variation_id > 0):
					path = "/api/v1/items/update_variation_stock"
					data['variation_id'] = variation_id
				else:
					path = "/api/v1/items/update_stock"

				base_string = HOST_URL+path + "|" + json.dumps(data)
				sign = hmac.new(PARTNER_KEY, base_string, hashlib.sha256).hexdigest()
				
				headers = {
				"Authorization":sign
				}

				response = requests.post(HOST_URL+path, json=data, headers=headers).json()
				#_logger.info('shopee response : %s',str(response))
				_logger.info('update stock @SHOPEE success for item_sku : %s',str(item_sku))
				return response
			else: _logger.info('update stock @SHOPEE failed for item_sku : %s',str(item_sku))

	def price_update(self, cr,uid, item_sku, new_price):		
		timest = int(time.time())
		shop_id = self._getStoreID(cr,uid)
		if (shop_id != 0):
			item_id, variation_id = self.search_product_id_by_sku(shop_id,item_sku)
			#print "result item id : "+str(item_id)+" variation_id: "+str(variation_id)
			if (item_id > 0):
				
				data = {
				'partner_id' : PARTNER_ID,
				'timestamp' : timest,
				'shopid' : shop_id,

				'item_id' : item_id,
				'price': float(new_price)
				}

				if (variation_id > 0):
					path = "/api/v1/items/update_variation_price"
					data['variation_id'] = variation_id
				else:
					path = "/api/v1/items/update_price"

				base_string = HOST_URL+path + "|" + json.dumps(data)
				sign = hmac.new(PARTNER_KEY, base_string, hashlib.sha256).hexdigest()
				
				headers = {
				"Authorization":sign
				}

				response = requests.post(HOST_URL+path, json=data, headers=headers).json()
				#_logger.info('shopee response : %s',str(response))
				_logger.info('update price @SHOPEE success for item_sku : %s',str(item_sku))
				return response
			else: _logger.info('update price @SHOPEE failed for item_sku : %s',str(item_sku))