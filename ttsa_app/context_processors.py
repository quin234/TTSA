"""Global template context processors."""

from ttsaadmin.models import AcademySettings


def academy_settings(request):
    """Make the singleton AcademySettings instance available in every template."""
    return {
        'academy_settings': AcademySettings.get_settings(),
    }
