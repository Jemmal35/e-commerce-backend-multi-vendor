from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, 'role', None)
        return bool(
            role == 'admin' or
            request.user.is_staff or
            request.user.is_superuser
        )
        
class IsVendorUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role= getattr(request.user, 'role', None)
        return bool(
            role == 'vendor'
        )


class IsCustomerUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, 'role', None)
        return bool(
            role == 'customer'
        )
        
class IsVendorOwnerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return hasattr(request.user, 'vendor_profile') and request.user.vendor_profile.status == "approved"
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return hasattr(request.user, 'vendor_profile') and obj.vendor == request.user.vendor_profile