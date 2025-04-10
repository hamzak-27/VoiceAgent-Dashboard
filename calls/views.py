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
            # Log the raw request data
            print("Webhook received!")
            
            body = request.body.decode('utf-8')
            print(f"Raw body: {body}")
            
            data = json.loads(body)
            
            # Check for different event types
            event_type = data.get('event')
            print(f"Event type: {event_type}")
            
            # Handle call_analyzed event
            if event_type == 'call_analyzed':
                call_data = data.get('call', {})
                
                # Extract phone number
                phone_number = call_data.get('from_number', 'Unknown')
                
                # Extract duration (convert ms to seconds)
                duration_ms = call_data.get('duration_ms', 0)
                duration = int(duration_ms / 1000) if duration_ms else 0
                
                # Extract call time
                start_timestamp = call_data.get('start_timestamp')
                if start_timestamp:
                    try:
                        call_time = datetime.datetime.fromtimestamp(
                            int(start_timestamp) / 1000,
                            tz=timezone.utc
                        )
                    except:
                        call_time = timezone.now()
                else:
                    call_time = timezone.now()
                
                # Extract follow-up flag, summary, transcript, recording URL
                follow_up = call_data.get('call_analysis', {}).get('custom_analysis_data', {}).get('_follow_up', False)
                summary = call_data.get('call_analysis', {}).get('call_summary', '')
                transcript = call_data.get('transcript', '')
                recording_url = call_data.get('recording_url', '')
                
                # Create call record
                call = Call.objects.create(
                    phone_number=phone_number,
                    duration=duration,
                    call_time=call_time,
                    follow_up=follow_up,
                    summary=summary,
                    transcript=transcript,
                    recording_url=recording_url
                )
                
                print(f"Created call record with ID {call.id}")
                return JsonResponse({'status': 'success', 'id': call.id}, status=201)
            
            # Handle other event types (call_started, call_ended)
            elif event_type in ['call_started', 'call_ended']:
                return JsonResponse({'status': 'received', 'event': event_type}, status=200)
            
            # Handle test payloads from Postman
            elif not event_type and 'from_number' in data:
                # This is likely a test payload
                call = Call.objects.create(
                    phone_number=data.get('from_number', 'Unknown'),
                    duration=data.get('duration', 0),
                    call_time=timezone.now(),
                    follow_up=data.get('Follow_up', False),
                    summary=data.get('summary', ''),
                    transcript=data.get('transcript', ''),
                    recording_url=data.get('recording_url', '')
                )
                
                return JsonResponse({'status': 'success', 'id': call.id}, status=201)
            
            # Handle unknown event types
            else:
                print(f"Unknown event type or structure: {data}")
                return JsonResponse({'status': 'received', 'message': 'Unknown event type'}, status=200)
                
        except Exception as e:
            import traceback
            print(f"Error processing webhook: {str(e)}")
            print(traceback.format_exc())
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
