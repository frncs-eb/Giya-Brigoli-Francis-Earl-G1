from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render


@login_required
def home(request):
    user = request.user
    if user.is_staff:
        users = get_user_model().objects.all()
        context = {
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'inactive_users': users.filter(is_active=False).count(),
            'admin_count': users.filter(is_staff=True).count(),
            'user_count': users.filter(is_staff=False).count(),
            'recent_users': users.order_by('-date_joined')[:5],
        }
        return render(request, 'dashboard/admin.html', context)

    return render(request, 'dashboard/user.html')
