from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import PreferenceForm
from .models import Notification, NotificationPreference

@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')
    category = request.GET.get('category', '')
    unread = request.GET.get('unread') == '1'
    if category in Notification.Category.values:
        qs = qs.filter(category=category)
    else:
        category = ''
    if unread:
        qs = qs.filter(is_read=False)
    return render(request, 'notifications/list.html', {'page_obj': Paginator(qs, 20).get_page(request.GET.get('page')), 'category': category, 'unread': unread, 'categories': Notification.Category.choices})

@login_required
def open_notification(request, pk):
    item = get_object_or_404(Notification, user=request.user, pk=pk)
    if not item.is_read:
        item.is_read = True
        item.read_at = timezone.now()
        item.save(update_fields=('is_read', 'read_at'))
    return redirect(item.link or 'notifications:list')

@login_required
@require_POST
def mark_read(request, pk):
    item = get_object_or_404(Notification, user=request.user, pk=pk)
    item.is_read = not item.is_read
    item.read_at = timezone.now() if item.is_read else None
    item.save(update_fields=('is_read', 'read_at'))
    return redirect('notifications:list')

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
    return redirect('notifications:list')

@login_required
@require_POST
def delete_notification(request, pk):
    get_object_or_404(Notification, user=request.user, pk=pk).delete()
    return redirect('notifications:list')

@login_required
@require_POST
def clear_read(request):
    Notification.objects.filter(user=request.user, is_read=True).delete()
    return redirect('notifications:list')

@login_required
def preferences(request):
    instance, _ = NotificationPreference.objects.get_or_create(user=request.user)
    form = PreferenceForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('notifications:preferences')
    return render(request, 'notifications/preferences.html', {'form': form})

@login_required
def poll(request):
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')
    latest = [{'id': x.pk, 'title': x.title, 'message': x.message, 'level': x.level, 'category': x.category, 'link': x.link, 'created': x.created_at.isoformat()} for x in qs[:5]]
    return JsonResponse({'unread': qs.filter(is_read=False).count(), 'latest': latest})
