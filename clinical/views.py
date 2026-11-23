from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ClinicalLogForm
from .models import ClinicalLog
from .suggestions import CASES_BY_AREA


@login_required
def home(request):
    form = ClinicalLogForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        log = form.save(commit=False)
        log.user = request.user
        log.save()
        messages.success(request, 'Clinical case logged.')
        return redirect('clinical:home')
    logs = ClinicalLog.objects.filter(user=request.user)
    return render(request, 'clinical/home.html', {
        'form': form,
        'logs': logs,
        'cases_by_area': CASES_BY_AREA,
    })
