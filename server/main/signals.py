from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def user_saved(sender, instance, **kwargs):
    from .models import Wallet
    Wallet.objects.get_or_create(user=instance)