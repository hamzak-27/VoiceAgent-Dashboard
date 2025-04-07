from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
import json
from .models import Call
from django.views.decorators.csrf import csrf_exempt
import datetime

def dashboard(request):
    # Get KPI data
    total_calls = Call.objects.count()
    avg_duration = Call.objects.aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0
    avg_duration_minutes = round(avg_duration / 60, 2)
    
    # Get call volume for the last week
    today = timezone.now().date()
    week_start = today - timedelta(days=6)
    
    call_volume_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_name = day.strftime('%a')
        count = Call.objects.filter(call_time__date=day).count()
        call_volume_data.append({'day': day_name, 'count': count})
    
    # Get recent calls
    recent_calls = Call.objects.all()[:100]  # Limit to 100 most recent calls
    
    context = {
        'total_calls': total_calls,
        'avg_duration_minutes': avg_duration_minutes,
        'call_volume_data': json.dumps(call_volume_data),
        'recent_calls': recent_calls,
    }
    
    return render(request, 'dashboard.html', context)

def get_call_details(request, call_id):
    try:
        call = Call.objects.get(id=call_id)
        data = {
            'summary': call.summary,
            'transcript': call.transcript,
            'recording_url': call.recording_url,
        }
        return JsonResponse(data)
    except Call.DoesNotExist:
        return JsonResponse({'error': 'Call not found'}, status=404)


@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Check if this is a call_analyzed event (the one with complete data)
            if data.get('event') == 'call_analyzed':
                call_data = data.get('call', {})
                
                # Extract call data from the Retell payload
                call = Call.objects.create(
                    phone_number=call_data.get('from_number', 'Unknown'),
                    duration=int(call_data.get('duration_ms', 0) / 1000),  # Convert ms to seconds
                    call_time=datetime.datetime.fromtimestamp(
                        int(call_data.get('start_timestamp', 0)) / 1000,  
                        tz=timezone.utc
                    ),
                    follow_up=call_data.get('call_analysis', {}).get('custom_analysis_data', {}).get('_follow_up', False),
                    summary=call_data.get('call_analysis', {}).get('call_summary', ''),
                    transcript=call_data.get('transcript', ''),
                    recording_url=call_data.get('recording_url', '')
                )
                
                return JsonResponse({'status': 'success', 'id': call.id}, status=201)
            else:
                # This handles other event types like call_started, call_ended
                return JsonResponse({'status': 'received', 'event': data.get('event')}, status=200)
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)

def latest_calls(request):
    last_id = request.GET.get('last_id')
    
    if last_id:
        new_calls = Call.objects.filter(id__gt=last_id).order_by('-call_time')
        calls_data = []
        
        for call in new_calls:
            calls_data.append({
                'id': call.id,
                'phone_number': call.phone_number,
                'duration': call.duration,
                'call_time': call.call_time.isoformat(),
                'follow_up': call.follow_up
            })
        
        return JsonResponse({'calls': calls_data})
    
    return JsonResponse({'calls': []})
