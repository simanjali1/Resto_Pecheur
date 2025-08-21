# reservations/admin.py 
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from .models import RestaurantInfo, Reservation, TimeSlot, SpecialDate, Notification, get_restaurant_info

# IMPORTANT: Clear any existing registrations to prevent duplicates
from django.contrib.admin.sites import site

# Unregister all models first to avoid conflicts
for model in [RestaurantInfo, Reservation, TimeSlot, SpecialDate, Notification, User]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass

# ===== SIMPLE ROLE-BASED USER ADMIN =====

class SimpleRoleCreateForm(forms.ModelForm):
    """Form for creating new users with role selection"""
    
    ROLE_CHOICES = [
        ('', '-- Sélectionner un rôle --'),
        ('manager', '👑 Manager Restaurant (Accès complet)'),
        ('staff', '👥 Personnel (Accès limité aux réservations)'),
    ]
    
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Votre mot de passe doit contenir au moins 8 caractères.",
        min_length=8
    )
    password2 = forms.CharField(
        label='Confirmation du mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Entrez le même mot de passe que précédemment, pour vérification."
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'font-size: 16px; padding: 10px; background: #f8f9fa; border: 2px solid #007bff; border-radius: 8px;'
        }),
        help_text="""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #f0f7ff 100%); padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4 style="color: #1976d2; margin-top: 0;">🎯 Choisissez le rôle :</h4>
            <p><strong>👑 Manager :</strong> Accès complet (propriétaire/gérant)</p>
            <p><strong>👥 Personnel :</strong> Réservations seulement (serveur/hôte)</p>
        </div>
        """
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field in self.fields:
            if field not in ['role']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return password2
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur existe déjà.")
        return username
    
    def save(self, commit=True):
        # Create user but don't save to database yet
        user = super().save(commit=False)
        
        # CRITICAL: Hash the password properly
        password = self.cleaned_data["password1"]
        user.set_password(password)  # This hashes the password
        
        if commit:
            user.save()
            self.save_m2m()  # Save many-to-many relationships
            
            # Clear existing groups first
            user.groups.clear()
            
            # Assign role based on selection
            role = self.cleaned_data.get('role')
            
            if role == 'manager':
                user.is_staff = True
                user.is_superuser = False
                from django.contrib.auth.models import Group
                manager_group, created = Group.objects.get_or_create(name='Restaurant Manager')
                user.groups.add(manager_group)
                self._assign_manager_permissions(user)
                print(f"✅ Created MANAGER user: {user.username}")
                
            elif role == 'staff':
                user.is_staff = True
                user.is_superuser = False
                from django.contrib.auth.models import Group
                staff_group, created = Group.objects.get_or_create(name='Restaurant Staff')
                user.groups.add(staff_group)
                self._assign_staff_permissions(user)
                print(f"✅ Created STAFF user: {user.username}")
            
            else:
                # No role selected - regular user (no admin access)
                user.is_staff = False
                user.is_superuser = False
                user.user_permissions.clear()
                print(f"✅ Created REGULAR user: {user.username}")
            
            user.save()  # Save again after role assignment
        
        return user
    
    def _assign_manager_permissions(self, user):
        """Assign all restaurant permissions to manager"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        try:
            restaurant_models = ['reservation', 'restaurantinfo', 'specialdate', 'timeslot', 'notification']
            manager_permissions = []
            
            for model_name in restaurant_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    model_permissions = Permission.objects.filter(content_type=content_type)
                    manager_permissions.extend(model_permissions)
                except ContentType.DoesNotExist:
                    continue
            
            user.user_permissions.set(manager_permissions)
            print(f"✅ Assigned {len(manager_permissions)} manager permissions to {user.username}")
        except Exception as e:
            print(f"❌ Error assigning manager permissions: {e}")
    
    def _assign_staff_permissions(self, user):
        """Assign limited permissions to staff"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        try:
            staff_permissions = []
            
            # Reservation permissions (view and change only)
            reservation_ct = ContentType.objects.get(app_label='reservations', model='reservation')
            staff_permissions.extend(Permission.objects.filter(
                content_type=reservation_ct,
                codename__in=['view_reservation', 'change_reservation']
            ))
            
            # View-only permissions for other models
            other_models = ['restaurantinfo', 'specialdate', 'timeslot', 'notification']
            for model_name in other_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    staff_permissions.extend(Permission.objects.filter(
                        content_type=content_type,
                        codename__startswith='view_'
                    ))
                except ContentType.DoesNotExist:
                    continue
            
            user.user_permissions.set(staff_permissions)
            print(f"✅ Assigned {len(staff_permissions)} staff permissions to {user.username}")
        except Exception as e:
            print(f"❌ Error assigning staff permissions: {e}")

class SimpleRoleForm(UserChangeForm):
    """Simple form with just Manager/Staff choice"""
    
    ROLE_CHOICES = [
        ('', '-- Sélectionner un rôle --'),
        ('manager', '👑 Manager Restaurant (Accès complet)'),
        ('staff', '👥 Personnel (Accès limité aux réservations)'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'font-size: 16px; padding: 10px; background: #f8f9fa; border: 2px solid #007bff; border-radius: 8px;'
        }),
        help_text="""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #f0f7ff 100%); padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #2196f3;">
            <h4 style="color: #1976d2; margin-top: 0;">🎯 Changer le rôle utilisateur:</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;">
                    <h5 style="color: #cb5103; margin-top: 0;">👑 Manager Restaurant</h5>
                    <ul style="color: #424242; margin: 10px 0; font-size: 14px;">
                        <li>✅ Toutes les réservations</li>
                        <li>✅ Configuration restaurant</li>
                        <li>✅ Dates spéciales</li>
                        <li>✅ Créneaux horaires</li>
                        <li>✅ Notifications</li>
                        <li>✅ Statistiques complètes</li>
                    </ul>
                    <small style="color: #666; font-style: italic;">Pour propriétaire/gérant</small>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;">
                    <h5 style="color: #333354; margin-top: 0;">👥 Personnel</h5>
                    <ul style="color: #424242; margin: 10px 0; font-size: 14px;">
                        <li>✅ Voir les réservations</li>
                        <li>✅ Modifier les réservations</li>
                        <li>✅ Voir les notifications</li>
                        <li>❌ Configuration (lecture seule)</li>
                        <li>❌ Dates spéciales (lecture seule)</li>
                        <li>❌ Statistiques avancées</li>
                    </ul>
                    <small style="color: #666; font-style: italic;">Pour serveurs/hôtes</small>
                </div>
            </div>
            <p style="color: #1976d2; font-weight: bold; text-align: center; margin-bottom: 0;">
                💡 Les permissions sont automatiquement assignées selon le rôle choisi
            </p>
        </div>
        """
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove password field for simpler interface
        if 'password' in self.fields:
            del self.fields['password']
        
        # Set current role based on user's groups
        if self.instance and self.instance.pk:
            if self.instance.groups.filter(name='Restaurant Manager').exists():
                self.fields['role'].initial = 'manager'
            elif self.instance.groups.filter(name__in=['Restaurant Staff', 'Host/Receptionist', 'Server/Waiter']).exists():
                self.fields['role'].initial = 'staff'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Clear existing groups
            user.groups.clear()
            
            # Assign role based on selection
            role = self.cleaned_data.get('role')
            
            if role == 'manager':
                # Make them manager with full access
                user.is_staff = True
                user.is_superuser = False  # Keep it safe - only owner should be superuser
                
                # Add to manager group (create if doesn't exist)
                from django.contrib.auth.models import Group
                manager_group, created = Group.objects.get_or_create(name='Restaurant Manager')
                user.groups.add(manager_group)
                
                # Assign manager permissions
                self._assign_manager_permissions(user)
                
            elif role == 'staff':
                # Make them staff with limited access
                user.is_staff = True
                user.is_superuser = False
                
                # Add to staff group (create if doesn't exist)
                from django.contrib.auth.models import Group
                staff_group, created = Group.objects.get_or_create(name='Restaurant Staff')
                user.groups.add(staff_group)
                
                # Assign staff permissions
                self._assign_staff_permissions(user)
            
            else:
                # No role selected - remove admin access
                user.is_staff = False
                user.is_superuser = False
                user.user_permissions.clear()
            
            user.save()
        
        return user
    
    def _assign_manager_permissions(self, user):
        """Assign all restaurant permissions to manager"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        manager_permissions = []
        
        try:
            # Get all permissions for restaurant models
            restaurant_models = ['reservation', 'restaurantinfo', 'specialdate', 'timeslot', 'notification']
            
            for model_name in restaurant_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    model_permissions = Permission.objects.filter(content_type=content_type)
                    manager_permissions.extend(model_permissions)
                except ContentType.DoesNotExist:
                    continue
            
            # Assign all permissions
            user.user_permissions.set(manager_permissions)
            
        except Exception as e:
            print(f"Error assigning manager permissions: {e}")
    
    def _assign_staff_permissions(self, user):
        """Assign limited permissions to staff"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        staff_permissions = []
        
        try:
            # Reservation permissions (view and change only)
            reservation_ct = ContentType.objects.get(app_label='reservations', model='reservation')
            staff_permissions.extend(Permission.objects.filter(
                content_type=reservation_ct,
                codename__in=['view_reservation', 'change_reservation']
            ))
            
            # View-only permissions for other models
            other_models = ['restaurantinfo', 'specialdate', 'timeslot', 'notification']
            for model_name in other_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    staff_permissions.extend(Permission.objects.filter(
                        content_type=content_type,
                        codename__startswith='view_'
                    ))
                except ContentType.DoesNotExist:
                    continue
            
            # Assign limited permissions
            user.user_permissions.set(staff_permissions)
            
        except Exception as e:
            print(f"Error assigning staff permissions: {e}")

