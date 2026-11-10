from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class HostelSettings(models.Model):
    singleton_key = models.CharField(
        max_length=16, unique=True, default="main", editable=False
    )
    hostel_name = models.CharField(max_length=160, default="Hostel Desk")
    address = models.TextField(blank=True)
    phone_numbers = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    receipt_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "hostel settings"
        verbose_name_plural = "hostel settings"

    def __str__(self):
        return self.hostel_name

    @classmethod
    def get_solo(cls):
        settings_obj, _ = cls.objects.get_or_create(singleton_key="main")
        return settings_obj

    def save(self, *args, **kwargs):
        self.singleton_key = "main"
        return super().save(*args, **kwargs)


class AuditEvent(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    action = models.CharField(max_length=80)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.CharField(max_length=64)
    affected_record = GenericForeignKey("content_type", "object_id")
    object_label = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp", "-pk")
        indexes = [
            models.Index(fields=("content_type", "object_id")),
            models.Index(fields=("timestamp",)),
        ]

    def __str__(self):
        return f"{self.action}: {self.object_label}"

    @property
    def action_label(self):
        return self.action.replace("_", " ").capitalize()