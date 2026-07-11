from django.contrib import admin
from .models import (
    PlayerProfile, Achievement, PlayerAchievement, ChessGame,
    Lesson, PlayerLesson, Puzzle, PlayerPuzzle, Leaderboard,
    Friend, Message, AcademyNews
)


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'coins', 'level', 'learning_streak']
    list_filter = ['level', 'learning_streak']
    search_fields = ['user__username', 'user__email']


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'points', 'icon']
    list_filter = ['category']
    search_fields = ['name', 'description']


@admin.register(PlayerAchievement)
class PlayerAchievementAdmin(admin.ModelAdmin):
    list_display = ['player', 'achievement', 'earned_at', 'progress']
    list_filter = ['achievement__category', 'earned_at']
    search_fields = ['player__user__username', 'achievement__name']


@admin.register(ChessGame)
class ChessGameAdmin(admin.ModelAdmin):
    list_display = ['id', 'player', 'difficulty_level', 'result', 'moves_count', 'created_at']
    list_filter = ['difficulty_level', 'result', 'player_color']
    search_fields = ['player__user__username']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'order', 'points_reward']
    list_filter = ['category', 'difficulty']
    search_fields = ['title', 'description']


@admin.register(PlayerLesson)
class PlayerLessonAdmin(admin.ModelAdmin):
    list_display = ['player', 'lesson', 'completed', 'score', 'completed_at']
    list_filter = ['completed', 'lesson__category']
    search_fields = ['player__user__username', 'lesson__title']


@admin.register(Puzzle)
class PuzzleAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'difficulty', 'rating', 'daily']
    list_filter = ['category', 'difficulty', 'daily']
    search_fields = ['fen', 'solution']


@admin.register(PlayerPuzzle)
class PlayerPuzzleAdmin(admin.ModelAdmin):
    list_display = ['player', 'puzzle', 'solved', 'attempts', 'solved_at']
    list_filter = ['solved', 'puzzle__category']
    search_fields = ['player__user__username']


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['player', 'weekly_rank', 'monthly_rank', 'all_time_rank']
    search_fields = ['player__user__username']


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'accepted', 'created_at']
    list_filter = ['accepted', 'created_at']
    search_fields = ['from_user__user__username', 'to_user__user__username']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'read', 'created_at']
    list_filter = ['read', 'created_at']
    search_fields = ['sender__user__username', 'receiver__user__username', 'content']


@admin.register(AcademyNews)
class AcademyNewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'published_at']
    list_filter = ['published_at']
    search_fields = ['title', 'content']
