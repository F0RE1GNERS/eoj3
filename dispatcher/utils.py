def is_success_response(response):
  return response.get('status') == 'received'
