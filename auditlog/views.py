from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.permissions import role_required

from .forms import AuditFilterForm, HostelSettingsForm
from .models import AuditEvent, HostelSettings


@role_required("Owner")
@require_http_methods(["GET", "POST"])
def settings_page(request):
    settings_obj = HostelSettings.get_solo()
    form = HostelSettingsForm(
        data=request.POST if request.method == "POST" else None,
        instance=settings_obj,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Hostel settings updated.")
        return redirect("auditlog:settings")
    return render(request, "auditlog/settings_form.html", {"form": form})


@role_required("Owner", "Manager")
def audit_history(request):
    form = AuditFilterForm(request.GET or None)
    events = AuditEvent.objects.select_related("actor", "content_type")
    if form.is_valid():
        query = form.cleaned_data.get("q")
        action = form.cleaned_data.get("action")
        actor = form.cleaned_data.get("actor")
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        if query:
            events = events.filter(
                Q(object_label__icontains=query)
                | Q(actor__username__icontains=query)
                | Q(action__icontains=query)
            )
        if action:
            events = events.filter(action=action)
        if actor:
            events = events.filter(actor=actor)
        if date_from:
            events = events.filter(timestamp__date__gte=date_from)
        if date_to:
            events = events.filter(timestamp__date__lte=date_to)

    page_obj = Paginator(events, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "auditlog/history.html",
        {"form": form, "page_obj": page_obj, "today": timezone.localdate()},
    )