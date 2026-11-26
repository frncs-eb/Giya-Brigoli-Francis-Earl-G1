import logging
from datetime import timedelta
from django.utils import timezone
from .models import Notification
from .services import generate_for_user

logger = logging.getLogger(__name__)

def notifications_context(request):
    if not request.user.is_authenticated:
        return {'unread_count': 0, 'latest_notifications': []}
    try:
        now = timezone.now()
        last = request.session.get('notifications_last_run')
        if not last or (now - timezone.datetime.fromisoformat(last)).total_seconds() >= 300:
            generate_for_user(request.user, now)
            request.session['notifications_last_run'] = now.isoformat()
        items = Notification.objects.filter(user=request.user).order_by('-created_at')
        return {'unread_count': items.filter(is_read=False).count(), 'latest_notifications': items[:5]}
    except Exception:
        logger.exception('Could not load notification context for user %s', request.user.pk)
        return {'unread_count': 0, 'latest_notifications': []}
