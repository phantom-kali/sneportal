## Project Overview
Build a voice-first exam system for blind students using Django SSR with Google Cloud Speech-to-Text and Text-to-Speech APIs. The system should be extremely simple, accessible, and follow a linear voice-controlled flow.

## Core Requirements

### 1. System Architecture
- **Backend**: Django with Server-Side Rendering (SSR)
- **Frontend**: Simple HTML/CSS/JavaScript with jQuery for AJAX requests
- **Voice APIs**: Google Cloud Speech-to-Text and Text-to-Speech
- **Database**: Django ORM with PostgreSQL/SQLite
- **Session Management**: Django sessions for exam state tracking

### 2. Database Models

```python
# Required Django Models
class Subject(models.Model):
    name = models.CharField(max_length=100)  # Science, Mathematics, Kiswahili, English
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Exam(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=20)  # Grade 1, Grade 2, etc.
    duration_minutes = models.IntegerField(default=45)
    language = models.CharField(max_length=10, choices=[('en', 'English'), ('sw', 'Kiswahili')], default='en')
    instructions = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    options = models.JSONField(blank=True, null=True)  # For multiple choice: {"A": "Option 1", "B": "Option 2", ...}
    correct_answer = models.CharField(max_length=500)
    order = models.IntegerField()
    points = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['order']

class ExamSession(models.Model):
    SESSION_STATES = [
        ('setup', 'Setup'),
        ('student_name', 'Capturing Student Name'),
        ('student_grade', 'Capturing Student Grade'), 
        ('exam_briefing', 'Exam Briefing'),
        ('question_reading', 'Reading Question'),
        ('answer_capture', 'Capturing Answer'),
        ('answer_confirmation', 'Confirming Answer'),
        ('exam_complete', 'Exam Complete'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    student_name = models.CharField(max_length=100, blank=True)
    student_grade = models.CharField(max_length=20, blank=True)
    current_question_index = models.IntegerField(default=0)
    current_state = models.CharField(max_length=20, choices=SESSION_STATES, default='setup')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_score = models.IntegerField(default=0)
    time_remaining = models.IntegerField()  # in seconds
    
class StudentResponse(models.Model):
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='responses/', blank=True, null=True)
    transcribed_text = models.TextField(blank=True)
    final_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=1)
```

### 3. User Interface Requirements

#### A. Teacher Setup Interface
- **Single page with minimal elements**:
  - Dropdown to select active exams
  - Large "Start Voice Session" button
  - No login required - direct access
  - Clear indication that system will go voice-only after start

#### B. Voice Interface Requirements
- **Single page that transforms based on state**
- **Visual elements for supervisor monitoring**:
  - Current system state indicator
  - Question display (for supervisor reference)
  - Audio waveform/listening indicator
  - Progress bar showing question completion
  - Timer showing remaining time
  - Emergency stop button
  - Available voice commands display

#### C. Voice Flow States
1. **Student Name Capture**: "Please state your name after the tone" → *BEEP* → Capture → Playback confirmation
2. **Student Grade Capture**: "Please state your grade level" → *BEEP* → Capture → Playback confirmation  
3. **Exam Briefing**: Read full instructions, available commands, exam details
4. **Question Reading**: Read question number, question text, and all choices
5. **Answer Capture**: Prompt for answer → *BEEP* → Capture response
6. **Answer Confirmation**: "You said [ANSWER]. Is this correct?" → Yes/No handling
7. **Navigation**: Handle "next question", "previous question", "repeat question", "time remaining"

### 4. Voice Processing Implementation

#### A. Google Cloud Integration
```python
# Required functionality for voice processing
class VoiceProcessor:
    def __init__(self):
        self.stt_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
    
    def transcribe_audio(self, audio_data, language_code='en-US'):
        # Convert audio to text using Google STT
        # Handle different audio formats
        # Return transcribed text with confidence score
        
    def synthesize_speech(self, text, language_code='en-US', voice_gender='NEUTRAL'):
        # Convert text to speech using Google TTS
        # Return audio data for playback
        # Handle different languages (English/Kiswahili)
    
    def generate_tone(self, frequency=800, duration=0.5):
        # Generate audio tone to signal voice capture start
```

#### B. Voice Command Parser
```python
class VoiceCommandParser:
    def parse_command(self, transcribed_text, current_state):
        # Parse voice commands based on current state
        # Handle navigation commands: "go back", "repeat question", "time remaining"
        # Handle answers: "A", "B", "C", "D", "True", "False"
        # Handle confirmations: "Yes", "No"
        # Return structured command object
    
    def extract_answer(self, text, question_type):
        # Extract answer from natural speech
        # Handle variations: "A", "Option A", "The answer is A"
        # Return standardized answer format
```