@admin.register(User)
class SimpleUserAdmin(admin.ModelAdmin):
    """Simplified User admin with Manager/Staff roles - COMPLETELY CUSTOM"""
    
    # Use our custom forms
    form = SimpleRoleForm
    add_form = SimpleRoleCreateForm
    
    # List display
    list_display = ('username', 'get_full_name', 'email', 'get_role', 'is_active', 'last_login')
    list_filter = ('is_active', 'is_staff', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Fieldsets for editing existing users
    fieldsets = (
        ('👤 Informations Utilisateur', {
            'fields': ('username', 'first_name', 'last_name', 'email'),
            'description': 'Informations de base de l\'utilisateur'
        }),
        ('🔐 Sécurité', {
            'fields': ('is_active', 'last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
        ('🎯 Rôle Restaurant', {
            'fields': ('role_display', 'role'),
            'description': 'Gérer le rôle de cet utilisateur'
        }),
        ('👑 Propriétaire Uniquement', {
            'fields': ('is_superuser',),
            'classes': ('collapse',),
            'description': '⚠️ Réservé au propriétaire du restaurant uniquement'
        }),
    )
    
    # Fieldsets for adding new users
    add_fieldsets = (
        ('🆕 Créer un Utilisateur', {
            'fields': ('username', 'password1', 'password2'),
            'description': 'Informations de connexion'
        }),
        ('👤 Informations Personnelles', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('🎯 Rôle Restaurant', {
            'fields': ('is_active', 'role'),
            'description': 'Définir le rôle et les permissions'
        }),
    )
    
    readonly_fields = ('role_display', 'last_login', 'date_joined')
    
    def get_form(self, request, obj=None, **kwargs):
        """Use different forms for add and change"""
        if obj is None:  # Adding
            kwargs['form'] = self.add_form
        else:  # Changing
            kwargs['form'] = self.form
        return super().get_form(request, obj, **kwargs)
    
    def get_fieldsets(self, request, obj=None):
        """Use different fieldsets for add and change"""
        if obj is None:  # Adding
            fieldsets = self.add_fieldsets
        else:  # Changing
            fieldsets = self.fieldsets
            
        # Hide superuser field for non-superusers
        if not request.user.is_superuser:
            fieldsets = [fs for fs in fieldsets if 'is_superuser' not in str(fs)]
        
        return fieldsets
    
    def role_display(self, obj):
        """Display current role of user"""
        if obj.is_superuser:
            return format_html('<span style="color: #cb5103; font-weight: bold; font-size: 16px;">👑 Propriétaire (Accès complet)</span>')
        elif obj.groups.filter(name='Restaurant Manager').exists():
            return format_html('''
                <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe8cc 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #cb5103;">
                    <h4 style="color: #cb5103; margin: 0;">👑 Manager Restaurant</h4>
                    <p style="margin: 5px 0; color: #555;">✅ Accès complet à toutes les fonctionnalités</p>
                </div>
            ''')
        elif obj.groups.filter(name__in=['Restaurant Staff', 'Host/Receptionist', 'Server/Waiter']).exists():
            return format_html('''
                <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e8d5ea 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #333354;">
                    <h4 style="color: #333354; margin: 0;">👥 Personnel Restaurant</h4>
                    <p style="margin: 5px 0; color: #555;">🔒 Accès limité aux réservations uniquement</p>
                </div>
            ''')
        elif obj.is_staff:
            return format_html('<span style="color: #6c757d; font-size: 16px;">⚙️ Admin système</span>')
        else:
            return format_html('<span style="color: #dc3545; font-size: 16px;">❌ Aucun rôle assigné</span>')
    role_display.short_description = 'Rôle Actuel'
    
    def get_role(self, obj):
        """Display user role in list"""
        if obj.is_superuser:
            return format_html('<span style="color: #cb5103; font-weight: bold;">👑 Propriétaire</span>')
        elif obj.groups.filter(name='Restaurant Manager').exists():
            return format_html('<span style="color: #cb5103; font-weight: bold;">👑 Manager</span>')
        elif obj.groups.filter(name__in=['Restaurant Staff', 'Host/Receptionist', 'Server/Waiter']).exists():
            return format_html('<span style="color: #333354; font-weight: bold;">👥 Personnel</span>')
        elif obj.is_staff:
            return format_html('<span style="color: #6c757d;">⚙️ Admin</span>')
        else:
            return format_html('<span style="color: #dc3545;">❌ Aucun rôle</span>')
    get_role.short_description = 'Rôle'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of superuser accounts"""
        if obj and obj.is_superuser:
            return request.user.is_superuser
        return super().has_delete_permission(request, obj)
    
    def get_urls(self):
        """Add custom URLs for user profile access"""
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('profile/', self.admin_site.admin_view(self.user_profile_view), name='user_profile'),
        ]
        return custom_urls + urls
    
    def user_profile_view(self, request):
        """Redirect to current user's profile edit page"""
        from django.shortcuts import redirect
        user_id = request.user.id
        return redirect(f'/admin/auth/user/{user_id}/change/')
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist to handle profile access"""
        # If user is not superuser and tries to access user list, redirect to their profile
        if not request.user.is_superuser and 'profile' not in request.path:
            # Check if user is trying to access their own profile
            if request.user.groups.filter(name='Restaurant Staff').exists():
                # Staff can only see their own profile
                return redirect(f'/admin/auth/user/{request.user.id}/change/')
        
        return super().changelist_view(request, extra_context)
    
    def has_view_permission(self, request, obj=None):
        """Control who can view what - JAZZMIN COMPATIBLE"""
        if request.user.is_superuser:
            return True
        
        # Managers can see all users
        if request.user.groups.filter(name='Restaurant Manager').exists():
            return True
        
        # Staff can only see their own profile
        if obj and obj == request.user:
            return True
        elif obj is None:
            # Allow access to changelist but will be filtered
            return request.user.is_staff
            
        return False
    
    def has_change_permission(self, request, obj=None):
        """Control who can change what - JAZZMIN COMPATIBLE"""
        if request.user.is_superuser:
            return True
        
        # Managers can change all users (except superusers)
        if request.user.groups.filter(name='Restaurant Manager').exists():
            if obj and obj.is_superuser and not request.user.is_superuser:
                return False
            return True
        
        # Staff can only change their own profile (limited fields)
        if obj and obj == request.user:
            return True
            
        return False
    
    def get_queryset(self, request):
        """Filter queryset based on user permissions - JAZZMIN COMPATIBLE"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Managers can see all users
        if request.user.groups.filter(name='Restaurant Manager').exists():
            return qs
        
        # Staff can only see themselves
        if request.user.groups.filter(name='Restaurant Staff').exists():
            return qs.filter(id=request.user.id)
        
        # Default: show nothing for users without proper roles
        return qs.none()
    
    def get_fieldsets(self, request, obj=None):
        """Different fieldsets based on permissions - JAZZMIN COMPATIBLE"""
        # If staff user editing their own profile
        if (obj and obj == request.user and 
            not request.user.is_superuser and
            request.user.groups.filter(name='Restaurant Staff').exists()):
            
            return (
                ('👤 Mon Profil', {
                    'fields': ('username', 'first_name', 'last_name', 'email'),
                    'description': 'Vous pouvez modifier vos informations personnelles'
                }),
                ('🔐 Sécurité', {
                    'fields': ('last_login', 'date_joined'),
                    'classes': ('collapse',),
                    'description': 'Informations de connexion (lecture seule)'
                }),
                ('🎯 Mon Rôle', {
                    'fields': ('role_display',),
                    'description': 'Votre rôle dans le restaurant'
                }),
            )
        
        # Default fieldsets for managers/superusers
        fieldsets = list(self.fieldsets)
        
        # Hide superuser field for non-superusers
        if not request.user.is_superuser:
            fieldsets = [fs for fs in fieldsets if 'is_superuser' not in str(fs)]
        
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on user role - JAZZMIN COMPATIBLE"""
        readonly = list(self.readonly_fields)
        
        # If staff editing their own profile
        if (obj and obj == request.user and 
            not request.user.is_superuser and
            request.user.groups.filter(name='Restaurant Staff').exists()):
            
            # Staff can't change their role, groups, or staff status
            readonly.extend(['is_staff', 'is_superuser'])
        
        return readonly
    
    def response_change(self, request, obj):
        """Custom response after changing user - JAZZMIN COMPATIBLE"""
        # Add success message for role changes
        if hasattr(request, '_role_changed'):
            from django.contrib import messages
            messages.success(request, f"Rôle mis à jour avec succès pour {obj.username}")
        
        return super().response_change(request, obj)
        """Custom save to handle password and roles"""
        super().save_model(request, obj, form, change)
        
        # Handle role assignment for both new and existing users
        if hasattr(form, 'cleaned_data'):
            role = form.cleaned_data.get('role')
            
            if role:
                print(f"🔄 Updating role for user {obj.username} to {role}")
                
                # Clear existing groups first
                obj.groups.clear()
                
                # Clear existing permissions
                obj.user_permissions.clear()
                
                if role == 'manager':
                    obj.is_staff = True
                    obj.is_superuser = False
                    
                    from django.contrib.auth.models import Group
                    manager_group, created = Group.objects.get_or_create(name='Restaurant Manager')
                    obj.groups.add(manager_group)
                    
                    # Assign manager permissions
                    self._assign_manager_permissions(obj)
                    print(f"✅ User {obj.username} is now MANAGER")
                    
                elif role == 'staff':
                    obj.is_staff = True
                    obj.is_superuser = False
                    
                    from django.contrib.auth.models import Group
                    staff_group, created = Group.objects.get_or_create(name='Restaurant Staff')
                    obj.groups.add(staff_group)
                    
                    # Assign staff permissions
                    self._assign_staff_permissions(obj)
                    print(f"✅ User {obj.username} is now STAFF")
                
                obj.save()  # Save again after role changes
                
                # Force refresh to see changes
                from django.contrib import messages
                messages.success(request, f"Rôle {role} assigné avec succès à {obj.username}")
    
    def _assign_manager_permissions(self, user):
        """Assign all restaurant permissions to manager"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        try:
            restaurant_models = ['reservation', 'restaurantinfo', 'specialdate', 'timeslot', 'notification']
            manager_permissions = []
            
            for model_name in restaurant_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    model_permissions = Permission.objects.filter(content_type=content_type)
                    manager_permissions.extend(model_permissions)
                except ContentType.DoesNotExist:
                    continue
            
            user.user_permissions.set(manager_permissions)
            print(f"✅ Assigned {len(manager_permissions)} manager permissions to {user.username}")
        except Exception as e:
            print(f"❌ Error assigning manager permissions: {e}")
    
    def _assign_staff_permissions(self, user):
        """Assign limited permissions to staff"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        try:
            staff_permissions = []
            
            # Reservation permissions (view and change only)
            reservation_ct = ContentType.objects.get(app_label='reservations', model='reservation')
            staff_permissions.extend(Permission.objects.filter(
                content_type=reservation_ct,
                codename__in=['view_reservation', 'change_reservation']
            ))
            
            # View-only permissions for other models
            other_models = ['restaurantinfo', 'specialdate', 'timeslot', 'notification']
            for model_name in other_models:
                try:
                    content_type = ContentType.objects.get(app_label='reservations', model=model_name)
                    staff_permissions.extend(Permission.objects.filter(
                        content_type=content_type,
                        codename__startswith='view_'
                    ))
                except ContentType.DoesNotExist:
                    continue
            
            user.user_permissions.set(staff_permissions)
            print(f"✅ Assigned {len(staff_permissions)} staff permissions to {user.username}")
        except Exception as e:
            print(f"❌ Error assigning staff permissions: {e}")

# ===== UTILITY FUNCTIONS =====

def get_dashboard_metrics():
    """Get dashboard metrics directly - CASABLANCA TIMEZONE VERSION"""
    # Get current time in Casablanca timezone
    casablanca_now = timezone.localtime(timezone.now())
    today = casablanca_now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    print(f"🔍 CASABLANCA DEBUG - Current time: {casablanca_now}")
    print(f"🔍 CASABLANCA DEBUG - Today date: {today}")
    
    # Get restaurant instance (single instance)
    restaurant = get_restaurant_info()
    
    # Calculate metrics - UPDATED WITH FRENCH STATUS AND CASABLANCA TIME
    metrics = {
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'today_confirmed': Reservation.objects.filter(date=today, status='Confirmée').count(),
        'today_pending': Reservation.objects.filter(date=today, status='En attente').count(),
        'today_guests': Reservation.objects.filter(date=today).aggregate(
            total=Sum('number_of_guests')
        )['total'] or 0,
        
        'week_reservations': Reservation.objects.filter(date__gte=week_start).count(),
        'month_reservations': Reservation.objects.filter(date__gte=month_start).count(),
        
        'total_tables': restaurant.number_of_tables,
        'available_tables': get_available_tables_count(today),
        
        'peak_hour': get_peak_hour_today(today),
        'next_available_slot': get_next_available_slot(),
        'occupancy_rate': restaurant.get_occupancy_rate_today(),
        'daily_average': round(Reservation.objects.filter(date__gte=month_start).count() / max(1, (today - month_start).days + 1), 1),
        
        # Restaurant info for display
        'restaurant_name': restaurant.name,
        'restaurant_phone': restaurant.phone,
        'restaurant_email': restaurant.email,
        'restaurant_address': restaurant.address,
        'restaurant_capacity': restaurant.capacity,
        
        # Notification metrics
        'unread_notifications': Notification.objects.filter(is_read=False).count(),
        'today_notifications': Notification.objects.filter(created_at__date=today).count(),
    }
    
    # Chart data - FIXED: Use actual reservation times
    chart_data = {
        'weekly_reservations': {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': get_weekly_stats(week_start)
        },
        'daily_time_slots': get_correct_daily_time_slots_data(today)
    }
    
    return metrics, chart_data

def get_correct_daily_time_slots_data(date):
    """Get reservation data by ACTUAL reservation times - CASABLANCA TIMEZONE VERSION"""
    from collections import defaultdict
    
    # Get current Casablanca time for debug
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 ADMIN CHART DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 ADMIN CHART DEBUG - Getting data for date: {date}")
    
    # Get all reservations for the specified date
    todays_reservations = Reservation.objects.filter(date=date).order_by('time')
    
    print(f"🔍 ADMIN CHART DEBUG - Found {todays_reservations.count()} reservations")
    
    if not todays_reservations.exists():
        print("🔍 ADMIN CHART DEBUG - No reservations, returning empty data")
        return {
            'labels': [],
            'data': []
        }
    
    # Count reservations by actual time - ONLY use actual reservation times
    time_counts = defaultdict(int)
    
    for reservation in todays_reservations:
        time_str = reservation.time.strftime('%H:%M')
        time_counts[time_str] += 1
        print(f"🔍 ADMIN CHART DEBUG - Reservation: {reservation.customer_name} at {time_str} (status: {reservation.status})")
    
    # Sort times and prepare data - CRITICAL: Only include times that have reservations
    sorted_times = sorted(time_counts.keys())
    labels = sorted_times
    data = [time_counts[time] for time in sorted_times]
    
    print(f"🔍 ADMIN CHART DEBUG - Final labels: {labels}")
    print(f"🔍 ADMIN CHART DEBUG - Final data: {data}")
    print(f"🔍 ADMIN CHART DEBUG - Time counts: {dict(time_counts)}")
    
    return {
        'labels': labels,
        'data': data
    }

def get_available_tables_count(date):
    """Calculate available tables for given date - CASABLANCA TIMEZONE VERSION"""
    restaurant = get_restaurant_info()
    
    # Debug timezone info
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 TABLES DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 TABLES DEBUG - Checking availability for date: {date}")
    
    reservations_count = Reservation.objects.filter(
        date=date,
        status__in=['Confirmée', 'En attente']
    ).count()
    
    available = max(0, restaurant.number_of_tables - reservations_count)
    print(f"🔍 TABLES DEBUG - Total tables: {restaurant.number_of_tables}, Reserved: {reservations_count}, Available: {available}")
    
    return available

def get_peak_hour_today(date):
    """Find the busiest hour for today - CASABLANCA TIMEZONE VERSION"""
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 PEAK HOUR DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 PEAK HOUR DEBUG - Checking peak hour for date: {date}")
    
    peak_hour = Reservation.objects.filter(
        date=date,
        status__in=['En attente', 'Confirmée']
    ).values('time').annotate(
        total_guests=Sum('number_of_guests')
    ).order_by('-total_guests').first()
    
    if peak_hour and peak_hour['total_guests'] > 0:
        result = peak_hour['time'].strftime('%H:%M')
        print(f"🔍 PEAK HOUR DEBUG - Peak hour found: {result} with {peak_hour['total_guests']} guests")
        return result
    
    print(f"🔍 PEAK HOUR DEBUG - No peak hour found")
    return None

def get_next_available_slot():
    """Find next available time slot - CASABLANCA TIMEZONE VERSION"""
    try:
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        current_date = casablanca_now.date()
        current_time = casablanca_now.time()
        
        print(f"🔍 NEXT SLOT DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 NEXT SLOT DEBUG - Current date: {current_date}, Current time: {current_time}")
        
        # Look for available slots in the next 7 days
        for days_ahead in range(7):
            check_date = current_date + timedelta(days=days_ahead)
            time_slots = TimeSlot.objects.filter(is_active=True).order_by('time')
            
            for slot in time_slots:
                # If it's today, skip past time slots (with 30min buffer)
                if days_ahead == 0:
                    time_with_buffer = (datetime.combine(current_date, current_time) + timedelta(minutes=30)).time()
                    if slot.time <= time_with_buffer:
                        print(f"🔍 NEXT SLOT DEBUG - Skipping past slot: {slot.time}")
                        continue
                
                # Count current reservations for this slot
                reservations_count = Reservation.objects.filter(
                    date=check_date,
                    time=slot.time,
                    status__in=['Confirmée', 'En attente']
                ).count()
                
                print(f"🔍 NEXT SLOT DEBUG - Slot {slot.time} on {check_date}: {reservations_count}/{slot.max_reservations}")
                
                # Check if slot is available
                if reservations_count < slot.max_reservations:
                    if days_ahead == 0:
                        result = f"Aujourd'hui {slot.time.strftime('%H:%M')}"
                    elif days_ahead == 1:
                        result = f"Demain {slot.time.strftime('%H:%M')}"
                    else:
                        result = f"{check_date.strftime('%d/%m')} à {slot.time.strftime('%H:%M')}"
                    
                    print(f"🔍 NEXT SLOT DEBUG - Available slot found: {result}")
                    return result
        
        print(f"🔍 NEXT SLOT DEBUG - No available slots found")
        return "Aucun créneau disponible cette semaine"
        
    except Exception as e:
        print(f"🔍 NEXT SLOT DEBUG - Error: {e}")
        return "Vérification en cours..."

def get_weekly_stats(week_start):
    """Get reservation data for the current week - CASABLANCA TIMEZONE VERSION"""
    casablanca_now = timezone.localtime(timezone.now())
    print(f"🔍 WEEKLY STATS DEBUG - Casablanca time: {casablanca_now}")
    print(f"🔍 WEEKLY STATS DEBUG - Week start: {week_start}")
    
    data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = Reservation.objects.filter(date=day).count()
        data.append(count)
        print(f"🔍 WEEKLY STATS DEBUG - Day {day}: {count} reservations")
    
    print(f"🔍 WEEKLY STATS DEBUG - Final weekly data: {data}")
    return data

def custom_admin_index(request, extra_context=None):
    """Custom admin index that shows unified dashboard with sidebar and CASABLANCA TIMEZONE"""
    try:
        # Get current Casablanca time
        casablanca_now = timezone.localtime(timezone.now())
        today = casablanca_now.date()
        
        print(f"🔍 DASHBOARD DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 DASHBOARD DEBUG - Today date: {today}")
        
        # Get dashboard metrics
        metrics, chart_data = get_dashboard_metrics()
        
        # Recent reservations (last 24 hours) - use Casablanca timezone
        last_24h = casablanca_now - timedelta(hours=24)
        recent_reservations = Reservation.objects.filter(
            created_at__gte=last_24h
        ).order_by('-created_at')[:10]
        
        print(f"🔍 DASHBOARD DEBUG - Looking for reservations since: {last_24h}")
        print(f"🔍 DASHBOARD DEBUG - Found {recent_reservations.count()} recent reservations")
        
        # Recent notifications
        recent_notifications = Notification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Today's schedule
        todays_schedule = Reservation.objects.filter(
            date=today
        ).order_by('time')
        
        print(f"🔍 DASHBOARD DEBUG - Today's schedule has {todays_schedule.count()} reservations")
        
        # Get admin context
        app_list = admin.site.get_app_list(request)
        
        # Add JavaScript to fix profile menu
        profile_fix_script = f"""
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Find the user menu dropdown
            const userMenu = document.querySelector('#user-tools');
            if (userMenu) {{
                // Find all links in the user menu
                const menuLinks = userMenu.querySelectorAll('a');
                menuLinks.forEach(link => {{
                    // Fix the "Profil" link to point to user edit page
                    if (link.textContent.trim() === 'Profil') {{
                        link.href = '/admin/auth/user/{request.user.id}/change/';
                        console.log('Fixed Profil link:', link.href);
                    }}
                    // Remove "Voir le profil" link
                    if (link.textContent.trim().includes('Voir le profil')) {{
                        link.style.display = 'none';
                        console.log('Hidden Voir le profil link');
                    }}
                }});
                
                // Alternative: Find by URL pattern and fix
                const profileLinks = userMenu.querySelectorAll('a[href*="/admin/auth/user/"]');
                profileLinks.forEach(link => {{
                    if (link.textContent.trim().includes('Voir le profil')) {{
                        link.remove(); // Remove the "Voir le profil" link completely
                    }}
                }});
            }}
            
            // Also check in any dropdown menus
            const dropdowns = document.querySelectorAll('.dropdown-menu, .user-menu, .account-menu');
            dropdowns.forEach(dropdown => {{
                const links = dropdown.querySelectorAll('a');
                links.forEach(link => {{
                    if (link.textContent.trim() === 'Profil') {{
                        link.href = '/admin/auth/user/{request.user.id}/change/';
                    }}
                    if (link.textContent.trim().includes('Voir le profil')) {{
                        link.remove();
                    }}
                }});
            }});
        }});
        </script>
        """
        
        context = {
            'title': 'Administration - Resto Pêcheur',
            'app_list': app_list,
            'available_apps': app_list,
            'metrics': metrics,
            'chart_data': chart_data,
            'recent_reservations': recent_reservations,
            'recent_notifications': recent_notifications,
            'todays_schedule': todays_schedule,
            # Flatten the metrics for direct access
            'today_reservations': metrics['today_reservations'],
            'today_guests': metrics['today_guests'],
            'available_tables': metrics['available_tables'],
            'total_tables': metrics['total_tables'],
            'occupancy_rate': metrics['occupancy_rate'],
            'restaurant_name': metrics['restaurant_name'],
            'restaurant_capacity': metrics['restaurant_capacity'],
            'unread_notifications': metrics['unread_notifications'],
            # Add timezone info for frontend
            'casablanca_time': casablanca_now.isoformat(),
            'casablanca_date': today.isoformat(),
            # Add the profile fix script
            'profile_fix_script': profile_fix_script,
        }
        context.update(extra_context or {})
        
        # Create a custom response that includes our script
        response = TemplateResponse(request, 'admin/unified_dashboard_with_sidebar.html', context)
        
        # Inject our script into the response
        def inject_script(response):
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                if '</body>' in content:
                    content = content.replace('</body>', f'{profile_fix_script}</body>')
                    response.content = content.encode('utf-8')
            return response
        
        response.add_post_render_callback(inject_script)
        return response
    
    except Exception as e:
        print(f"🔍 DASHBOARD DEBUG - Error: {e}")
        # Fallback to default admin if there's an error
        from django.contrib.admin.sites import AdminSite
        return AdminSite().index(request, extra_context)
    
# Override the admin site index
admin.site.index = custom_admin_index

# Simplify the custom context to avoid Jazzmin conflicts
def safe_custom_each_context(request):
    """Safe custom context that doesn't conflict with Jazzmin"""
    try:
        context = {}
        if hasattr(request, 'user') and request.user.is_authenticated:
            context['profile_url'] = f'/admin/auth/user/{request.user.id}/change/'
        return context
    except Exception as e:
        print(f"Context error: {e}")
        return {}

# Store original method safely
try:
    original_each_context = admin.site.each_context
    admin.site.each_context = lambda request: {**original_each_context(request), **safe_custom_each_context(request)}
except Exception as e:
    print(f"Could not override admin context: {e}")

# ===== MODEL ADMIN CLASSES =====

class NotificationAdmin(admin.ModelAdmin):
    """Enhanced admin interface for notifications with email tracking - CASABLANCA TIMEZONE"""
    
    # ✅ REORGANIZED: Better column order without priority
    list_display = [
        'admin_read_status',      # 1️⃣ ADMIN: Has admin read this? (✅/❌)
        'email_tracking_status',  # 2️⃣ CLIENT: Did client see email? (● ✓ ✓✓)
        'title_with_customer',    # 3️⃣ MESSAGE: What's the notification about?
        'message_preview',        # 4️⃣ CONTENT: Preview of message
        'customer_contact',       # 5️⃣ CONTACT: Phone/email links
        'time_display',          # 6️⃣ WHEN: When was this created
        'quick_actions'          # 7️⃣ ACTIONS: Quick buttons
    ]

    # ✅ Also remove priority from filters since we're not showing it
    list_filter = [
        'message_type', 
        'is_read',
        'email_sent',              
        'email_opened_by_client',  
        'created_at',
        # 'priority',  # ✅ REMOVED
    ]

    # ✅ And remove from fields in the form
    fields = [
        'title',
        'message',
        'message_type',
        # 'priority',  # ✅ REMOVED - let it default to 'normal'
        'related_reservation',
        'is_read',
        'user',
        'created_at',
        'read_at',
        # Email tracking section
        'email_tracking_details',
        'email_sent',
        'email_sent_at',
        'email_opened_by_client',
        'email_opened_at',
        'tracking_token',
        'client_ip',
        'client_user_agent',
        'reservation_details'
    ]
        
    search_fields = [
        'title',
        'message',
        'related_reservation__customer_name',
        'related_reservation__customer_email',
        'related_reservation__customer_phone'
    ]
    
    readonly_fields = [
        'user',
        'created_at',
        'read_at',
        'email_sent_at',       # ✅ NEW: Show when email was sent
        'email_opened_at',     # ✅ NEW: Show when email was opened
        'tracking_token',      # ✅ NEW: Show tracking token
        'client_ip',           # ✅ NEW: Show client IP who opened email
        'client_user_agent',   # ✅ NEW: Show client browser info
        'reservation_details',
        'email_tracking_details'  # ✅ NEW: Detailed tracking info
    ]
    
    ordering = ['-created_at']
    list_per_page = 20
    

    # Enhanced actions
    actions = ['mark_as_read', 'mark_as_unread', 'delete_read_messages', 'resend_email']  # ✅ NEW: Added resend_email
    
    # ✅ NEW: Email tracking status display (the main feature you wanted)
    def email_tracking_status(self, obj):
        """Show email tracking status with ● ✓ ✓✓ indicators"""
        if not obj.email_sent:
            # ● Red dot = Email failed to send or not sent
            return format_html('<span style="font-size: 18px; color: #dc3545;" title="Email non envoyé">●</span>')
        elif obj.email_sent and obj.email_opened_by_client:
            # ✓✓ Double checkmarks = Client opened/seen the email  
            return format_html('<span style="font-size: 16px; color: #28a745;" title="Email ouvert par le client">✓✓</span>')
        elif obj.email_sent and not obj.email_opened_by_client:
            # ✓ Single checkmark = Email sent but client hasn't seen it yet
            return format_html('<span style="font-size: 16px; color: #ffc107;" title="Email envoyé mais non ouvert">✓</span>')
        else:
            # Default fallback
            return format_html('<span style="font-size: 18px; color: #6c757d;" title="Statut inconnu">●</span>')
    email_tracking_status.short_description = "📧"
    
    # ✅ NEW: Admin read status separate from email tracking
    def admin_read_status(self, obj):
        """Show if admin has read this notification"""
        if obj.is_read:
            return format_html('<span style="color: #28a745;" title="Lu par admin">✅</span>')
        else:
            return format_html('<span style="color: #dc3545; font-weight: bold;" title="Non lu par admin">❌</span>')
    admin_read_status.short_description = "Admin"
        
    # ✅ NEW: Detailed email tracking info for the form view
    def email_tracking_details(self, obj):
        """Show comprehensive email tracking information"""
        if not obj.email_sent:
            return format_html('''
                <div style="background: linear-gradient(135deg, #fff5f5 0%, #fee 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #dc3545;">
                    <h4 style="color: #dc3545; margin-top: 0;">❌ Email non envoyé</h4>
                    <p style="margin: 5px 0; color: #721c24;">L'email de confirmation n'a pas encore été envoyé à ce client.</p>
                    <p style="margin: 5px 0; color: #721c24;"><strong>Action recommandée:</strong> Contacter le client par téléphone</p>
                </div>
            ''')
        
        # Email was sent
        sent_info = f"📤 Email envoyé le {obj.email_sent_at.strftime('%d/%m/%Y à %H:%M')}" if obj.email_sent_at else "📤 Email envoyé"
        
        if obj.email_opened_by_client:
            # Client opened the email
            opened_info = f"👁️ Ouvert le {obj.email_opened_at.strftime('%d/%m/%Y à %H:%M')}" if obj.email_opened_at else "👁️ Ouvert par le client"
            
            client_details = ""
            if obj.client_ip or obj.client_user_agent:
                client_details = f"""
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <small style="color: #6c757d;">
                            <strong>Détails techniques:</strong><br>
                            {f"IP: {obj.client_ip}<br>" if obj.client_ip else ""}
                            {f"Navigateur: {obj.client_user_agent[:100]}..." if obj.client_user_agent else ""}
                        </small>
                    </div>
                """
            
            return format_html('''
                <div style="background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                    <h4 style="color: #28a745; margin-top: 0;">✅ Email reçu et ouvert par le client</h4>
                    <p style="margin: 5px 0; color: #155724;">📤 {}</p>
                    <p style="margin: 5px 0; color: #155724;">👁️ {}</p>
                    <p style="margin: 5px 0; color: #155724;"><strong>Statut:</strong> Le client a bien reçu et consulté l'email ✓</p>
                    {}
                </div>
            ''', sent_info.replace('📤 ', ''), opened_info.replace('👁️ ', ''), client_details)
        else:
            # Email sent but not opened yet
            time_since_sent = ""
            if obj.email_sent_at:
                from django.utils import timezone
                diff = timezone.now() - obj.email_sent_at
                if diff.days > 0:
                    time_since_sent = f" (il y a {diff.days} jour{'s' if diff.days > 1 else ''})"
                elif diff.seconds > 3600:
                    time_since_sent = f" (il y a {diff.seconds // 3600}h)"
                else:
                    time_since_sent = f" (il y a {diff.seconds // 60}min)"
            
            return format_html('''
                <div style="background: linear-gradient(135deg, #fffbf0 0%, #fff3cd 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <h4 style="color: #856404; margin-top: 0;">⏳ Email envoyé mais pas encore ouvert</h4>
                    <p style="margin: 5px 0; color: #856404;">📤 {}{}</p>
                    <p style="margin: 5px 0; color: #856404;">👁️ Le client n'a pas encore ouvert l'email</p>
                    <p style="margin: 5px 0; color: #856404;"><strong>Action possible:</strong> Relancer par téléphone si urgent</p>
                    <div style="background: #fff; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <small style="color: #6c757d;">
                            <strong>Token de suivi:</strong> {}<br>
                            <strong>URL de tracking:</strong> /track/{}/
                        </small>
                    </div>
                </div>
            ''', sent_info.replace('📤 ', ''), time_since_sent, 
                str(obj.tracking_token)[:8] + "...", str(obj.tracking_token))
    
    email_tracking_details.short_description = "📧 Suivi Email Détaillé"
    
    # ✅ NEW: Action to resend emails
    def resend_email(self, request, queryset):
        """Resend email for selected notifications"""
        count = 0
        for notification in queryset:
            if notification.related_reservation and notification.related_reservation.customer_email:
                # Reset email tracking status
                notification.email_sent = False
                notification.email_opened_by_client = False
                notification.email_opened_at = None
                notification.email_sent_at = None
                notification.save()
                count += 1
        
        self.message_user(request, f"📧 {count} email(s) marqué(s) pour renvoi.")
    resend_email.short_description = "📧 Renvoyer les emails"
    
    # ✅ KEEP ALL YOUR EXISTING METHODS BELOW (priority_icon, read_status, etc.)
    def priority_icon(self, obj):
        """Show priority with colored icon"""
        if obj.priority == 'urgent':
            return format_html('<span style="font-size: 16px; color: #dc3545;">🚨</span>')
        elif obj.priority == 'normal':
            return format_html('<span style="font-size: 16px; color: #ffc107;">📨</span>')
        else:
            return format_html('<span style="font-size: 16px; color: #28a745;">ℹ️</span>')
    priority_icon.short_description = "Priorité"
    
    def read_status(self, obj):
        """Show read status"""
        if obj.is_read:
            return format_html('<span style="color: #6c757d;">✓ Lu</span>')
        else:
            return format_html('<span style="color: #333354d0; font-weight: bold;">● Non lu</span>')
    read_status.short_description = "Statut"
    
    def title_with_customer(self, obj):
        """Show title with customer name highlighted"""
        if obj.related_reservation:
            customer = obj.related_reservation.customer_name
            return format_html('<strong>{}</strong><br><small style="color: #6c757d;">{}</small>',
                             obj.title, customer)
        return format_html('<strong>{}</strong>', obj.title)
    title_with_customer.short_description = "Message"
    
    def message_preview(self, obj):
        """Show message preview"""
        preview = obj.message[:150] + "..." if len(obj.message) > 150 else obj.message
        return format_html('<div style="max-width: 350px; white-space: pre-line; font-size: 12px; line-height: 1.4;">{}</div>', 
                          preview)
    message_preview.short_description = "Contenu"
    
    def customer_contact(self, obj):
        """Show customer contact info"""
        if obj.related_reservation:
            res = obj.related_reservation
            contact_parts = []
            
            if res.customer_phone:
                phone_display = res.customer_phone[:12] + "..." if len(res.customer_phone) > 12 else res.customer_phone
                contact_parts.append(f'<a href="tel:{res.customer_phone}" style="color: #333354d0; text-decoration: none;">📞 {phone_display}</a>')
            
            if res.customer_email:
                email_display = res.customer_email[:20] + "..." if len(res.customer_email) > 20 else res.customer_email
                contact_parts.append(f'<a href="mailto:{res.customer_email}" style="color: #333354d0; text-decoration: none;">📧 {email_display}</a>')
            
            if contact_parts:
                return format_html('<br>'.join(contact_parts))
            else:
                return format_html('<span style="color: #dc3545;">❌ Pas de contact</span>')
        return "-"
    customer_contact.short_description = "Contact"
    
    def time_display(self, obj):
        """Show time in readable format - CASABLANCA TIMEZONE VERSION"""
        from django.utils import timezone
        
        # Convert to Casablanca timezone
        created_local = timezone.localtime(obj.created_at)
        
        return format_html('<small style="color: #6c757d;">{}<br>{}</small>',
                        created_local.strftime('%d/%m %H:%M'),
                        obj.time_ago)
    time_display.short_description = "Quand"
    
    def quick_actions(self, obj):
        """Show quick action buttons"""
        if obj.related_reservation:
            from django.urls import reverse
            try:
                res_url = reverse('admin:reservations_reservation_change', args=[obj.related_reservation.pk])
                return format_html(
                    '<a href="{}" class="button" style="background: #333354d0; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">📋 Voir</a>',
                    res_url
                )
            except:
                return "-"
        return "-"
    quick_actions.short_description = "Actions"
    
    def reservation_details(self, obj):
        """Show full reservation details in form"""
        if obj.related_reservation:
            from django.urls import reverse
            res = obj.related_reservation
            try:
                res_url = reverse('admin:reservations_reservation_change', args=[res.pk])
                return format_html("""
                    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e8e8f0 100%); padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #333354d0;">
                        <h3 style="color: #333354; margin-top: 0;">📋 Détails de la réservation</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                            <div>
                                <p style="margin: 8px 0;"><strong>👤 Client:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>📅 Date:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>⏰ Heure:</strong> {}</p>
                                <p style="margin: 8px 0;"><strong>👥 Personnes:</strong> {}</p>
                            </div>
                            <div>
                                <p style="margin: 8px 0;"><strong>📞 Téléphone:</strong> <a href="tel:{}" style="color: #333354d0;">{}</a></p>
                                <p style="margin: 8px 0;"><strong>📧 Email:</strong> <a href="mailto:{}" style="color: #333354d0;">{}</a></p>
                                <p style="margin: 8px 0;"><strong>📊 Statut:</strong> <span style="background: #333354d0; color: white; padding: 3px 10px; border-radius: 15px; font-size: 12px;">{}</span></p>
                                {}
                            </div>
                        </div>
                        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                        <div style="text-align: center;">
                            <a href="{}" class="button" style="background: linear-gradient(45deg, #333354d0, #333354); color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
                                🔗 Gérer cette réservation
                            </a>
                        </div>
                    </div>
                """,
                    res.customer_name,
                    res.date.strftime('%d/%m/%Y'),
                    res.time.strftime('%H:%M'),
                    res.number_of_guests,
                    res.customer_phone or 'Non fourni',
                    res.customer_phone or 'Non fourni',
                    res.customer_email or 'Non fourni',
                    res.customer_email or 'Non fourni',
                    res.get_status_display(),
                    f'<p style="margin: 8px 0;"><strong>🪑 Table:</strong> {res.table_number}</p>' if res.table_number else '',
                    res_url
                )
            except Exception as e:
                return format_html('<div style="color: #dc3545;">Erreur: {}</div>', str(e))
        return format_html('<div style="text-align: center; color: #6c757d; padding: 20px;">Aucune réservation liée</div>')
    reservation_details.short_description = "Réservation Liée"
    
    def mark_as_read(self, request, queryset):
        """Mark selected messages as read - CASABLANCA TIMEZONE VERSION"""
        casablanca_now = timezone.localtime(timezone.now())
        count = queryset.filter(is_read=False).update(is_read=True, read_at=casablanca_now)
        self.message_user(request, f"✅ {count} message(s) marqué(s) comme lu(s).")
    mark_as_read.short_description = "✓ Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        """Mark selected messages as unread"""
        count = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f"📩 {count} message(s) marqué(s) comme non lu(s).")
    mark_as_unread.short_description = "● Marquer comme non lu"
    
    def delete_read_messages(self, request, queryset):
        """Delete only read messages"""
        read_messages = queryset.filter(is_read=True)
        count = read_messages.count()
        read_messages.delete()
        self.message_user(request, f"🗑️ {count} message(s) lu(s) supprimé(s).")
    delete_read_messages.short_description = "🗑️ Supprimer les messages lus"
    
    # Auto-mark as read when viewing details
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Auto-mark message as read when viewing details"""
        obj = self.get_object(request, object_id)
        if obj and not obj.is_read:
            obj.mark_as_read()
            self.message_user(request, f"✅ Notification marquée comme lue: {obj.title}")
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user', 'related_reservation').order_by('-created_at')
    
class RestaurantInfoAdmin(admin.ModelAdmin):
    """Admin for single restaurant configuration - CASABLANCA TIMEZONE VERSION"""
    
    fieldsets = (
        ('Restaurant Resto Pêcheur', {
            'fields': ('address', 'phone', 'email', 'description'),
            'description': 'Informations de contact pour Resto Pêcheur'
        }),
        ('Capacité et Tables', {
            'fields': ('capacity', 'number_of_tables'),
            'description': 'Configuration de la capacité du restaurant'
        }),
        ('Horaires d\'Ouverture', {
            'fields': ('opening_time', 'closing_time'),
            'description': 'Horaires d\'ouverture standard'
        }),
        ('Fermetures Hebdomadaires', {
            'fields': (
                'closed_on_monday', 'closed_on_tuesday', 'closed_on_wednesday',
                'closed_on_thursday', 'closed_on_friday', 'closed_on_saturday', 'closed_on_sunday'
            ),
            'classes': ('collapse',),
            'description': 'Jours de fermeture hebdomadaire réguliers'
        }),
    )
    
    # FIXED: Prevent multiple restaurants
    def has_add_permission(self, request):
        """Allow add only if no restaurant exists"""
        return False  # Always prevent adding since we use singleton
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of restaurant info"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Always redirect to single restaurant edit"""
        restaurant = get_restaurant_info()  # This will create if doesn't exist
        return redirect(f'/admin/reservations/restaurantinfo/{restaurant.pk}/change/')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Ensure we're always editing the single restaurant"""
        restaurant = get_restaurant_info()
        if str(object_id) != str(restaurant.pk):
            return redirect(f'/admin/reservations/restaurantinfo/{restaurant.pk}/change/')
        
        extra_context = extra_context or {}
        extra_context['title'] = 'Configuration Restaurant - Resto Pêcheur'
        return super().change_view(request, object_id, form_url, extra_context)

class ReservationAdmin(admin.ModelAdmin):
    """Admin for reservations - CASABLANCA TIMEZONE VERSION"""
    list_display = [
        'customer_name', 'customer_phone', 'date', 'time', 
        'number_of_guests', 'status', 'colored_status', 'created_at', 'is_today_reservation'
    ]
    list_filter = ['status', 'date', 'number_of_guests', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email']
    list_editable = ['status']
    date_hierarchy = 'date'
    ordering = ['-date', '-time']
    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_completed']
    
    fieldsets = (
        ('Information Client', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Détails Réservation', {
            'fields': ('date', 'time', 'number_of_guests', 'status', 'table_number')
        }),
        ('Informations Supplémentaires', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
        ('Historique', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',),
            'description': 'Ces champs sont automatiquement mis à jour'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at', 'cancelled_at']
    
    def colored_status(self, obj):
        # Support both French and English status values
        colors = {
            # English statuses
            'pending': '#ff8f00',
            'confirmed': '#4caf50',
            'cancelled': '#f44336',
            'completed': '#2196f3',
            # French statuses
            'En attente': '#ff8f00',
            'Confirmée': '#4caf50',
            'Annulée': '#f44336',
            'Terminée': '#2196f3',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">●</span>',
            colors.get(obj.status, '#666')
        )
    colored_status.short_description = 'État'
    
    def is_today_reservation(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            if obj.date == today:
                return format_html('<span style="color: #4caf50; font-weight: bold;">Aujourd\'hui</span>')
            elif obj.date > today:
                return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
            else:
                return format_html('<span style="color: #666;">Passée</span>')
        except:
            return '-'
    is_today_reservation.short_description = 'Timing'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related().order_by('-date', '-time')
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='Confirmée')
        self.message_user(request, f'{updated} réservations marquées comme confirmées.')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='Annulée')
        self.message_user(request, f'{updated} réservations annulées.')
    mark_as_cancelled.short_description = "Annuler les réservations"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='Terminée')
        self.message_user(request, f'{updated} réservations marquées comme terminées.')
    mark_as_completed.short_description = "Marquer comme terminées"

class TimeSlotAdmin(admin.ModelAdmin):
    """Admin for time slots - CASABLANCA TIMEZONE VERSION"""
    list_display = ['time', 'max_reservations', 'is_active', 'current_reservations', 'availability_status']
    list_filter = ['is_active']
    ordering = ['time']
    list_editable = ['max_reservations', 'is_active']
    
    def current_reservations(self, obj):
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        today = casablanca_now.date()
        
        print(f"🔍 TIMESLOT DEBUG - Casablanca time: {casablanca_now}")
        print(f"🔍 TIMESLOT DEBUG - Today: {today}")
        
        # Support both French and English statuses
        count = Reservation.objects.filter(
            time=obj.time,
            date=today,
            status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
        ).count()
        
        print(f"🔍 TIMESLOT DEBUG - Slot {obj.time}: {count}/{obj.max_reservations}")
        return f"{count}/{obj.max_reservations}"
    current_reservations.short_description = 'Réservations Aujourd\'hui'
    
    def availability_status(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            # Support both French and English statuses
            reservations_count = Reservation.objects.filter(
                time=obj.time,
                date=today,
                status__in=['pending', 'confirmed', 'En attente', 'Confirmée']
            ).count()
            available = obj.max_reservations - reservations_count
            
            if available <= 0:
                color = '#f44336'
                status = 'Complet'
            elif available <= 2:
                color = '#ff9800'
                status = 'Presque complet'
            else:
                color = '#4caf50'
                status = 'Disponible'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span> ({} places)',
                color, status, available
            )
        except Exception as e:
            print(f"🔍 TIMESLOT ERROR - {e}")
            return format_html('<span style="color: #999;">N/A</span>')
    availability_status.short_description = 'Disponibilité'

class SpecialDateAdmin(admin.ModelAdmin):
    """Admin for special dates - CASABLANCA TIMEZONE VERSION - FIXED FOR is_open FIELD"""
    list_display = ['date', 'reason', 'is_open_colored', 'is_upcoming_date', 'days_until_date']
    list_filter = ['is_open', 'date']  # ✅ FIXED: Changed from 'is_closed' to 'is_open'
    date_hierarchy = 'date'
    ordering = ['-date']
    
    fieldsets = (
        ('Date et Raison', {
            'fields': ('date', 'reason', 'is_open')  # ✅ FIXED: Changed from 'is_closed' to 'is_open'
        }),
        ('Horaires Spéciaux', {
            'fields': ('special_opening_time', 'special_closing_time'),
            'classes': ('collapse',),
            'description': 'Laisser vide si fermé ou pour garder les horaires normaux'
        }),
    )
    
    def is_open_colored(self, obj):
        """Show open/closed status with colors - FIXED FOR is_open FIELD"""
        if obj.is_open:
            return format_html('<span style="color: #4caf50; font-weight: bold;">✅ Ouvert</span>')
        else:
            return format_html('<span style="color: #f44336; font-weight: bold;">❌ Fermé</span>')
    is_open_colored.short_description = 'Statut'
    
    def is_upcoming_date(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            print(f"🔍 SPECIAL DATE DEBUG - Casablanca time: {casablanca_now}")
            print(f"🔍 SPECIAL DATE DEBUG - Today: {today}, Special date: {obj.date}")
            
            if obj.date == today:
                return format_html('<span style="color: #f44336; font-weight: bold;">Aujourd\'hui</span>')
            elif obj.date > today:
                return format_html('<span style="color: #ff9800; font-weight: bold;">À venir</span>')
            else:
                return format_html('<span style="color: #666;">Passée</span>')
        except Exception as e:
            print(f"🔍 SPECIAL DATE ERROR - {e}")
            return format_html('<span style="color: #999;">N/A</span>')
    is_upcoming_date.short_description = 'Statut'
    
    def days_until_date(self, obj):
        try:
            # Use Casablanca timezone
            casablanca_now = timezone.localtime(timezone.now())
            today = casablanca_now.date()
            
            if obj.date == today:
                return "Aujourd'hui"
            elif obj.date > today:
                days = (obj.date - today).days
                return f"Dans {days} jour{'s' if days > 1 else ''}"
            else:
                return "-"
        except Exception as e:
            print(f"🔍 SPECIAL DATE DAYS ERROR - {e}")
            return "-"
    days_until_date.short_description = 'Échéance'
    
    def get_queryset(self, request):
        """Filter to show only recent and upcoming dates - CASABLANCA TIMEZONE VERSION"""
        qs = super().get_queryset(request)
        # Use Casablanca timezone
        casablanca_now = timezone.localtime(timezone.now())
        thirty_days_ago = casablanca_now.date() - timedelta(days=30)
        
        print(f"🔍 SPECIAL DATE QUERYSET DEBUG - Filtering from: {thirty_days_ago}")
        return qs.filter(date__gte=thirty_days_ago)

# ===== REGISTER ALL MODELS =====
admin.site.register(Notification, NotificationAdmin)
admin.site.register(RestaurantInfo, RestaurantInfoAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(SpecialDate, SpecialDateAdmin)

# Customize admin site - REMOVE ALL BRANDING
admin.site.site_header = ""
admin.site.site_title = ""
admin.site.index_title = ""