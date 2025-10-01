from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Create profile if new user
    if created:
        Profile.objects.create(user=instance)

    # Ensure profile exists before saving (for existing users)
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

    instance.profile.save()  # Now safe to save