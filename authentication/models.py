from django.db import models
import uuid

# Create your models here.

class UserStatusLookup(models.Model):
    user_status_id = models.SmallAutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "user_status_lookup"
        managed = False


class User(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True)
    phone_country_code = models.IntegerField()
    password_hash = models.CharField(max_length=120)

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    profile_last_updated = models.DateTimeField(null=True)
    password_last_updated = models.DateTimeField(null=True)

    user_status = models.ForeignKey(
        UserStatusLookup,
        on_delete=models.DO_NOTHING,
        db_column="user_status",
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        managed = False 

    def __str__(self):
        return f"{self.phone}"
    

class RoleScope(models.TextChoices):
    PLATFORM = 'PLATFORM', 'Platform'
    TENANT = 'TENANT', 'Tenant'
    FLEET = 'FLEET', 'Fleet'
    SELF = 'SELF', 'Self'


class Role(models.Model):
    role_id = models.SmallAutoField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)
    role_scope = models.CharField(
        max_length=10,
        choices=RoleScope.choices
    )

    class Meta:
        db_table = "roles"
        managed = False


class UserPasswordHistory(models.Model):
    password_log_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        db_column="user_id"
    )
    password_hash = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "user_password_history"
        managed = False


class EmergencyContact(models.Model):
    emergency_contact_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        db_column="user_id"
    )
    contact_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)

    class Meta:
        db_table = "emergency_contacts"
        managed = False
        unique_together = ("user", "contact_number")

    def __str__(self):
        return f"{self.contact_name} ({self.contact_number})"


class TenantStatusLookup(models.Model):
    tenant_status_id = models.SmallAutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tenant_status_lookup"
        managed = False

    def __str__(self):
        return self.status_name


class Tenant(models.Model):
    tenant_id = models.UUIDField(primary_key=True)
    tenant_name = models.CharField(max_length=255)
    support_email = models.EmailField(null=True)
    support_phone = models.CharField(max_length=20, null=True)

    tenant_status = models.ForeignKey(
        TenantStatusLookup,
        on_delete=models.DO_NOTHING,
        db_column="tenant_status",
        null=True
    )

    verified_by_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        null=True,
        db_column="verified_by_user_id"
    )

    class Meta:
        db_table = "tenants"
        managed = False


class TenantUser(models.Model):
    tenant_user_id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
                User, 
                on_delete=models.DO_NOTHING, 
                db_column="user_id"
            )
    tenant = models.ForeignKey(
                Tenant, 
                on_delete=models.DO_NOTHING,
                db_column="tenant_id"
            )

    tenant_role = models.ForeignKey(
        Role,
        on_delete=models.DO_NOTHING,
        db_column="tenant_role"
    )

    status = models.ForeignKey(
        UserStatusLookup,
        on_delete=models.DO_NOTHING,
        db_column="status"
    )

    joined_at = models.DateTimeField()

    class Meta:
        db_table = "tenant_users"
        managed = False


class UserRole(models.Model):
    user_role_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        db_column="user_id"
    )

    tenant_id = models.UUIDField(null=True, blank=True)

    role = models.ForeignKey(
        Role,
        on_delete=models.DO_NOTHING,
        db_column="role_id"
    )

    assigned_by = models.ForeignKey(Tenant, on_delete= models.DO_NOTHING,null=True, db_column="assigned_by", blank=True)
    assigned_at = models.DateTimeField()

    class Meta:
        db_table = "user_roles"
        managed = False
        unique_together = ("user", "role", "tenant_id")


