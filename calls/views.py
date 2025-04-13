from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
import json
from .models import Call
from django.views.decorators.csrf import csrf_exempt
import datetime
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = None
if OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

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
def generate_summary(request, call_id):
    """
    Generate a structured summary from a call transcript using OpenAI
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        call = Call.objects.get(id=call_id)
        
        # If we already have a summary, return it
        if call.summary:
            return JsonResponse({'success': True, 'summary': call.summary})
        
        # Check if transcript exists
        if not call.transcript:
            return JsonResponse({'error': 'No transcript available for this call'}, status=400)
        
        # Check if OpenAI client is configured
        if not openai_client:
            return JsonResponse({'error': 'OpenAI API is not configured'}, status=500)
        
        # Generate summary using OpenAI
        structured_summary = generate_structured_summary_from_transcript(call.transcript)
        
        # Save the summary to the call record
        call.summary = structured_summary
        call.save()
        
        return JsonResponse({
            'success': True,
            'summary': structured_summary
        })
        
    except Call.DoesNotExist:
        return JsonResponse({'error': 'Call not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"Error generating summary: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Failed to generate summary: {str(e)}'}, status=500)

def generate_structured_summary_from_transcript(transcript):
    """
    Use OpenAI to generate a structured summary from a transcript
    """
    # Format the prompt to get structured data
    prompt = f"""
    Please analyze this customer service call transcript and extract the following information in a structured format.
    Return ONLY the extracted information in the format specified, with no additional text.
    
    The format should be:
    Customer Name: [if mentioned]
    Services Discussed: [types of services discussed]
    Patient Volume: [number of patients mentioned]
    Key Challenges: [main problems or challenges mentioned]
    Decision Maker: [who makes decisions at the practice]
    
    For each field, if the information is not available in the transcript, write "Not mentioned".
    
    Here's the transcript:
    
    {transcript}
    """
    
    try:
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured information from customer service call transcripts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        # Get the response text
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        raise Exception(f"OpenAI API error: {str(e)}")

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
                
                # Format the transcript if needed
                transcript = call_data.get('transcript', '')
                transcript = format_transcript(transcript)
                
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
                
                # Format the transcript if needed
                transcript = data.get('transcript', '')
                transcript = format_transcript(transcript)
                
                call = Call.objects.create(
                    phone_number=data.get('from_number', 'Unknown'),
                    duration=data.get('duration', 0),
                    call_time=timezone.now(),
                    follow_up=data.get('Follow_up', False),
                    summary=data.get('summary', ''),
                    transcript=transcript,
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

def format_transcript(transcript):
    """
    Process incoming transcript to ensure proper formatting.
    - Ensures each speaker's part starts with 'Agent:' or 'Patient:'
    - Ensures each speaker change gets a new line
    """
    if not transcript:
        return ""
    
    # Detect if this is a conversation already properly formatted
    if ("Agent:" in transcript and "Patient:" in transcript) or ("Agent:" in transcript and "User:" in transcript):
        # Convert any "User:" to "Patient:" for consistency
        normalized = transcript.replace("User:", "Patient:")
        return normalized
    
    lines = []
    current_speaker = None
    current_text = []
    
    # Split by newlines and process each line
    for raw_line in transcript.strip().split('\n'):
        line = raw_line.strip()
        if not line:
            continue
            
        # Detect speaker by different prefixes
        if line.startswith('Agent:') or line.startswith('Agent '):
            # If we were collecting text for previous speaker, add it
            if current_speaker and current_text:
                lines.append((current_speaker, ' '.join(current_text)))
                current_text = []
            
            # Start collecting text for Agent
            current_speaker = 'Agent'
            text_part = line.replace('Agent:', '').replace('Agent ', '').strip()
            if text_part:
                current_text.append(text_part)
                
        elif line.startswith('User:') or line.startswith('User ') or line.startswith('Patient:') or line.startswith('Patient '):
            # If we were collecting text for previous speaker, add it
            if current_speaker and current_text:
                lines.append((current_speaker, ' '.join(current_text)))
                current_text = []
            
            # Start collecting text for User/Patient
            current_speaker = 'Patient'
            text_part = line.replace('User:', '').replace('User ', '').replace('Patient:', '').replace('Patient ', '').strip()
            if text_part:
                current_text.append(text_part)
        
        # Handle quotes that might indicate agent speaking
        elif line.startswith('"') and current_speaker is None:
            current_speaker = 'Agent'
            current_text.append(line)
            
        # Continue with current speaker
        elif current_speaker:
            current_text.append(line)
            
        # If no speaker identified yet, alternate between agent and patient
        else:
            # Default starting with Agent if we can't tell
            current_speaker = 'Agent'
            current_text.append(line)
    
    # Add the final speaker's text
    if current_speaker and current_text:
        lines.append((current_speaker, ' '.join(current_text)))
    
    # Format the normalized lines
    formatted_lines = []
    for speaker, text in lines:
        # Remove surrounding quotes if present for Agent text
        if speaker == 'Agent' and text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
            
        formatted_lines.append(f"{speaker}: {text}")
    
    return "\n".join(formatted_lines)