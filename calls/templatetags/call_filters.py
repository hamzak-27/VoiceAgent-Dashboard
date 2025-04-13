from django import template
from django.utils.html import mark_safe
import re

register = template.Library()

@register.filter
def divisibleby(value, arg):
    """Returns the integer division of the value by the argument"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def modulo(value, arg):
    """Returns the remainder of the division"""
    try:
        return int(value) % int(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def format_transcript(transcript):
    """
    Formats a transcript with different styling for agent and patient lines.
    
    Example usage in template:
    {{ call.transcript|format_transcript }}
    """
    if not transcript:
        return ''
    
    lines = []
    current_speaker = None
    current_text = []
    
    # First pass - normalize the format by splitting by speaker changes
    for raw_line in transcript.split('\n'):
        line = raw_line.strip()
        if not line:
            continue
            
        # Check for Agent/User markers in different formats
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
                
        # Handle quotes that might indicate a speaker
        elif line.startswith('"') and current_speaker is None:
            current_speaker = 'Agent'
            current_text.append(line)
        
        # Continue with current speaker
        elif current_speaker:
            current_text.append(line)
        
        # If no speaker identified yet, make a guess based on content
        else:
            # Default to starting with Agent if we can't tell
            current_speaker = 'Agent'
            current_text.append(line)
    
    # Add the final speaker's text
    if current_speaker and current_text:
        lines.append((current_speaker, ' '.join(current_text)))
    
    # Format the normalized lines
    formatted_lines = []
    for speaker, text in lines:
        if speaker == 'Agent':
            # Remove surrounding quotes if present
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1].strip()
            formatted_lines.append(f'<div class="agent-line"><strong>Agent:</strong> {text}</div>')
        else:
            formatted_lines.append(f'<div class="patient-line"><strong>Patient:</strong> {text}</div>')
    
    return mark_safe('\n'.join(formatted_lines))