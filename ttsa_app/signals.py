from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PlayerProfile, OrganizerProfile, Leaderboard


@receiver(post_save, sender=User)
def create_player_profile(sender, instance, created, **kwargs):
    if created:
        PlayerProfile.objects.get_or_create(user=instance)
        # Create leaderboard entry
        Leaderboard.objects.get_or_create(player=instance.playerprofile)


@receiver(post_save, sender=User)
def save_player_profile(sender, instance, **kwargs):
    # Ensure player profile exists and is saved
    profile, _ = PlayerProfile.objects.get_or_create(user=instance)
    profile.save()


@receiver(post_save, sender=User)
def create_organizer_profile(sender, instance, created, **kwargs):
    """Create OrganizerProfile when a user becomes PLAYER_PLUS or TTSA Admin."""
    if instance.role in ('player_plus', 'ttsa_admin'):
        OrganizerProfile.objects.get_or_create(user=instance)
