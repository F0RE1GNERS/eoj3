def notification_processor(request):
  if request.user.is_authenticated:
    return {'notifications': request.user.notifications.unread()}
  else:
    return {}
