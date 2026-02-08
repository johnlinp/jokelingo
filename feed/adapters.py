import secrets
import string
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        user.display_name = f'{user.first_name} {user.last_name}'

        # Generate a random username
        user.username = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(50))

        return user