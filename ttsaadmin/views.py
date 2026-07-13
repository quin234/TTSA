from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import YouTubeChannelForm, VideoLessonForm
from .models import YouTubeChannel
from .youtube_utils import validate_and_fetch_channel_metadata, YouTubeChannelError
from ttsa_app.models import VideoLesson
from .youtube_utils import validate_and_fetch_video_metadata, YouTubeVideoError


@login_required
def admin_dashboard(request):
    """Main dashboard view for TTSA admin portal"""
    context = {
        'user': request.user,
    }
    return render(request, 'ttsaadmin/dashboard.html', context)


@login_required
def add_youtube_channel(request):
    """View for adding a YouTube channel"""
    if request.method == 'POST':
        form = YouTubeChannelForm(request.POST)
        if form.is_valid():
            try:
                channel = form.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'Successfully added YouTube channel: {channel.channel_name}'})
                
                messages.success(
                    request,
                    f'Successfully added YouTube channel: {channel.channel_name}'
                )
                return redirect('youtube_channels_list')
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(
                    request,
                    f'Error saving channel: {str(e)}'
                )
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: errors[0] for field, errors in form.errors.items()}
                return JsonResponse({'success': False, 'error': 'Please correct the errors in the form.', 'errors': errors})
            
            messages.error(
                request,
                'Please correct the errors in the form.'
            )
    else:
        form = YouTubeChannelForm()
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'ttsaadmin/add_youtube_channel.html', context)


@login_required
def youtube_channels_list(request):
    """View for listing all YouTube channels"""
    channels = YouTubeChannel.objects.filter(is_active=True).order_by('-created_at')
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        channels_data = [{
            'id': channel.id,
            'channel_id': channel.channel_id,
            'channel_url': channel.channel_url,
            'channel_name': channel.channel_name,
            'channel_description': channel.channel_description,
            'channel_thumbnail_url': channel.channel_thumbnail_url,
            'video_count': channel.video_count,
            'view_count': channel.view_count,
            'created_at': channel.created_at.isoformat(),
        } for channel in channels]
        return JsonResponse({'channels': channels_data})
    
    # For non-AJAX requests, redirect to dashboard since channels are now integrated there
    from django.shortcuts import redirect
    return redirect('admin_dashboard')


@csrf_exempt
@login_required
def validate_channel_api(request):
    """API endpoint for validating YouTube channel before submission"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        channel_url = data.get('channel_url')
        
        if not channel_url:
            return JsonResponse({'success': False, 'error': 'Channel URL is required'})
        
        # Validate and fetch metadata
        channel_metadata = validate_and_fetch_channel_metadata(channel_url)
        
        # Check if channel already exists
        if YouTubeChannel.objects.filter(channel_id=channel_metadata['channel_id']).exists():
            return JsonResponse({'success': False, 'error': 'This YouTube channel has already been added'})
        
        return JsonResponse({
            'success': True,
            'channel_id': channel_metadata['channel_id'],
            'channel_url': channel_metadata['channel_url'],
            'channel_name': channel_metadata['channel_name'],
            'channel_description': channel_metadata['channel_description'],
            'channel_thumbnail_url': channel_metadata['channel_thumbnail_url'],
            'video_count': channel_metadata['video_count'],
        })
        
    except YouTubeChannelError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@login_required
def add_video_lesson(request):
    """View for adding a YouTube video lesson"""
    if request.method == 'POST':
        form = VideoLessonForm(request.POST)
        if form.is_valid():
            try:
                video = form.save()
                
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': f'Successfully added video lesson: {video.title}'})
                
                messages.success(
                    request,
                    f'Successfully added video lesson: {video.title}'
                )
                return redirect('video_library')
            except Exception as e:
                # Return JSON if requested via AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                
                messages.error(
                    request,
                    f'Error saving video: {str(e)}'
                )
        else:
            # Return JSON if requested via AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: errors[0] for field, errors in form.errors.items()}
                return JsonResponse({'success': False, 'error': 'Please correct the errors in the form.', 'errors': errors})
            
            messages.error(
                request,
                'Please correct the errors in the form.'
            )
    else:
        form = VideoLessonForm()
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'ttsaadmin/add_video_lesson.html', context)


@login_required
def video_library(request):
    """View for listing all video lessons"""
    videos = VideoLesson.objects.all().order_by('order', '-created_at')
    
    # Return JSON if requested via AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        videos_data = [{
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'youtube_id': video.youtube_id,
            'thumbnail_url': video.thumbnail_url,
            'channel_name': video.channel_name,
            'duration': video.duration,
            'category': video.category,
            'difficulty': video.difficulty,
            'views': video.views,
            'created_at': video.created_at.isoformat(),
        } for video in videos]
        return JsonResponse({'videos': videos_data})
    
    # For non-AJAX requests, redirect to dashboard since videos are now integrated there
    from django.shortcuts import redirect
    return redirect('admin_dashboard')


@csrf_exempt
@login_required
def validate_video_api(request):
    """API endpoint for validating YouTube video before submission"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        video_url = data.get('video_url')
        
        if not video_url:
            return JsonResponse({'success': False, 'error': 'Video URL is required'})
        
        # Check if video already exists
        from .youtube_utils import extract_video_id
        video_id = extract_video_id(video_url)
        if video_id and VideoLesson.objects.filter(youtube_id=video_id).exists():
            return JsonResponse({'success': False, 'error': 'This YouTube video has already been added'})
        
        # Validate and fetch metadata
        video_metadata = validate_and_fetch_video_metadata(video_url)
        
        return JsonResponse({
            'success': True,
            'video_id': video_metadata['video_id'],
            'video_url': video_metadata['video_url'],
            'title': video_metadata['title'],
            'description': video_metadata.get('description', ''),
            'channel_name': video_metadata.get('channel_name', video_metadata.get('author_name', '')),
            'thumbnail_url': video_metadata['thumbnail_url'],
            'duration': video_metadata.get('duration', ''),
        })
        
    except YouTubeVideoError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})


@csrf_exempt
@login_required
def delete_video_lesson(request, video_id):
    """API endpoint for deleting a video lesson"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        video = VideoLesson.objects.get(id=video_id)
        video.delete()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Video deleted successfully'})
        
        messages.success(request, 'Video deleted successfully')
        return redirect('video_library')
        
    except VideoLesson.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Video not found'})
        
        messages.error(request, 'Video not found')
        return redirect('video_library')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting video: {str(e)}')
        return redirect('video_library')


@csrf_exempt
@login_required
def delete_youtube_channel(request, channel_id):
    """API endpoint for deleting a YouTube channel"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    try:
        channel = YouTubeChannel.objects.get(id=channel_id)
        channel.delete()
        
        # Return JSON if requested via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Channel deleted successfully'})
        
        messages.success(request, 'Channel deleted successfully')
        return redirect('youtube_channels_list')
        
    except YouTubeChannel.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Channel not found'})
        
        messages.error(request, 'Channel not found')
        return redirect('youtube_channels_list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        messages.error(request, f'Error deleting channel: {str(e)}')
        return redirect('youtube_channels_list')