### 5. Django Views and URLs

#### A. Required Views
```python
# Main exam interface view
class ExamSessionView(View):
    def get(self, request):
        # Serve the main exam interface
        # Load available exams for teacher selection
        # Initialize session management
    
    def post(self, request):
        # Handle exam selection from teacher
        # Create new exam session
        # Redirect to voice interface

# Voice processing endpoints
class VoiceProcessingView(View):
    def post(self, request):
        # Handle audio upload from frontend
        # Process through Google STT
        # Update session state
        # Return TTS response and next state

class SessionStateView(View):
    def get(self, request):
        # Return current session state as JSON
        # Include current question, progress, time remaining
    
    def post(self, request):
        # Update session state
        # Handle state transitions
        # Save student responses

# Text-to-speech endpoint
class TTSView(View):
    def post(self, request):
        # Convert text to speech
        # Return audio file/stream
        # Handle language selection
```

#### B. URL Configuration
```python
urlpatterns = [
    path('', ExamSessionView.as_view(), name='exam_session'),
    path('voice/process/', VoiceProcessingView.as_view(), name='voice_process'),
    path('voice/tts/', TTSView.as_view(), name='text_to_speech'),
    path('session/state/', SessionStateView.as_view(), name='session_state'),
    path('admin/', admin.site.urls),
]
```

### 6. Frontend JavaScript Implementation

#### A. Voice Interface Controller
```javascript
class VoiceExamController {
    constructor() {
        this.currentState = 'setup';
        this.isListening = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.sessionId = null;
    }
    
    // Initialize voice interface after teacher selects exam
    initializeVoiceInterface(examId) {
        // Create exam session
        // Start voice flow
        // Initialize audio recording
    }
    
    // Handle state transitions
    handleStateTransition(newState, data) {
        // Update UI based on state
        // Show appropriate prompts
        // Handle voice commands per state
    }
    
    // Audio recording and processing
    startRecording() {
        // Start microphone recording
        // Show listening indicator
        // Handle recording timeout
    }
    
    stopRecording() {
        // Stop recording
        // Send audio to backend for processing
        // Handle response and next state
    }
    
    // Voice feedback system
    playTone() {
        // Generate audio tone before recording
        // Use Web Audio API
    }
    
    speakText(text) {
        // Request TTS from backend
        // Play audio response
        // Handle completion callback
    }
}
```

#### B. State Management
```javascript
// Voice interface state machine
const StateHandlers = {
    student_name: {
        prompt: "Please state your name clearly after the tone",
        commands: ["speak your name"],
        onResponse: (text) => confirmName(text)
    },
    
    student_grade: {
        prompt: "Please state your grade level",
        commands: ["speak your grade"],
        onResponse: (text) => confirmGrade(text)
    },
    
    exam_briefing: {
        prompt: "Listen to exam instructions. Say 'Start' when ready.",
        commands: ["start", "repeat instructions"],
        onResponse: (text) => handleBriefingResponse(text)
    },
    
    question_reading: {
        prompt: "Listen to the question and choices",
        commands: ["repeat question", "go back", "time remaining"],
        onResponse: (text) => handleQuestionCommand(text)
    },
    
    answer_capture: {
        prompt: "Please provide your answer",
        commands: ["A", "B", "C", "D", "repeat question", "go back"],
        onResponse: (text) => captureAnswer(text)
    },
    
    answer_confirmation: {
        prompt: "You answered [X]. Is this correct?",
        commands: ["yes", "no", "listen again"],
        onResponse: (text) => confirmAnswer(text)
    }
};
```

### 7. Voice Flow Logic

#### A. Complete Voice Sequence
```python
# Voice flow implementation
class VoiceFlowManager:
    def handle_voice_input(self, session_id, audio_data):
        session = ExamSession.objects.get(session_id=session_id)
        
        if session.current_state == 'student_name':
            return self.handle_name_input(session, audio_data)
        elif session.current_state == 'student_grade':
            return self.handle_grade_input(session, audio_data)
        elif session.current_state == 'exam_briefing':
            return self.handle_briefing_response(session, audio_data)
        elif session.current_state == 'question_reading':
            return self.handle_question_command(session, audio_data)
        elif session.current_state == 'answer_capture':
            return self.handle_answer_input(session, audio_data)
        elif session.current_state == 'answer_confirmation':
            return self.handle_confirmation(session, audio_data)
    
    def generate_voice_response(self, session, response_text):
        # Convert text to speech
        # Return audio data and next state
        # Handle language selection based on exam
    
    def read_question_aloud(self, question):
        # Format question for voice reading
        # Include question number, text, and choices
        # Return formatted text for TTS
```

