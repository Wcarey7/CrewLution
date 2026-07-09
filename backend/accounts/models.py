from django.db import models
from django.conf import settings
import uuid


"""
Model representing a company.
"""
class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    website = models.URLField(blank=True, default="")
    address1 = models.CharField(max_length=255, blank=True, default="")
    address2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self): # pragma: no cover
        return self.name


"""
Model representing a membership of a user in a company.
"""
class CompanyMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        DISPATCHER = "dispatcher", "Dispatcher"
        TECH = "tech", "Tech"
        VIEWER = "viewer", "Viewer"


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_memberships")
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.TECH, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('company', 'user')

    def __str__(self): # pragma: no cover
        return f"{self.company} - {self.user} ({self.role})"
