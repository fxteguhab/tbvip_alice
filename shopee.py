
from openerp.osv import osv, fields

import urllib
import json
import requests
import hmac
import time
import hashlib
#import logging

#_logger = logging.getLogger(__name__)

HOST_URL = "https://partner.shopeemobile.com"
USER_AGENT = "Alice_python/1.0"

#const 
#SHOP_ID = 219482557
PARTNER_ID = 2001507
PARTNER_KEY = "27bc6c1f2bc3c736db69106dd04c2e5e9db443f4a55367b7c59084f0a653a8cc"

#expirated token
CODE = "accfb0dceb4b13f4158d94157dd7c86b"
access_token ="10a4033e6c1c84b14840c18c9d2ec749"
refresh_token = "f3d82405f3a3e27e61d507b27adadbb3"

#https://www.tokobesivip.com/?code=accfb0dceb4b13f4158d94157dd7c86b&shop_id=219482557


class shopee_connector(osv.osv):
	_name = 'shopee.connector'
	_description = 'Connect to SHOPEE'

	_columns = {
			'access_token': fields.char('access_token'),
			'refresh_token': fields.char('refresh_token'),
			}

	_defaults = {
		'refresh_token': "63ed51076c984cb1a5079138420889fc",
		}

	def _getStoreID(self,cr,uid):
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['SHOPEE_STORE_ID'])])
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'SHOPEE_STORE_ID':
				return int(param_data.value)
			else:
				return 0

	def _call_api(self,host, endpoint, params=None, return_response=False, method="GET", access_token='', credentials=''):
		url = "{0}{1}".format(host, endpoint)

		headers = {}
		response = None

		if (access_token != ''):
			headers['Content-Type'] = 'application/json'
		else:
			headers['Authorization'] = 'Basic ' + credentials 
			headers['Content-Length'] = '0'
			headers['user-agent'] = USER_AGENT

		if (method == 'POST'):
			response = requests.post(url, data=params, headers=headers)
		else:
			response = requests.get(url, params=params, headers=headers)

		json_response = response.json()
		#_logger.info('json_response : %s',str(json_response))
		return json_response


	def get_token_shop_level(code, partner_id, partner_key, shop_id):
		timest = int(time.time())
		body = {"code":code, "shop_id":shop_id, "partner_id": partner_id}
		path = "/api/v2/auth/token/get"	
		base_string = "%s%s%s"%(partner_id, path, timest) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		
		url = HOST_URL + path + "?partner_id=%s&timestamp=%s&sign=%s"%(partner_id,timest,sign)
		headers = { "Content-Type" : "application/json"}
		response = requests.post(url, json=body, headers=headers)
		ret = json.loads(response.content)

		access_token = ret.get("access_token")
		new_refresh_token = ret.get("refresh_token")
		print "access_token :" +str(access_token)
		print "refresh_token:" +str(new_refresh_token)
		return access_token, new_refresh_token

	def get_access_token_shop_level(self,shop_id, partner_id, partner_key, refresh_token):
		timest = int(time.time())
		path = "/api/v2/auth/access_token/get"
		body = {"shop_id":shop_id, "partner_id": partner_id,"refresh_token": refresh_token}
		base_string = "%s%s%s"%(partner_id, path, timest)
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		
		url = HOST_URL + path + "?partner_id=%s&timestamp=%s&sign=%s"%(partner_id,timest,sign) 
		headers = { "Content-Type" : "application/json"}
		response = requests.post(url, json=body, headers=headers)
		ret = json.loads(response.content)
		
		access_token = ret.get("access_token")
		new_refresh_token = ret.get("refresh_token")
		#_logger.info('access_token : %s',str(access_token))
		#_logger.info('refresh_token : %s',str(new_refresh_token))
		#print "access_token :" +str(access_token)
		#print "refresh_token:" +str(new_refresh_token)
		return access_token, new_refresh_token

	def get_shop_info(shop_id, partner_id, partner_key, access_token):		
		timest = int(time.time())
		host = "https://partner.test-stable.shopeemobile.com"
		path = "/api/v2/shop/get_shop_info"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		
		response = None
		data = {
		'partner_id' : partner_id,
		'shop_id' : shop_id,
		'access_token' : access_token,
		'timestamp' : timest,
		'sign' : sign,
		}
		response = _call_api(host,path, params=data, method="GET",access_token=access_token)
		print "SHOP INFO :" + str(response) +'\n'
		print "SHOP NAME :" + str(response["shop_name"]) +'\n'

	def get_product_info(shop_id, partner_id, partner_key, access_token, item_id):		
		timest = int(time.time())
		path = "/api/v2/product/get_item_base_info"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()

		response = None
		data = {
		'partner_id' : partner_id,
		'timestamp' : timest,
		'access_token' : access_token,
		'shop_id' : shop_id,
		'sign' : sign,

		'item_id_list' : item_id,
		}
		response = _call_api(HOST_URL,path, params=data, method="GET",access_token=access_token)
		if ('response' in response):
			print "PRODUCT INFO :"+ str(response["response"]["item_list"][0]) + '\n'
			return response

	def get_product_sku(self,shop_id, partner_id, partner_key, access_token, item_id):		
		timest = int(time.time())
		path = "/api/v2/product/get_item_base_info"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()

		response = None
		data = {
		'partner_id' : partner_id,
		'timestamp' : timest,
		'access_token' : access_token,
		'shop_id' : shop_id,
		'sign' : sign,

		'item_id_list' : item_id,
		}
		response = self._call_api(HOST_URL,path, params=data, method="GET",access_token=access_token)
		if ('response' in response):	
			#if (response['response']['item_list'][0]['item_sku']):
			return response["response"]["item_list"][0]["item_sku"]
			return item_sku
		else: return 0

	def get_product_list(shop_id, partner_id, partner_key, access_token):		
		timest = int(time.time())
		path = "/api/v2/product/get_item_list"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()

		response = None
		data = {
		'partner_id' : partner_id,
		'timestamp' : timest,
		'access_token' : access_token,
		'shop_id' : shop_id,
		'sign' : sign,

		'offset' : 0,
		'page_size':10,
		'item_status':'NORMAL',
		}
		response = _call_api(HOST_URL,path, params=data, method="GET",access_token=access_token)
		print "ITEM LIST : "+ str(response["response"]) +'\n'
		#print "ITEM COUNT : "+ str(response['response']['total_count']) +'\n'
		'''
		item_count = response['response']['total_count']
		for i in range(item_count):
			#print "ITEM IDs : "+ str(response['response']['item'][i]['item_id']) +'\n'
			if (response['response']['item'][i]['item_id']):
				sku = get_product_sku(shop_id, partner_id, partner_key, access_token,response['response']['item'][i]['item_id'])
				if (sku > 0):
					print "SKU:" + str(sku)
				else : print "ERROR, NO SKU"
		'''

	def search_product_id_by_sku(self,shop_id, partner_id, partner_key, access_token, sku):		
		timest = int(time.time())
		path = "/api/v2/product/get_item_list"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()

		response = None
		result_item_id = 0
		data = {
		'partner_id' : partner_id,
		'timestamp' : timest,
		'access_token' : access_token,
		'shop_id' : shop_id,
		'sign' : sign,

		'offset' : 0,
		'page_size':10,
		'item_status':'NORMAL',
		}

		response = self._call_api(HOST_URL,path, params=data, method="GET",access_token=access_token)
		if ('response' in response):
			item_count = response["response"]["total_count"]
			for i in range(item_count):			
					item_id = response["response"]["item"][i]["item_id"]
					item_sku = self.get_product_sku(shop_id, partner_id, partner_key, access_token,item_id)
					if ((item_sku > 0) and (item_sku == sku)): 
						result_item_id = item_id
						return result_item_id
					

	def stock_update(self, cr, uid,product_sku, new_stock):		
		timest = int(time.time())
		path = "/api/v2/product/update_stock"
		
		#GET REFRESH TOKEN
		shopee = self.browse(cr,uid,1)
		refresh_token = shopee.refresh_token
		SHOP_ID = self._getStoreID(cr,uid)
		if (SHOP_ID > 0):
			#GENERATE NEW TOKEN
			access_token, new_refresh_token = self.get_access_token_shop_level(SHOP_ID,PARTNER_ID,PARTNER_KEY,refresh_token)

			if (access_token):
				#SAVE NEW REFRESH TOKEN
				self.write(cr, uid, 1, {
					'access_token' : access_token,
					'refresh_token': new_refresh_token,
					}, context=None)
			
				#GENERATE SIGN
				base_string = "%s%s%s%s%s"%(PARTNER_ID, path, timest, access_token, SHOP_ID) 
				sign = hmac.new( PARTNER_KEY, base_string, hashlib.sha256).hexdigest()
				item_id = self.search_product_id_by_sku(SHOP_ID, PARTNER_ID, PARTNER_KEY, access_token, product_sku)
				response = None
				data = {'item_id': item_id,
						'stock_list' :[
						{
						'model_id' : 0,
						'normal_stock' : int(new_stock),
						}]
						}
				
				target = path+ "?partner_id=%s&timestamp=%s&access_token=%s&shop_id=%s&sign=%s"%(PARTNER_ID,timest,access_token,SHOP_ID,sign)
				response = self._call_api(HOST_URL,target, params=json.dumps(data), method="POST",access_token=access_token)
				
				if (response):
					return response
				else:
					return 0

	def price_update(self, cr, uid,product_sku, new_price):		
		timest = int(time.time())
		path = "/api/v2/product/update_price"
		
		#GET REFRESH TOKEN
		shopee = self.browse(cr,uid,1)
		refresh_token = shopee.refresh_token
		SHOP_ID = self._getStoreID(cr,uid)
		
		if (SHOP_ID > 0):
			#GENERATE NEW TOKEN
			access_token, new_refresh_token = self.get_access_token_shop_level(SHOP_ID,PARTNER_ID,PARTNER_KEY,refresh_token)

			if (access_token):
				#SAVE NEW REFRESH TOKEN
				self.write(cr, uid, 1, {
					'access_token' : access_token,
					'refresh_token': new_refresh_token,
					}, context=None)

				#GENERATE SIGN
				base_string = "%s%s%s%s%s"%(PARTNER_ID, path, timest, access_token, SHOP_ID) 
				sign = hmac.new( PARTNER_KEY, base_string, hashlib.sha256).hexdigest()
				item_id = self.search_product_id_by_sku(SHOP_ID, PARTNER_ID, PARTNER_KEY, access_token, product_sku)
				response = None
				data = {'item_id': item_id,
						'price_list' :[
						{
						'model_id' : 0,
						'original_price' : new_price,
						}]
						}
				
				target = path+ "?partner_id=%s&timestamp=%s&access_token=%s&shop_id=%s&sign=%s"%(PARTNER_ID,timest,access_token,SHOP_ID,sign)
				response = self._call_api(HOST_URL,target, params=json.dumps(data), method="POST",access_token=access_token)
				
				if (response):
					return response
				else:
					return 0

	def shopee_1st_call(self, cr, uid, context={}):
		self.create(cr, uid, {
						'access_token': access_token,
						'refresh_token': refresh_token,
					})

	#STANDAR MODEL SHOPPE STYLE NOT ODOO RELATED
	'''
	def update_stock(shop_id, partner_id, partner_key, access_token, item_sku, new_stock):		
		timest = int(time.time())
		path = "/api/v2/product/update_stock"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		item_id = search_product_id_by_sku(shop_id, partner_id, partner_key, access_token, item_sku)
		response = None
		data = {'item_id': item_id,
				'stock_list' :[
				{
				'model_id' : 0,
				'normal_stock' : new_stock
				}]
				}
		
		target = path+ "?partner_id=%s&timestamp=%s&access_token=%s&shop_id=%s&sign=%s"%(partner_id,timest,access_token,shop_id,sign)
		response = _call_api(HOST_URL,target, params=json.dumps(data), method="POST",access_token=access_token)
		print " update_stock : "+ str(response) +'\n'
	

	def update_price(shop_id, partner_id, partner_key, access_token, item_sku, new_price):		
		timest = int(time.time())
		path = "/api/v2/product/update_price"
		base_string = "%s%s%s%s%s"%(partner_id, path, timest, access_token, shop_id) 
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		item_id = search_product_id_by_sku(shop_id, partner_id, partner_key, access_token, item_sku)
		response = None
		data = {'item_id': item_id,
				'price_list' :[
				{
				'model_id' : 0,
				'original_price' : new_price
				}]
				}
		
		target = path+ "?partner_id=%s&timestamp=%s&access_token=%s&shop_id=%s&sign=%s"%(partner_id,timest,access_token,shop_id,sign)
		response = _call_api(HOST_URL,target, params=json.dumps(data), method="POST",access_token=access_token)
		print " update_price : "+ str(response) +'\n'


	def shopee_auth(partner_id, partner_key):
		timest = int(time.time())
		path = "/api/v2/shop/auth_partner"
		redirect_url = "https://www.tokobesivip.com/"
		base_string = "%s%s%s"%(partner_id, path, timest)
		sign = hmac.new( partner_key, base_string, hashlib.sha256).hexdigest()
		###generate api
		url = HOST_URL + path + "?partner_id=%s&redirect=%s&timestamp=%s&sign=%s"%(partner_id,redirect_url,timest,sign)
		print "AUTH URL: "+url
	'''

#link fot auth & connect app - shopee shop
#shopee_auth(PARTNER_ID, PARTNER_KEY)

#1st time access token
#access_token, refresh_token = get_token_shop_level(CODE, PARTNER_ID, PARTNER_KEY, SHOP_ID)

#2nd time access token
#access_token, refresh_token = get_access_token_shop_level(shop_id,partner_id,partner_key,refresh_token)

#get_shop_info(shop_id, partner_id, partner_key, access_token)
#get_product_list(shop_id, partner_id, partner_key, access_token)
#get_product_info(shop_id, partner_id, partner_key, access_token,100021502)


#update_stock(SHOP_ID, PARTNER_ID, PARTNER_KEY, access_token, '7615', 59) #7615 = asahi kaleng
#update_price(SHOP_ID, PARTNER_ID, PARTNER_KEY, access_token, '7615', 32000)
