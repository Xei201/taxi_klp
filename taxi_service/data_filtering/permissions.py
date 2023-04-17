from rest_framework.permissions import BasePermissionMetaclass


class StaffPermission(metaclass=BasePermissionMetaclass):

    def has_permission(self, request, view):


        return True