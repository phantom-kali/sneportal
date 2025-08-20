import json
import re
import wave
import numpy as np
import base64
import io
import os
import tempfile
import logging
from django.conf import settings
from django.utils import timezone
from django.contrib.sessions.models import Session

# Local voice processing imports
import whisper
import torch
from TTS.api import TTS

logger = logging.getLogger(__name__)


class LocalVoiceProcessor:
    """Core voice processing functionality using local Coqui TTS and Whisper"""
    
    def __init__(self):
        # Initialize Whisper model (small for balance of speed/accuracy)
        self.whisper_model = whisper.load_model("small")
        
        # Initialize Coqui TTS
        # Get available TTS models - using a fast English model
        self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", 
                      progress_bar=False, gpu=torch.cuda.is_available())
        
        # Voice settings
        self.voice_settings = getattr(settings, 'VOICE_SETTINGS', {})
        
        logger.info("Local voice processor initialized with Whisper (small) and Coqui TTS")
    
    def transcribe_audio(self, audio_data, language_code='en-US', **kwargs):
        """Convert audio to text using Whisper"""
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            try:
                # Transcribe using Whisper
                language = 'en' if language_code.startswith('en') else 'sw'
                result = self.whisper_model.transcribe(
                    temp_audio_path,
                    language=language,
                    word_timestamps=False
                )
                
                transcript = result['text'].strip()
                
                if transcript:
                    return {
                        'success': True,
                        'transcript': transcript
                    }
                else:
                    return {
                        'success': False,
                        'transcript': '',
                        'error': 'No speech detected'
                    }
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}")
            return {
                'success': False,
                'transcript': '',
                'error': str(e)
            }
    
    def synthesize_speech(self, text, language_code='en-US', voice_gender='NEUTRAL'):
        """Convert text to speech using Coqui TTS"""
        try:
            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            try:
                # Generate speech using Coqui TTS
                self.tts.tts_to_file(text=text, file_path=temp_audio_path)
                
                # Read the generated audio file
                with open(temp_audio_path, 'rb') as audio_file:
                    audio_content = audio_file.read()
                
                return {
                    'success': True,
                    'audio_content': audio_content,
                    'content_type': 'audio/wav'
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Coqui TTS synthesis error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_tone(self, frequency=800, duration=0.5, sample_rate=16000):
        """Generate audio tone to signal voice capture start"""
        try:
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)
            # Convert to 16-bit PCM
            tone = (tone * 32767).astype(np.int16)
            
            # Create WAV file in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(tone.tobytes())
            
            return {
                'success': True,
                'tone_data': buffer.getvalue()
            }
            
        except Exception as e:
            logger.error(f"Tone generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class LocalVoiceFlowManager:
    """Local implementation of voice flow manager using local voice processor"""
    
    def __init__(self):
        self.voice_processor = LocalVoiceProcessor()
        # Import the existing command parser - it doesn't need to change
        from .voice_processor import VoiceCommandParser
        self.command_parser = VoiceCommandParser()
    
    def handle_voice_input(self, session, audio_data, existing_transcript=None):
        """Main entry point for processing voice input using local models"""
        try:
            # Use existing transcript if provided, otherwise transcribe locally
            if existing_transcript:
                transcript = existing_transcript
                transcription_success = True
            else:
                language_code = 'sw-KE' if session.exam.language == 'sw' else 'en-US'
                transcription_result = self.voice_processor.transcribe_audio(
                    audio_data, 
                    language_code
                )
                transcription_success = transcription_result.get('success', False)
                transcript = transcription_result.get('transcript', '')
            
            # Validate transcript exists
            if not transcription_success or not transcript:
                return self._create_error_response(
                    "Sorry, I couldn't understand your response. Please try again."
                )
            
            # Process the transcript using existing logic
            command = self.command_parser.parse_command(transcript, session.current_state)
                
            # Route to appropriate handler - use existing methods from original implementation
            if session.current_state == 'student_name':
                return self._handle_name_input(session, transcript, command)
            elif session.current_state == 'student_grade':
                return self._handle_grade_input(session, transcript, command)
            elif session.current_state == 'exam_briefing':
                return self._handle_briefing_response(session, transcript, command)
            elif session.current_state == 'question_reading':
                return self._handle_question_command(session, transcript, command)
            elif session.current_state == 'answer_capture':
                return self._handle_answer_input(session, transcript, command)
            elif session.current_state == 'answer_confirmation':
                return self._handle_confirmation(session, transcript, command)
            
            return self._create_error_response("Invalid state")
            
        except Exception as e:
            logger.error(f"Local voice flow error: {str(e)}")
            return self._create_error_response(
                "Sorry, there was an error processing your response. Please try again."
            )
    
    # Import all the existing handler methods from the original VoiceFlowManager
    def _handle_name_input(self, session, transcript, command):
        """Handle student name input"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        session.student_name = transcript
        session.current_state = 'student_grade'
        session.save()
        
        response_text = f"Thank you, {transcript}. Now please state your grade level."
        return self._create_voice_response(session, response_text)
    
    def _handle_grade_input(self, session, transcript, command):
        """Handle student grade input"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        session.student_grade = transcript
        session.current_state = 'exam_briefing'
        session.save()
        
        briefing_text = self._create_exam_briefing(session)
        return self._create_voice_response(session, briefing_text)
    
    def _handle_briefing_response(self, session, transcript, command):
        """Handle exam briefing response"""
        if command['type'] == 'navigation' and command['command'] == 'start_exam':
            session.current_state = 'question_reading'
            session.save()
            
            question_text = self._format_question_for_voice(session.current_question)
            return self._create_voice_response(session, question_text)
        
        elif command['type'] == 'navigation' and command['command'] == 'repeat_question':
            briefing_text = self._create_exam_briefing(session)
            return self._create_voice_response(session, briefing_text)
        
        response_text = "Please say 'start' when you are ready to begin the exam, or say 'repeat' to hear the instructions again."
        return self._create_voice_response(session, response_text)
    
    def _handle_question_command(self, session, transcript, command):
        """Handle commands during question reading"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        session.current_state = 'answer_capture'
        session.save()
        
        response_text = "Please provide your answer after the tone."
        return self._create_voice_response(session, response_text, include_tone=True)
    
    def _handle_answer_input(self, session, transcript, command):
        """Handle answer input from student"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        current_question = session.current_question
        answer_result = self.command_parser.extract_answer(
            transcript, current_question.question_type
        )
        
        if self.command_parser.is_valid_answer(answer_result['answer'], current_question.question_type):
            session.current_state = 'answer_confirmation'
            session.save()
            
            # Store answer in session for confirmation
            
            request_session = getattr(session, '_request_session', {})
            request_session['temp_answer'] = answer_result['answer']
            request_session['temp_transcript'] = transcript
            
            response_text = f"You answered {answer_result['answer']}. Is this correct? Say yes to confirm or no to try again."
            return self._create_voice_response(session, response_text)
        else:
            response_text = f"I didn't understand your answer. For this {current_question.question_type} question, please provide a clear answer."
            return self._create_voice_response(session, response_text, include_tone=True)
    
    def _handle_confirmation(self, session, transcript, command):
        """Handle answer confirmation"""
        if command['type'] == 'confirmation':
            request_session = getattr(session, '_request_session', {})
            
            if command['confirmed']:
                temp_answer = request_session.get('temp_answer', '')
                temp_transcript = request_session.get('temp_transcript', '')
                
                self._save_student_response(session, temp_answer, temp_transcript)
                
                session.advance_question()
                
                if session.is_complete():
                    session.complete_exam()
                    final_text = self._create_exam_completion_text(session)
                    return self._create_voice_response(session, final_text)
                else:
                    session.current_state = 'question_reading'
                    session.save()
                    
                    question_text = self._format_question_for_voice(session.current_question)
                    return self._create_voice_response(session, question_text)
            else:
                session.current_state = 'answer_capture'
                session.save()
                
                response_text = "Please provide your answer again after the tone."
                return self._create_voice_response(session, response_text, include_tone=True)
        
        response_text = "Please say 'yes' to confirm your answer or 'no' to try again."
        return self._create_voice_response(session, response_text)
    
    def _handle_navigation_command(self, session, command):
        """Handle navigation commands"""
        if command == 'go_back':
            if session.current_question_index > 0:
                session.go_back_question()
                session.current_state = 'question_reading'
                session.save()
                
                question_text = self._format_question_for_voice(session.current_question)
                return self._create_voice_response(session, question_text)
            else:
                response_text = "You are already at the first question."
                return self._create_voice_response(session, response_text)
        
        elif command == 'repeat_question':
            if session.current_question:
                question_text = self._format_question_for_voice(session.current_question)
                return self._create_voice_response(session, question_text)
            else:
                response_text = "No question to repeat."
                return self._create_voice_response(session, response_text)
        
        elif command == 'time_remaining':
            response_text = f"You have {session.time_remaining_formatted} remaining."
            return self._create_voice_response(session, response_text)
        
        elif command == 'next_question':
            if session.current_state == 'question_reading':
                session.current_state = 'answer_capture'
                session.save()
                response_text = "Please provide your answer after the tone."
                return self._create_voice_response(session, response_text, include_tone=True)
        
        response_text = "I didn't understand that command. Please try again."
        return self._create_voice_response(session, response_text)
    
    def _create_exam_briefing(self, session):
        """Create comprehensive exam briefing text"""
        exam = session.exam
        total_questions = exam.get_total_questions()
        
        briefing = f"""
        Hello {session.student_name}, Grade {session.student_grade}. 
        
        You are about to take the {exam.title} exam in {exam.subject.name}.
        
        This exam has {total_questions} questions and you have {exam.duration_minutes} minutes to complete it.
        
        {exam.instructions}
        
        Here are the voice commands you can use:
        - Say 'repeat' to hear a question again
        - Say 'go back' to return to the previous question
        - Say 'time remaining' to hear how much time you have left
        
        When you are ready to begin, say 'start'.
        """
        
        return briefing.strip()
    
    def _format_question_for_voice(self, question):
        """Format question for voice reading"""
        if not question:
            return "No more questions."
        
        return question.format_for_voice()
    
    def _create_exam_completion_text(self, session):
        """Create exam completion announcement"""
        return f"""
        Congratulations {session.student_name}! You have completed the {session.exam.title} exam.
        
        Your final score is {session.total_score} out of {session.exam.get_total_points()} points.
        
        Thank you for taking the exam. You may now leave your seat.
        """
    
    def _save_student_response(self, session, answer, transcript):
        """Save student response to database"""
        from .models import StudentResponse
        
        current_question = session.current_question
        
        response, created = StudentResponse.objects.get_or_create(
            exam_session=session,
            question=current_question,
            defaults={
                'transcribed_text': transcript,
                'final_answer': answer,
                'attempts': 1
            }
        )
        
        if not created:
            response.final_answer = answer
            response.transcribed_text = transcript
            response.attempts += 1
        
        response.check_answer()
        
        session.total_score = sum(
            r.points_earned for r in session.responses.all()
        )
        session.save()
        
        return response
    
    def _create_voice_response(self, session, text, include_tone=False):
        """Create voice response with local TTS"""
        language_code = 'sw-KE' if session.exam.language == 'sw' else 'en-US'
        
        # Generate TTS using local Coqui TTS
        tts_result = self.voice_processor.synthesize_speech(text, language_code)
        
        response = {
            'session_id': session.session_id,
            'state': session.current_state,
            'text': text,
            'audio_available': tts_result['success'],
            'include_tone': include_tone,
            'progress': session.progress_percentage,
            'time_remaining': session.time_remaining,
            'current_question': session.current_question_index + 1,
            'total_questions': session.exam.get_total_questions()
        }
        
        if tts_result['success']:
            # Encode audio data as base64 for JSON serialization
            response['audio_data'] = base64.b64encode(tts_result['audio_content']).decode('utf-8')
            response['audio_content_type'] = tts_result.get('content_type', 'audio/wav')
        
        return response
    
    def _create_error_response(self, message):
        """Create error response"""
        return {
            'error': True,
            'message': message,
            'text': message,
            'audio_available': False
        }


# Convenience function to switch between local and cloud processing
def get_voice_flow_manager(use_local=True):
    """Get voice flow manager - local or cloud-based"""
    if use_local:
        return LocalVoiceFlowManager()
    else:
        from .voice_processor import VoiceFlowManager
        return VoiceFlowManager()
