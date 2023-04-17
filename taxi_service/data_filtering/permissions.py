import json
from functools import wraps

from rest_framework.permissions import BasePermissionMetaclass

from data_filtering.models import Profile


class StaffPermission(metaclass=BasePermissionMetaclass):

    def has_permission(self, request, view):
        try:
            print(request.body)
            request_dict = json.loads(request.body.decode('UTF-8'))
            if request_dict["message"]["text"] == "/start":
                return True

            telegram_user_id = request_dict["message"]["from"]["id"]
            print(telegram_user_id)
            profile = Profile.objects.get(telegram_id=telegram_user_id)
            if profile.user.is_staff:
                return True
        except Exception as x:
            print(x)
            return True
        return True


def private_access():
    """
    Restrict access to the command to users allowed by the is_known_username function.
    """
    def deco_restrict(f):

        @wraps(f)
        def f_restrict(message, *args, **kwargs):
            telegram_user_id = message.chat.id
            profile = Profile.objects.get(telegram_id=telegram_user_id)
            if profile.user.is_staff:
                return f(message, *args, **kwargs)
            else:
                bot.reply_to(message, text='Who are you?  Keep on walking...')

        return f_restrict  # true decorator

    return deco_restrict