#### B. Navigation Commands
```python
class NavigationHandler:
    def handle_navigation(self, command, session):
        if command == 'go_back':
            return self.go_to_previous_question(session)
        elif command == 'repeat_question':
            return self.repeat_current_question(session)
        elif command == 'time_remaining':
            return self.announce_time_remaining(session)
        elif command == 'next_question':
            return self.advance_to_next_question(session)
    
    def format_time_announcement(self, seconds_remaining):
        # Format time for voice announcement
        # "You have 25 minutes and 30 seconds remaining"
```

### 8. Django Admin Integration

#### A. Admin Configuration
```python
# Admin interface for exam management
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'grade_level', 'duration_minutes', 'is_active']
    list_filter = ['subject', 'grade_level', 'is_active']
    search_fields = ['title', 'subject__name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_text', 'question_type', 'order', 'points']
    list_filter = ['exam', 'question_type']
    ordering = ['exam', 'order']
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Custom form field for JSON options
        if db_field.name == 'options':
            # Provide better interface for multiple choice options
            pass
        return super().formfield_for_dbfield(db_field, request, **kwargs)

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student_name', 'student_grade', 'current_state', 'total_score', 'started_at']
    list_filter = ['exam', 'current_state', 'started_at']
    readonly_fields = ['session_id', 'started_at', 'completed_at']
    
    def has_add_permission(self, request):
        return False  # Sessions created through voice interface only
```

### 9. Settings and Configuration

#### A. Django Settings
```python
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS = 'path/to/service-account-key.json'

# Voice processing settings
VOICE_SETTINGS = {
    'DEFAULT_LANGUAGE': 'en-US',
    'SUPPORTED_LANGUAGES': ['en-US', 'sw-KE'],
    'AUDIO_FORMAT': 'WEBM_OPUS',
    'SAMPLE_RATE': 16000,
    'RECORDING_TIMEOUT': 30,  # seconds
    'SILENCE_THRESHOLD': 2,   # seconds of silence before stopping
}

# File upload settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Session settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour
```

#### B. Requirements.txt
```
Django==4.2.7
google-cloud-speech==2.21.0
google-cloud-texttospeech==2.16.3
psycopg2-binary==2.9.7
Pillow==10.0.1
django-cors-headers==4.3.1
```

### 10. Testing Requirements

#### A. Voice Processing Tests
- Test STT accuracy with various accents and speech patterns
- Test TTS quality in both English and Kiswahili
- Test audio recording and playback functionality
- Test state transitions and command recognition

#### B. User Experience Tests
- Test complete exam flow from start to finish
- Test navigation commands and error handling
- Test timeout handling and session recovery
- Test emergency stop functionality

### 11. Deployment Considerations

#### A. Production Setup
- Configure Google Cloud credentials securely
- Set up proper file storage for audio files
- Configure session storage (Redis recommended)
- Set up monitoring for voice processing errors

#### B. Performance Optimization
- Implement audio compression for faster uploads
- Cache TTS responses for repeated text
- Optimize database queries for real-time performance
- Implement proper error handling and recovery

### 12. Security and Privacy

#### A. Data Protection
- Secure audio file storage with appropriate permissions
- Implement session security and timeout handling
- Ensure GDPR compliance for voice data storage
- Implement audit logging for exam sessions

#### B. Access Control
- Implement simple teacher authentication for exam setup
- Secure admin interface with proper permissions
- Implement rate limiting for voice processing endpoints
- Validate and sanitize all voice inputs

## Implementation Priority

1. **Phase 1**: Basic Django setup, models, and admin interface
2. **Phase 2**: Voice processing integration with Google APIs
3. **Phase 3**: Complete voice flow implementation
4. **Phase 4**: Frontend interface and state management
5. **Phase 5**: Testing, optimization, and deployment

This system should provide a seamless, accessible exam experience for blind students while maintaining simplicity and reliability.


---

### 💡 Sponsor This Project on Render

This project is currently hosted on [Render](https://render.com) under a free tier. To ensure continuous uptime and unlock more resources (e.g., background workers, storage, faster builds), I’m seeking a sponsor to cover hosting costs.

If you're interested in sponsoring, you can do so **without sending money directly to me**:

1. Create a free account on [Render](https://render.com).
2. Create a **Team** from your dashboard.
3. Add a payment method for billing.
4. Invite me (**[fideleliudclimax@gmail.com](mailto:fideleliudclimax@gmail.com)**) as a collaborator.
5. I’ll transfer the service to your team and manage everything from there.

✅ You stay in control of the billing.
✅ I take care of the development, deployment, and maintenance.

**Want to help?** Email me at **[fideleliudclimax@gmail.com](mailto:fideleliudclimax@gmail.com)** or open a discussion in the issues tab.


