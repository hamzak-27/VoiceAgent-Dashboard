import os
import django
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'call_dashboard.settings')
django.setup()

from calls.models import Call  # Replace 'your_app' with your actual app name

# Sample data
phone_numbers = [
    '+1234567890',
    '+1987654321',
    '+1456789012',
    '+1567890123',
    '+1678901234',
    '+1789012345',
    '+1890123456',
    '+1901234567',
]

summaries = [
    "Patient inquired about medication side effects and was advised to continue as prescribed but monitor for specific symptoms.",
    "Follow-up appointment scheduled for next week. Patient reported improvement in symptoms.",
    "Patient reported new symptoms. Urgent appointment scheduled with specialist.",
    "Medication refill request processed. Patient will pick up prescription tomorrow.",
    "Patient had questions about insurance coverage for upcoming procedure.",
    "Discussed lab results with patient. All values within normal range.",
    "Patient requested medical records to be sent to another provider.",
    "Discussed dietary recommendations for managing patient's condition.",
]

transcripts = [
    "Agent: Hello, this is Healthcare Services. How may I help you today?\nPatient: Hi, I've been taking my new medication for a week now and I'm experiencing some dizziness.\nAgent: I understand your concern. Dizziness can be a side effect of this medication. Are you experiencing any other symptoms?\nPatient: No, just the dizziness, especially when I stand up quickly.\nAgent: I recommend continuing the medication as prescribed, but please monitor for any worsening symptoms. If the dizziness becomes severe, please contact us immediately or visit the emergency room.",
    
    "Agent: Good morning, this is Healthcare Services. How may I assist you?\nPatient: I'd like to schedule my follow-up appointment with Dr. Smith.\nAgent: Of course, I can help with that. How does next Tuesday at 2:00 PM sound?\nPatient: That works for me.\nAgent: Great, I've scheduled you for Tuesday at 2:00 PM with Dr. Smith. Is there anything else you need help with today?",
    
    "Agent: Healthcare Services, how can I help you?\nPatient: I've developed a rash that's spreading quickly and I'm feeling short of breath.\nAgent: That sounds concerning. Based on your symptoms, I recommend you see a doctor as soon as possible. I can schedule an urgent appointment for you today at 3:30 PM. Would that work for you?\nPatient: Yes, that would be great.\nAgent: I've booked that appointment for you. Please bring your insurance card and arrive 15 minutes early to complete paperwork.",
]

# Create sample calls
def create_sample_data(num_calls=50):
    # Delete existing data
    Call.objects.all().delete()
    
    # Current time
    now = datetime.now()
    
    # Create calls for the past 7 days
    for i in range(num_calls):
        # Random time in the past 7 days
        days_ago = random.randint(0, 6)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        call_time = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Random duration between 1 and 15 minutes
        duration = random.randint(60, 900)
        
        # Random follow-up status
        follow_up = random.choice([True, False])
        
        # Create call
        call = Call(
            phone_number=random.choice(phone_numbers),
            duration=duration,
            call_time=call_time,
            follow_up=follow_up,
            summary=random.choice(summaries) if random.random() > 0.2 else None,
            transcript=random.choice(transcripts) if random.random() > 0.3 else None,
            recording_url="https://example.com/recordings/sample.mp3" if random.random() > 0.4 else None
        )
        call.save()
    
    print(f"Created {num_calls} sample calls")

if __name__ == "__main__":
    create_sample_data()
    print("Sample data creation completed")