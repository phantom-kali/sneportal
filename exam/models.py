from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Subject(models.Model):
    name = models.CharField(max_length=100)  # Science, Mathematics, Kiswahili, English
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Exam(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Kiswahili'),
    ]
    
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=20)  # Grade 1, Grade 2, etc.
    duration_minutes = models.IntegerField(default=45)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    instructions = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

    def get_total_questions(self):
        return self.questions.count()

    def get_total_points(self):
        return sum(q.points for q in self.questions.all())

    class Meta:
        ordering = ['-created_at']


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
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

    def get_options_text(self):
        """Format options for voice reading"""
        if self.question_type == 'multiple_choice' and self.options:
            options_text = []
            for key, value in self.options.items():
                options_text.append(f"Option {key}: {value}")
            return ". ".join(options_text)
        elif self.question_type == 'true_false':
            return "Say True or False"
        return ""

    def format_for_voice(self):
        """Format complete question for voice reading"""
        text = f"Question {self.order}. {self.question_text}"
        if self.get_options_text():
            text += f". {self.get_options_text()}"
        return text

    class Meta:
        ordering = ['exam', 'order']
        unique_together = ['exam', 'order']


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
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    student_name = models.CharField(max_length=100, blank=True)
    student_grade = models.CharField(max_length=20, blank=True)
    current_question_index = models.IntegerField(default=0)
    current_state = models.CharField(max_length=20, choices=SESSION_STATES, default='setup')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_score = models.IntegerField(default=0)
    time_remaining = models.IntegerField()  # in seconds
    
    def __str__(self):
        return f"{self.exam.title} - {self.student_name or 'Unknown'}"

    @property
    def current_question(self):
        """Get the current question being attempted"""
        questions = self.exam.questions.all()
        if self.current_question_index < len(questions):
            return questions[self.current_question_index]
        return None

    @property
    def progress_percentage(self):
        """Calculate exam completion percentage"""
        total_questions = self.exam.get_total_questions()
        if total_questions == 0:
            return 0
        return (self.current_question_index / total_questions) * 100

    @property
    def time_remaining_formatted(self):
        """Format remaining time for voice announcement"""
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        if minutes > 0:
            return f"{minutes} minutes and {seconds} seconds"
        return f"{seconds} seconds"

    def advance_question(self):
        """Move to next question"""
        self.current_question_index += 1
        self.save()

    def go_back_question(self):
        """Go to previous question"""
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.save()

    def is_complete(self):
        """Check if exam is complete"""
        return self.current_question_index >= self.exam.get_total_questions()

    def complete_exam(self):
        """Mark exam as complete"""
        self.current_state = 'exam_complete'
        self.completed_at = timezone.now()
        self.save()

    class Meta:
        ordering = ['-started_at']


class StudentResponse(models.Model):
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='responses/%Y/%m/%d/', blank=True, null=True)
    transcribed_text = models.TextField(blank=True)
    final_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.exam_session.student_name} - Q{self.question.order}: {self.final_answer}"

    def check_answer(self):
        """Check if the answer is correct and calculate points"""
        if self.question.question_type == 'multiple_choice':
            # Handle variations like "A", "Option A", "The answer is A"
            answer_clean = self.final_answer.upper().strip()
            if answer_clean in ['A', 'B', 'C', 'D']:
                self.is_correct = answer_clean == self.question.correct_answer.upper()
            else:
                # Try to extract letter from longer responses
                for letter in ['A', 'B', 'C', 'D']:
                    if letter in answer_clean:
                        self.is_correct = letter == self.question.correct_answer.upper()
                        break
        elif self.question.question_type == 'true_false':
            answer_clean = self.final_answer.lower().strip()
            if 'true' in answer_clean:
                self.is_correct = self.question.correct_answer.lower() == 'true'
            elif 'false' in answer_clean:
                self.is_correct = self.question.correct_answer.lower() == 'false'
        else:
            # Short answer - simple string comparison (can be enhanced)
            self.is_correct = self.final_answer.lower().strip() == self.question.correct_answer.lower().strip()
        
        self.points_earned = self.question.points if self.is_correct else 0
        self.save()

    class Meta:
        ordering = ['answered_at']
        unique_together = ['exam_session', 'question']