from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import ChessGame, MultiplayerGame, User, PlayerProfile, OrganizerProfile, Leaderboard
from ttsaadmin.models import Tournament


def schedule_dashboard_update():
    from .consumers import broadcast_dashboard_update

    transaction.on_commit(broadcast_dashboard_update)


@receiver(post_save, sender=User)
def update_dashboard_for_user(sender, instance, **kwargs):
    schedule_dashboard_update()


@receiver(post_save, sender=PlayerProfile)
def update_dashboard_for_player_profile(sender, instance, **kwargs):
    schedule_dashboard_update()


@receiver(post_save, sender=ChessGame)
def update_dashboard_for_computer_game(sender, instance, **kwargs):
    schedule_dashboard_update()


@receiver(post_save, sender=MultiplayerGame)
def update_dashboard_for_multiplayer_game(sender, instance, **kwargs):
    schedule_dashboard_update()


@receiver(post_save, sender=Tournament)
@receiver(post_delete, sender=Tournament)
def update_dashboard_for_tournament(sender, instance, **kwargs):
    schedule_dashboard_update()


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
